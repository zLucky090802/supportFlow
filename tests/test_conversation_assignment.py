"""Assignment API behavior with SQLite; MySQL locking is tested separately."""
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from sqlalchemy.dialects import mysql

import test_auth_api as auth_fixture
from app.models.generated_models import Conversations, Users
from app.repositories import conversations_repository
from app.security.tokens import create_access_token
from app.services import conversation_assignment_service as assignments


class ConversationAssignmentTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(auth_fixture.AuthAPITests.setUpClass.__func__)
    request = auth_fixture.AuthAPITests.request

    def setUp(self):
        auth_fixture.AuthAPITests.setUp(self)
        self.db.add(Users(id="agent2", organization_id="org", name="Second Agent",
                          email="agent2@example.com", password_hash=self.password_hash, role="AGENT"))
        self.db.commit()

    async def check(self, actor, method, path, expected, body=None):
        status, response, _ = await self.request(method, path, body, create_access_token(actor))
        self.assertEqual(status, expected, (actor, path, response))
        return response

    async def test_assignment_reassignment_unassignment_and_preserved_resolution(self):
        conversation = self.db.get(Conversations, "unassigned")
        conversation.status = "RESOLVED"
        conversation.resolved_at = datetime(2026, 9, 29, 12)
        self.db.commit()
        for actor, agent_id in (("admin", "agent"), ("supervisor", "agent2")):
            result = await self.check(actor, "PATCH", "/conversations/unassigned/assign", 200,
                                      {"agent_id": agent_id})
            self.assertEqual(result["data"]["assigned_agent_id"], agent_id)
            self.assertEqual(result["data"]["status"], "RESOLVED")
            self.assertEqual(result["data"]["resolved_at"], "2026-09-29T12:00:00")
        result = await self.check("supervisor", "PATCH", "/conversations/unassigned/unassign", 200)
        self.assertIsNone(result["data"]["assigned_agent_id"])
        self.assertEqual(result["data"]["status"], "RESOLVED")

    async def test_agents_cannot_assign_self_reassign_or_unassign(self):
        for conversation_id in ("assigned", "unassigned"):
            await self.check("agent", "PATCH", f"/conversations/{conversation_id}/assign", 403,
                             {"agent_id": "agent"})
            await self.check("agent", "PATCH", f"/conversations/{conversation_id}/unassign", 403)
        self.assertEqual(self.db.get(Conversations, "assigned").assigned_agent_id, "agent")
        self.assertIsNone(self.db.get(Conversations, "unassigned").assigned_agent_id)

    async def test_missing_and_cross_tenant_targets_have_identical_404(self):
        for actor in ("admin", "supervisor"):
            results = []
            for conversation_id in ("foreign-conversation", "missing"):
                results.append(await self.check(actor, "PATCH", f"/conversations/{conversation_id}/assign", 404,
                                                {"agent_id": "agent"}))
                results.append(await self.check(actor, "PATCH", f"/conversations/{conversation_id}/unassign", 404))
            for agent_id in ("foreign", "missing"):
                results.append(await self.check(actor, "PATCH", "/conversations/unassigned/assign", 404,
                                                {"agent_id": agent_id}))
            self.assertTrue(all(result == results[0] for result in results))
        self.assertIsNone(self.db.get(Conversations, "unassigned").assigned_agent_id)

    async def test_invalid_role_and_body_do_not_assign(self):
        for agent_id in ("admin", "supervisor"):
            await self.check("admin", "PATCH", "/conversations/unassigned/assign", 400,
                             {"agent_id": agent_id})
        for payload in ({}, {"agent_id": None}, {"agent_id": "agent", "organization_id": "other"}):
            await self.check("admin", "PATCH", "/conversations/unassigned/assign", 422, payload)
        self.assertIsNone(self.db.get(Conversations, "unassigned").assigned_agent_id)

    async def test_personal_and_agent_lists_follow_latest_assignment(self):
        result = await self.check("agent", "GET", "/conversations/me", 200)
        self.assertEqual([row["id"] for row in result["data"]], ["assigned"])
        await self.check("supervisor", "PATCH", "/conversations/assigned/assign", 200, {"agent_id": "agent2"})
        self.assertEqual((await self.check("agent", "GET", "/conversations/me", 200))["data"], [])
        for actor in ("admin", "supervisor"):
            result = await self.check(actor, "GET", "/conversations/by-agent/agent2", 200)
            self.assertEqual([row["id"] for row in result["data"]], ["assigned"])
            await self.check(actor, "GET", "/conversations/by-agent/foreign", 404)
            await self.check(actor, "GET", "/conversations/by-agent/missing", 404)
        await self.check("agent", "GET", "/conversations/by-agent/agent", 403)
        await self.check("agent", "PATCH", "/conversations/assigned", 403, {"status": "CLOSED"})
        await self.check("agent2", "PATCH", "/conversations/assigned", 200, {"status": "RESOLVED"})

    async def test_lock_is_requested_for_assignment_and_status(self):
        original = conversations_repository.get_conversation_for_update
        with patch.object(conversations_repository, "get_conversation_for_update", wraps=original) as lock:
            await self.check("admin", "PATCH", "/conversations/unassigned/assign", 200, {"agent_id": "agent"})
            lock.assert_called_once_with(self.db, "unassigned")
            lock.reset_mock()
            await self.check("agent", "PATCH", "/conversations/unassigned", 200, {"status": "RESOLVED"})
            lock.assert_called_once_with(self.db, "unassigned")


class AssignmentTransactionTests(unittest.TestCase):
    def test_lock_query_uses_for_update_and_refreshes_identity_map(self):
        db = Mock()
        conversations_repository.get_conversation_for_update(db, "conversation")
        statement = db.scalar.call_args.args[0]
        self.assertIn("FOR UPDATE", str(statement.compile(dialect=mysql.dialect())))
        self.assertTrue(statement.get_execution_options()["populate_existing"])

    def test_failure_after_lock_rolls_back(self):
        db = Mock()
        with patch.object(assignments.authorization, "require_conversation", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                assignments.assign_conversation(db, Mock(), "conversation", "agent")
        db.rollback.assert_called_once()
