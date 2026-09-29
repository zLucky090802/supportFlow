import json
import os
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.generated_models import Base, Conversations, Customers, Organizations, Users
from app.security.passwords import hash_password
from app.security.tokens import create_access_token

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
    from app.db.database import get_db
    from app.main import app


class AuthAPITests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "a long test password for login"
        cls.password_hash = hash_password(cls.password)

    def setUp(self):
        env = patch.dict(os.environ, {"JWT_SECRET_KEY": "test-key-only-never-use-in-production-1234567890"})
        env.start()
        self.addCleanup(env.stop)
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def setup_database(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("char_length", 1, len)

        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add_all([Organizations(id="org", name="Local"), Organizations(id="other", name="Other")])
        self.db.commit()
        self.db.add_all([
            Users(id=user_id, organization_id=org, name=user_id, email=user_id + "@example.com",
                  password_hash=self.password_hash, role=role)
            for user_id, org, role in (("admin", "org", "ADMIN"), ("supervisor", "org", "SUPERVISOR"),
                                       ("agent", "org", "AGENT"), ("foreign", "other", "ADMIN"))
        ])
        self.db.add_all([Customers(id="customer", organization_id="org", name="Customer", email="customer@example.com"),
                         Customers(id="foreign-customer", organization_id="other", name="Foreign", email="foreign-customer@example.com")])
        self.db.commit()
        self.db.add_all([
            Conversations(id="assigned", organization_id="org", customer_id="customer", assigned_agent_id="agent", status="OPEN"),
            Conversations(id="unassigned", organization_id="org", customer_id="customer", status="OPEN"),
            Conversations(id="foreign-conversation", organization_id="other", customer_id="foreign-customer", status="OPEN"),
        ])
        self.db.commit()
        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db

        def restore_overrides():
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
        self.addCleanup(restore_overrides)

    async def request(self, method, path, body=None, token=None, form=False):
        events = []
        data = urlencode(body).encode() if form else json.dumps(body).encode() if body is not None else b""
        headers = [(b"content-type", b"application/x-www-form-urlencoded" if form else b"application/json")]
        if token is not None:
            headers.append((b"authorization", ("Bearer " + token).encode()))

        async def receive():
            return {"type": "http.request", "body": data, "more_body": False}

        async def send(message):
            events.append(message)

        await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                   "scheme": "http", "path": path, "raw_path": path.encode(), "root_path": "",
                   "query_string": b"", "headers": headers, "client": ("127.0.0.1", 5555),
                   "server": ("test", 80)}, receive, send)
        start = next(message for message in events if message["type"] == "http.response.start")
        response = b"".join(message.get("body", b"") for message in events if message["type"] == "http.response.body")
        return start["status"], json.loads(response) if response else None, dict(start["headers"])

    async def test_login_and_current_user_with_real_hash_and_jwt(self):
        status, body, headers = await self.request("POST", "/auth/login", {
            "username": " ADMIN@EXAMPLE.COM ", "password": self.password,
        }, form=True)
        self.assertEqual(status, 200)
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["expires_in"], 1800)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        status, body, _ = await self.request("GET", "/auth/me", token=body["access_token"])
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["id"], "admin")
        self.assertNotIn("password_hash", body["data"])
        self.assertNotIn(self.password, json.dumps(body))

    async def test_wrong_password_and_unknown_email_have_same_response(self):
        results = []
        for email in ("admin@example.com", "unknown@example.com"):
            status, body, headers = await self.request("POST", "/auth/login", {
                "username": email, "password": "incorrect password",
            }, form=True)
            self.assertEqual(status, 401)
            self.assertEqual(headers[b"www-authenticate"], b"Bearer")
            results.append(body)
        self.assertEqual(results[0], results[1])

    async def test_no_token_rejected_across_business_routes(self):
        for path in ("/auth/me", "/users", "/organizations", "/customer", "/conversations", "/messages/any", "/db-health"):
            with self.subTest(path=path):
                status, _, headers = await self.request("GET", path)
                self.assertEqual(status, 401)
                self.assertEqual(headers[b"www-authenticate"], b"Bearer")
        self.assertEqual((await self.request("GET", "/health"))[0], 200)

    async def test_invalid_token_and_missing_configuration_fail_closed(self):
        self.assertEqual((await self.request("GET", "/auth/me", token="invalid"))[0], 401)
        with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
            status, body, _ = await self.request("GET", "/auth/me", token="invalid")
            self.assertEqual(status, 503)
            self.assertNotIn("JWT_SECRET_KEY", json.dumps(body))

    async def test_admin_user_list_is_tenant_scoped_and_other_roles_denied(self):
        status, body, _ = await self.request("GET", "/users", token=create_access_token("admin"))
        self.assertEqual(status, 200)
        self.assertEqual({row["id"] for row in body["data"]}, {"admin", "supervisor", "agent"})
        for role in ("agent", "supervisor"):
            self.assertEqual((await self.request("GET", "/users", token=create_access_token(role)))[0], 403)
        self.assertEqual((await self.request("GET", "/users/foreign", token=create_access_token("admin")))[0], 404)

    async def test_admin_and_supervisor_access_organization_conversations_only(self):
        for user_id in ("admin", "supervisor"):
            with self.subTest(user_id=user_id):
                token = create_access_token(user_id)
                status, body, _ = await self.request("GET", "/conversations", token=token)
                self.assertEqual(status, 200)
                self.assertEqual({row["id"] for row in body["data"]}, {"assigned", "unassigned"})
                for conversation_id in ("assigned", "unassigned"):
                    self.assertEqual((await self.request(
                        "GET", "/conversations/" + conversation_id, token=token,
                    ))[0], 200)
                self.assertEqual((await self.request(
                    "GET", "/conversations/foreign-conversation", token=token,
                ))[0], 404)

    async def test_agent_conversations_are_filtered_and_foreign_access_denied(self):
        token = create_access_token("agent")
        status, body, _ = await self.request("GET", "/conversations", token=token)
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in body["data"]], ["assigned"])
        for conversation_id in ("unassigned", "foreign-conversation"):
            self.assertEqual((await self.request("GET", "/conversations/" + conversation_id, token=token))[0], 404 if conversation_id == "foreign-conversation" else 403)

    async def test_agent_can_reply_as_self_but_cannot_impersonate(self):
        token = create_access_token("agent")
        payload = {"conversation_id": "assigned", "content": "Reply"}
        self.assertEqual((await self.request("POST", "/messages", payload, token))[0], 201)
        for change in ({"sender_type": "AI", "sender_id": None}, {"sender_id": "admin"},
                       {"conversation_id": "unassigned"}, {"conversation_id": "foreign-conversation"}):
            expected = (422 if "sender_type" in change or "sender_id" in change else
                        404 if change.get("conversation_id") == "foreign-conversation" else 403)
            self.assertEqual((await self.request("POST", "/messages", payload | change, token))[0], expected)

    async def test_role_changes_and_deleted_users_take_effect_with_existing_token(self):
        token = create_access_token("admin")
        self.db.get(Users, "admin").role = "AGENT"
        self.db.commit()
        self.assertEqual((await self.request("GET", "/users", token=token))[0], 403)
        self.db.delete(self.db.get(Users, "admin"))
        self.db.commit()
        self.assertEqual((await self.request("GET", "/auth/me", token=token))[0], 401)

    async def test_validation_does_not_echo_credentials(self):
        secret = "sensitive-password-value"
        status, body, _ = await self.request("POST", "/auth/login", {"password": secret}, form=True)
        self.assertEqual(status, 422)
        self.assertNotIn(secret, json.dumps(body))


if __name__ == "__main__":
    unittest.main()
