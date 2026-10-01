"""Conversation lifecycle and authorization across authenticated API modules."""
import unittest
from unittest.mock import Mock, patch

import test_auth_api as fixture
from app.exceptions.auth_exceptions import PermissionDeniedError
from app.exceptions.conversation_exceptions import InvalidConversationStatusError
from app.models.generated_models import Conversations, Messages, Users
from app.schemas.conversations import ConversationUpdate
from app.security.tokens import create_access_token
from app.services import conversations


class ConversationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixture.AuthAPITests.setUpClass.__func__)
    setUp = fixture.AuthAPITests.setUp
    request = fixture.AuthAPITests.request

    async def call(self, actor, method, path, body=None, expected=200):
        status, result, _ = await self.request(method, path, body, create_access_token(actor))
        self.assertEqual(status, expected, result)
        return result

    async def test_login_assignment_message_and_resolution_full_flow(self):
        tokens = {}
        for actor in ("admin", "supervisor", "agent"):
            status, result, _ = await self.request("POST", "/auth/login", {
                "username": actor + "@example.com", "password": self.password,
            }, form=True)
            self.assertEqual(status, 200)
            tokens[actor] = result["access_token"]
        status, result, _ = await self.request("POST", "/conversations", {
            "organization_id": "org", "customer_id": "customer",
        }, tokens["admin"])
        self.assertEqual(status, 201)
        conversation_id = result["data"]["id"]
        self.assertEqual(result["data"]["status"], "OPEN")
        path = "/conversations/" + conversation_id
        self.assertEqual((await self.request("PATCH", path + "/assign", {"agent_id": "agent"}, tokens["supervisor"]))[0], 200)
        status, result, _ = await self.request("GET", "/conversations/me", token=tokens["agent"])
        self.assertEqual(status, 200)
        self.assertIn(conversation_id, [row["id"] for row in result["data"]])
        status, result, _ = await self.request("POST", path + "/messages", {"content": "Resolved with customer"}, tokens["agent"])
        self.assertEqual(status, 201)
        self.assertEqual(result["data"]["sender_id"], "agent")
        message_id = result["data"]["id"]
        for actor in tokens:
            self.assertEqual((await self.request("GET", "/messages/" + message_id, token=tokens[actor]))[0], 200)
        status, result, _ = await self.request("PATCH", path, {"status": "RESOLVED"}, tokens["agent"])
        self.assertEqual(status, 200)
        self.assertIsNotNone(result["data"]["resolved_at"])
        status, history, _ = await self.request("GET", path + "/messages", token=tokens["supervisor"])
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in history["data"]], [message_id])

    async def test_status_lifecycle_for_every_staff_role(self):
        for actor in ("admin", "supervisor", "agent"):
            path = "/conversations/assigned"
            await self.call(actor, "PATCH", path, {"status": "OPEN"})
            resolved = await self.call(actor, "PATCH", path, {"status": "RESOLVED"})
            timestamp = resolved["data"]["resolved_at"]
            self.assertIsNotNone(timestamp)
            for status in ("RESOLVED", "CLOSED"):
                result = await self.call(actor, "PATCH", path, {"status": status})
                self.assertEqual(result["data"]["resolved_at"], timestamp)
            for status in ("OPEN", "ESCALATED"):
                await self.call(actor, "PATCH", path, {"status": "RESOLVED"})
                result = await self.call(actor, "PATCH", path, {"status": status})
                self.assertIsNone(result["data"]["resolved_at"])
            result = await self.call(actor, "PATCH", path, {"status": "CLOSED"})
            self.assertIsNone(result["data"]["resolved_at"])

    async def test_denied_status_updates_leave_conversations_unchanged(self):
        for actor in ("admin", "supervisor", "agent"):
            for status in ("OPEN", "ESCALATED", "RESOLVED", "CLOSED"):
                foreign = await self.call(actor, "PATCH", "/conversations/foreign-conversation", {"status": status}, 404)
                absent = await self.call(actor, "PATCH", "/conversations/missing", {"status": status}, 404)
                self.assertEqual(foreign, absent)
                await self.call("agent", "PATCH", "/conversations/unassigned", {"status": status}, 403)
        self.db.expire_all()
        for ident in ("foreign-conversation", "unassigned"):
            row = self.db.get(Conversations, ident)
            self.assertEqual(row.status, "OPEN")
            self.assertIsNone(row.resolved_at)

    async def test_reassignment_revokes_access_across_conversation_and_message_aliases(self):
        self.db.add(Users(id="second-agent", organization_id="org", role="AGENT", name="Second",
                          email="second@example.com", password_hash=self.password_hash))
        self.db.commit()
        message = await self.call("agent", "POST", "/conversations/assigned/messages", {"content": "Before reassignment"}, 201)
        await self.call("supervisor", "PATCH", "/conversations/assigned/assign", {"agent_id": "second-agent"})
        for actor, expected in (("agent", 403), ("second-agent", 200), ("supervisor", 200), ("admin", 200)):
            for path in ("/conversations/assigned", "/conversations/assigned/messages",
                         "/messages/by-conversation/assigned", "/messages/" + message["data"]["id"]):
                await self.call(actor, "GET", path, expected=expected)
            await self.call(actor, "PATCH", "/conversations/assigned", {"status": "ESCALATED"}, expected)
            for path, body in (("/messages", {"conversation_id": "assigned", "content": "Reply"}),
                               ("/conversations/assigned/messages", {"content": "Reply"})):
                await self.call(actor, "POST", path, body, 403 if expected == 403 else 201)
        for path in ("/conversations", "/conversations/me", "/conversations/by-organization/org", "/conversations/by-customer/customer"):
            result = await self.call("agent", "GET", path)
            self.assertEqual(result["data"], [])
        await self.call("admin", "PATCH", "/conversations/assigned/unassign")
        await self.call("second-agent", "GET", "/conversations/assigned", expected=403)
        await self.call("second-agent", "PATCH", "/conversations/assigned", {"status": "RESOLVED"}, 403)

    async def test_assignment_and_tenant_fields_cannot_bypass_dedicated_endpoints(self):
        count = self.db.query(Conversations).count()
        for actor in ("admin", "supervisor", "agent"):
            for extra in ({"assigned_agent_id": "agent"}, {"status": "RESOLVED"}, {"resolved_at": "2026-01-01T00:00:00"}):
                await self.call(actor, "POST", "/conversations", {
                    "organization_id": "org", "customer_id": "customer", **extra,
                }, 422)
            for extra in ({"assigned_agent_id": "agent"}, {"organization_id": "other"},
                          {"customer_id": "foreign-customer"}, {"resolved_at": None}):
                await self.call(actor, "PATCH", "/conversations/unassigned", {"status": "OPEN", **extra}, 422)
        self.assertEqual(self.db.query(Conversations).count(), count)
        self.assertIsNone(self.db.get(Conversations, "unassigned").assigned_agent_id)


class ConversationServiceTransactionTests(unittest.TestCase):
    def test_denial_rolls_back_and_does_not_write(self):
        db = Mock()
        with patch("app.services.authorization_service.require_conversation", side_effect=PermissionDeniedError()) as guard, patch.object(conversations, "_update_status") as update:
            with self.assertRaises(PermissionDeniedError):
                conversations.update_staff_conversation(db, "actor", ConversationUpdate(status="RESOLVED"), "conversation")
        guard.assert_called_once_with(db, "actor", "conversation", lock=True)
        update.assert_not_called()
        db.rollback.assert_called_once()

    def test_service_rejects_invalid_status_even_if_schema_was_mutated(self):
        db = Mock()
        data = ConversationUpdate(status="OPEN")
        data.status = "UNKNOWN"
        with patch.object(conversations.conversations_repository, "get_conversation_by_id", return_value=Conversations(id="conversation", status="OPEN")), patch.object(conversations.conversations_repository, "update_conversation") as write:
            with self.assertRaises(InvalidConversationStatusError):
                conversations.update_conversation(db, data, "conversation")
        write.assert_not_called()

    def test_locked_row_drives_status_without_snapshot_reread(self):
        from datetime import datetime
        db = Mock()
        timestamp = datetime(2026, 1, 1)
        row = Conversations(id="conversation", status="RESOLVED", resolved_at=timestamp)
        with patch("app.services.authorization_service.require_conversation", return_value=row), patch.object(conversations.conversations_repository, "get_conversation_by_id") as read, patch.object(conversations.conversations_repository, "update_conversation", return_value=row) as write:
            result = conversations.update_staff_conversation(db, "actor", ConversationUpdate(status="CLOSED"), "conversation")
        self.assertIs(result, row)
        read.assert_not_called()
        write.assert_called_once_with(db=db, conversation_id="conversation", status="CLOSED", resolved_at=timestamp)
