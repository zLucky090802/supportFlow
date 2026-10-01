"""Final API security closure; Orders and RAG are intentionally outside this suite."""
import json
import re
import unittest
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

import test_auth_api as fixture
from app.models.generated_models import Customers, Organizations, Users
from app.security.tokens import create_access_token


class FinalAPIIntegrationTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixture.AuthAPITests.setUpClass.__func__)
    setUp = fixture.AuthAPITests.setUp
    request = fixture.AuthAPITests.request

    async def call(self, actor, method, path, body=None, expected=200):
        status, result, _ = await self.request(method, path, body, create_access_token(actor))
        self.assertEqual(status, expected, (actor, method, path, result))
        return result

    async def test_every_core_business_route_rejects_missing_and_invalid_jwt(self):
        prefixes = ("/users", "/customer", "/organizations", "/conversations", "/messages")
        tested = set()
        for route_path, operations in fixture.app.openapi()["paths"].items():
            if not (route_path.startswith(prefixes) or route_path in ("/auth/me", "/db-health")):
                continue
            path = re.sub(r"\{[^}]+\}", "not-authorized", route_path)
            for operation in operations:
                method = operation.upper()
                if method not in ("GET", "POST", "PATCH", "PUT", "DELETE"):
                    continue
                for token in (None, "invalid-token"):
                    with self.subTest(method=method, path=path, token=token):
                        status, body, headers = await self.request(method, path, {}, token)
                        self.assertEqual(status, 401, body)
                        self.assertEqual(headers.get(b"www-authenticate"), b"Bearer")
                tested.add((method, route_path))
        self.assertGreaterEqual(len(tested), 35)

    async def test_created_users_customers_organizations_and_conversations_work_together(self):
        org = await self.call("admin", "PATCH", "/organizations/org", {"name": "Support team"})
        self.assertEqual(org["data"]["name"], "Support team")
        password = "integration-password-never-returned"
        user = await self.call("admin", "POST", "/users", {
            "organization_id": "org", "name": "New agent", "email": "new-agent@example.com",
            "password": password, "role": "AGENT",
        }, 201)
        user_id = user["data"]["id"]
        self.assertNotIn("password", json.dumps(user))
        self.assertNotEqual(self.db.get(Users, user_id).password_hash, password)
        customer = await self.call("supervisor", "POST", "/customer", {
            "organization_id": "org", "name": "New customer", "email": "new-customer@example.com",
        }, 201)
        customer_id = customer["data"]["id"]
        conversation = await self.call("supervisor", "POST", "/conversations", {
            "organization_id": "org", "customer_id": customer_id,
        }, 201)
        path = "/conversations/" + conversation["data"]["id"]
        await self.call("supervisor", "PATCH", path + "/assign", {"agent_id": user_id})
        status, login, _ = await self.request("POST", "/auth/login", {
            "username": "new-agent@example.com", "password": password,
        }, form=True)
        self.assertEqual(status, 200)
        token = login["access_token"]
        status, current, _ = await self.request("GET", "/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(current["data"]["organization_id"], "org")
        status, message, _ = await self.request("POST", path + "/messages", {"content": "Welcome"}, token)
        self.assertEqual(status, 201)
        self.assertEqual(message["data"]["sender_id"], user_id)
        self.assertEqual((await self.request("PATCH", path, {"status": "RESOLVED"}, token))[0], 200)
        self.assertEqual((await self.request("GET", "/customer/" + customer_id, token=token))[0], 403)
        for actor in ("admin", "supervisor"):
            await self.call(actor, "GET", "/customer/" + customer_id)
        foreign = await self.call("foreign", "GET", path, expected=404)
        missing = await self.call("foreign", "GET", "/conversations/missing", expected=404)
        self.assertEqual(foreign, missing)

    async def test_customer_management_and_organization_permissions_all_roles(self):
        for actor in ("admin", "supervisor", "agent"):
            orgs = await self.call(actor, "GET", "/organizations")
            self.assertEqual([row["id"] for row in orgs["data"]], ["org"])
            await self.call(actor, "GET", "/organizations/org")
            await self.call(actor, "PATCH", "/organizations/org", {"name": "Local edited"}, 200 if actor == "admin" else 403)
            await self.call(actor, "POST", "/organizations", {"name": "No platform role", "email": "platform@example.com"}, 403)
            await self.call(actor, "DELETE", "/organizations/org", expected=403)
            allowed = actor != "agent"
            for path in ("/customer", "/customer/customer", "/customer/organizations/org/customers"):
                result = await self.call(actor, "GET", path, expected=200 if allowed else 403)
                if allowed and isinstance(result["data"], list):
                    self.assertTrue(all(row["organization_id"] == "org" for row in result["data"]))
            created = await self.call(actor, "POST", "/customer", {
                "organization_id": "org", "name": "Temporary", "email": actor + "-customer@example.com",
            }, 201 if allowed else 403)
            target = created["data"]["id"] if allowed else "customer"
            await self.call(actor, "PATCH", "/customer/" + target, {"name": "Updated"}, 200 if allowed else 403)
            await self.call(actor, "DELETE", "/customer/" + target, expected=204 if allowed else 403)
            if allowed:
                self.assertIsNone(self.db.get(Customers, target))
        self.assertEqual(self.db.get(Customers, "customer").name, "Customer")
        self.assertEqual(self.db.query(Organizations).count(), 2)

    async def test_sql_failures_across_modules_never_expose_error_details(self):
        secret = "SELECT password_hash FROM users WHERE token='private-secret'"
        cases = (
            ("app.routes.users.user_service.get_users_by_organization_id", "/users"),
            ("app.routes.customers.customer_service.get_customers_by_organization_id", "/customer"),
            ("app.routes.organizations.organization_service.get_organization_by_id", "/organizations"),
            ("app.routes.conversation.authorization.list_conversations", "/conversations"),
            ("app.routes.messages.message_service.get_messages_by_conversation_id", "/conversations/assigned/messages"),
        )
        for target, path in cases:
            with self.subTest(path=path), patch(target, side_effect=SQLAlchemyError(secret)):
                # The conversation router logs this server-side exception deliberately.
                with patch("app.routes.conversation.logger.exception"):
                    body = await self.call("admin", "GET", path, expected=500)
            self.assertEqual(body, {"success": False, "message": "An unexpected database error occurred", "data": None})
            self.assertNotIn("private-secret", json.dumps(body))

    async def test_validation_and_user_responses_do_not_echo_passwords_or_hashes(self):
        marker = "SENSITIVE-password-input"
        for payload in (
            {"organization_id": "org", "name": "Agent", "email": "secret@example.com", "password": {"secret": marker}, "role": "AGENT"},
            {"organization_id": "org", "name": "Agent", "email": "secret@example.com", "password": marker, "role": "AGENT", "password_hash": marker},
        ):
            body = await self.call("admin", "POST", "/users", payload, 422)
            self.assertNotIn(marker, json.dumps(body))
            self.assertEqual(body, {"success": False, "message": "Invalid request data", "data": None})
        for path in ("/users", "/users/agent", "/users/by-organization/org", "/auth/me"):
            body = await self.call("admin", "GET", path)
            output = json.dumps(body)
            for value in ("password_hash", self.password, self.password_hash):
                self.assertNotIn(value, output)
        self.assertEqual(self.db.query(Users).count(), 4)

    async def test_unexpected_and_response_validation_errors_return_only_generic_500(self):
        marker = "SENSITIVE-internal-data"
        for failure in (RuntimeError(marker), None):
            events = []
            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}
            async def send(event):
                events.append(event)
            options = ({"side_effect": failure} if failure else {"return_value": [{"password_hash": marker}]})
            with self.subTest(failure=type(failure).__name__), patch(
                "app.routes.users.user_service.get_users_by_organization_id", **options,
            ):
                # ServerErrorMiddleware sends a sanitized response, then re-raises
                # for server logging; capture the actual response sent to clients.
                with self.assertRaises(Exception):
                    await fixture.app({
                        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                        "method": "GET", "scheme": "http", "path": "/users", "raw_path": b"/users",
                        "root_path": "", "query_string": b"",
                        "headers": [(b"authorization", ("Bearer " + create_access_token("admin")).encode())],
                        "client": ("127.0.0.1", 5555), "server": ("test", 80),
                    }, receive, send)
            self.assertEqual(next(e["status"] for e in events if e["type"] == "http.response.start"), 500)
            content = b"".join(e.get("body", b"") for e in events if e["type"] == "http.response.body")
            self.assertEqual(content, b"Internal Server Error")
            self.assertNotIn(marker.encode(), content)
