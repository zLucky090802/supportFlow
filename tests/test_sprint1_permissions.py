"""Independent HTTP permission matrix; real JWTs and isolated SQLite only."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_auth_api as auth_fixture
from app.exceptions.auth_exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.generated_models import Conversations, Customers, Messages, Organizations, Users
from app.security.tokens import create_access_token
from app.services import authorization_service as authorization


class Sprint1PermissionTests(unittest.IsolatedAsyncioTestCase):
    # Reuse setup/request helpers without inheriting or rediscovering auth tests.
    setUpClass = classmethod(auth_fixture.AuthAPITests.setUpClass.__func__)
    request = auth_fixture.AuthAPITests.request

    def setUp(self):
        auth_fixture.AuthAPITests.setUp(self)
        for conversation_id in ("assigned", "unassigned", "foreign-conversation"):
            self.db.add(Messages(
                id="message-" + conversation_id, conversation_id=conversation_id,
                sender_type="AI", content="History " + conversation_id,
            ))
        self.db.commit()

    async def check(self, actor, method, path, expected, body=None):
        status, response, _ = await self.request(method, path, body, create_access_token(actor))
        self.assertEqual(status, expected, (actor, method, path, response))
        if expected == 403:
            self.assertFalse(response["success"])
            self.assertIsNone(response["data"])
        return response

    async def test_user_crud_role_matrix(self):
        for actor in ("admin", "supervisor", "agent"):
            allowed = actor == "admin"
            payload = {"organization_id": "org", "name": "Created", "email": actor + "-new@example.com",
                       "password": self.password, "role": "AGENT"}
            with self.subTest(actor=actor):
                response = await self.check(actor, "POST", "/users", 201 if allowed else 403, payload)
                for path in ("/users", "/users/agent", "/users/by-organization/org"):
                    await self.check(actor, "GET", path, 200 if allowed else 403)
                target = response["data"]["id"] if allowed else "supervisor"
                await self.check(actor, "PATCH", "/users/" + target, 200 if allowed else 403, {"name": "Changed"})
                if allowed:
                    self.db.expire_all()
                    self.assertEqual(self.db.get(Users, target).name, "Changed")
                await self.check(actor, "DELETE", "/users/" + target, 204 if allowed else 403)
                if allowed:
                    self.db.expire_all()
                    self.assertIsNone(self.db.get(Users, target))
        self.db.expire_all()
        self.assertEqual(self.db.get(Users, "supervisor").name, "supervisor")

    async def test_all_roles_cross_tenant_user_reads_and_writes_denied(self):
        for actor in ("admin", "supervisor", "agent"):
            for path in ("/users/foreign", "/users/by-organization/other"):
                await self.check(actor, "GET", path, 404)
            await self.check(actor, "POST", "/users", 404, {
                "organization_id": "other", "name": "Blocked", "email": "blocked@example.com",
                "password": self.password, "role": "ADMIN",
            })
            await self.check(actor, "PATCH", "/users/foreign", 404, {"name": "Blocked"})
            await self.check(actor, "DELETE", "/users/foreign", 404)
        self.db.expire_all()
        self.assertEqual(self.db.get(Users, "foreign").name, "foreign")
        self.assertEqual(self.db.query(Users).count(), 4)

    async def test_conversation_creation_role_and_tenant_matrix(self):
        for actor in ("admin", "supervisor", "agent"):
            response = await self.check(actor, "POST", "/conversations", 403 if actor == "agent" else 201,
                                       {"organization_id": "org", "customer_id": "customer"})
            if actor != "agent":
                self.assertEqual(response["data"]["status"], "OPEN")
                self.assertEqual(response["data"]["organization_id"], "org")
            for payload in ({"organization_id": "other", "customer_id": "foreign-customer"},
                            {"organization_id": "org", "customer_id": "foreign-customer"}):
                await self.check(actor, "POST", "/conversations", 404, payload)
        self.assertEqual(self.db.query(Conversations).count(), 5)

    async def test_all_roles_cross_tenant_customer_and_organization_operations_denied(self):
        for actor in ("admin", "supervisor", "agent"):
            for path in ("/customer/foreign-customer", "/customer/organizations/other/customers", "/organizations/other"):
                await self.check(actor, "GET", path, 404)
            await self.check(actor, "POST", "/customer", 404, {
                "organization_id": "other", "name": "Blocked", "email": "blocked@example.com",
            })
            for path in ("/customer/foreign-customer", "/organizations/other"):
                await self.check(actor, "PATCH", path, 404, {"name": "Blocked"})
                await self.check(actor, "DELETE", path, 403 if path.startswith("/organizations") else 404)
        self.db.expire_all()
        self.assertEqual(self.db.get(Customers, "foreign-customer").name, "Foreign")
        self.assertEqual(self.db.get(Organizations, "other").name, "Other")
        self.assertEqual(self.db.query(Customers).count(), 2)

    async def test_conversation_lists_reads_and_status_updates_matrix(self):
        for actor in ("admin", "supervisor", "agent"):
            expected_ids = {"assigned"} if actor == "agent" else {"assigned", "unassigned"}
            for path in ("/conversations", "/conversations/by-organization/org", "/conversations/by-customer/customer"):
                response = await self.check(actor, "GET", path, 200)
                self.assertEqual({row["id"] for row in response["data"]}, expected_ids)
            for conversation_id in ("assigned", "unassigned", "foreign-conversation"):
                allowed = conversation_id in expected_ids
                path = "/conversations/" + conversation_id
                await self.check(actor, "GET", path, 200 if allowed else 404 if conversation_id == "foreign-conversation" else 403)
                await self.check(actor, "PATCH", path, 200 if allowed else 404 if conversation_id == "foreign-conversation" else 403, {"status": "ESCALATED"})
            for path in ("/conversations/by-organization/other", "/conversations/by-customer/foreign-customer"):
                await self.check(actor, "GET", path, 404)
        self.db.expire_all()
        self.assertEqual(self.db.get(Conversations, "foreign-conversation").status, "OPEN")

    async def test_message_read_history_and_create_matrix(self):
        successful_posts = 0
        for actor in ("admin", "supervisor", "agent"):
            for conversation_id in ("assigned", "unassigned", "foreign-conversation"):
                allowed = conversation_id != "foreign-conversation" and (actor != "agent" or conversation_id == "assigned")
                for path in ("/messages/message-" + conversation_id, "/messages/by-conversation/" + conversation_id):
                    await self.check(actor, "GET", path, 200 if allowed else 404 if conversation_id == "foreign-conversation" else 403)
                response = await self.check(actor, "POST", "/messages", 201 if allowed else 404 if conversation_id == "foreign-conversation" else 403, {
                    "conversation_id": conversation_id, "content": "Reply",
                })
                if allowed:
                    successful_posts += 1
                    self.assertEqual(response["data"]["sender_id"], actor)
        self.assertEqual(self.db.query(Messages).count(), 3 + successful_posts)

    async def test_all_roles_cannot_impersonate_sender(self):
        for actor in ("admin", "supervisor", "agent"):
            for sender_type, sender_id in (("CUSTOMER", "customer"), ("AI", None), ("AGENT", "foreign")):
                await self.check(actor, "POST", "/messages", 422, {
                    "conversation_id": "assigned", "sender_type": sender_type,
                    "sender_id": sender_id, "content": "Spoofed",
                })
        self.assertEqual(self.db.query(Messages).count(), 3)


class PermissionOrderTests(unittest.TestCase):
    def test_tenant_is_checked_before_management_role(self):
        for role in ("ADMIN", "SUPERVISOR", "AGENT"):
            actor = SimpleNamespace(id="actor", role=role, organization_id="org")
            for method in (authorization.require_user_management, authorization.require_customer_management,
                           authorization.require_organization_management):
                with self.subTest(role=role, method=method.__name__), patch.object(authorization, "require_role") as role_check:
                    with self.assertRaises(ResourceNotFoundError):
                        method(actor, "foreign")
                    role_check.assert_not_called()

    def test_user_resource_checks_tenant_before_role(self):
        actor = SimpleNamespace(id="actor", role="AGENT", organization_id="org")
        with patch.object(authorization.user_service, "get_user_by_id", return_value=SimpleNamespace(organization_id="foreign")), \
             patch.object(authorization, "require_role") as role_check:
            with self.assertRaises(ResourceNotFoundError):
                authorization.require_user(None, actor, "foreign-user")
            role_check.assert_not_called()

    def test_conversation_tenant_checks_precede_role(self):
        actor = SimpleNamespace(id="actor", role="AGENT", organization_id="org")
        foreign = SimpleNamespace(organization_id="foreign", assigned_agent_id="actor")
        with patch.object(authorization.conversations, "get_conversation_by_id", return_value=foreign), \
             patch.object(authorization, "require_role") as role_check:
            with self.assertRaises(ResourceNotFoundError):
                authorization.require_conversation(None, actor, "foreign-conversation")
            role_check.assert_not_called()
        with patch.object(authorization.customer_service, "get_customer_by_id", return_value=foreign), \
             patch.object(authorization, "require_role") as role_check:
            with self.assertRaises(ResourceNotFoundError):
                authorization.require_conversation_creation(None, actor, "org", "foreign-customer")
            role_check.assert_not_called()
