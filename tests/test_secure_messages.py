"""JWT sender identity and equivalent access policy on both message URLs."""
from datetime import datetime, timedelta
import unittest

import test_auth_api as fixture
from app.models.generated_models import Messages
from app.security.tokens import create_access_token


class SecureMessagesTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(fixture.AuthAPITests.setUpClass.__func__)
    setUp = fixture.AuthAPITests.setUp
    request = fixture.AuthAPITests.request

    async def post(self, role, conversation="assigned", nested=True, extra=None):
        path = f"/conversations/{conversation}/messages" if nested else "/messages"
        body = {"content": "  Hello from staff  "}
        if not nested:
            body["conversation_id"] = conversation
        body.update(extra or {})
        return await self.request("POST", path, body, create_access_token(role))

    async def test_both_urls_derive_sender_for_all_staff_roles(self):
        for role in ("admin", "supervisor", "agent"):
            for nested in (True, False):
                with self.subTest(role=role, nested=nested):
                    status, body, _ = await self.post(role, nested=nested)
                    self.assertEqual(status, 201, body)
                    data = body["data"]
                    self.assertEqual((data["sender_id"], data["sender_type"], data["content"]),
                                     (role, "AGENT", "Hello from staff"))
                    self.db.expire_all()
                    self.assertEqual(self.db.get(Messages, data["id"]).sender_id, role)

    async def test_sender_fields_and_other_extra_fields_are_rejected_without_writes(self):
        for nested in (True, False):
            for extra in ({"sender_id": "admin"}, {"sender_id": "agent"},
                          {"sender_type": "AI"}, {"sender_type": "CUSTOMER"},
                          {"sender_type": "AGENT"}, {"organization_id": "other"}):
                with self.subTest(nested=nested, extra=extra):
                    self.assertEqual((await self.post("agent", nested=nested, extra=extra))[0], 422)
        self.assertEqual((await self.post("agent", extra={"conversation_id": "unassigned"}))[0], 422)
        self.assertEqual(self.db.query(Messages).count(), 0)

    async def test_permissions_and_tenant_privacy_on_both_urls(self):
        for nested in (True, False):
            self.assertEqual((await self.post("agent", "unassigned", nested))[0], 403)
            for role in ("admin", "supervisor", "agent"):
                foreign = await self.post(role, "foreign-conversation", nested)
                missing = await self.post(role, "missing", nested)
                self.assertEqual(foreign[:2], missing[:2])
                self.assertEqual(foreign[0], 404)
            for role in ("admin", "supervisor"):
                self.assertEqual((await self.post(role, "unassigned", nested))[0], 201)

    async def test_history_is_chronological_and_read_aliases_enforce_access(self):
        earlier = datetime(2026, 1, 1)
        for ident, when in (("later", earlier + timedelta(seconds=1)), ("earlier", earlier)):
            self.db.add(Messages(id=ident, conversation_id="assigned", sender_type="AGENT",
                                 sender_id="agent", content=ident, created_at=when))
        self.db.add(Messages(id="foreign-message", conversation_id="foreign-conversation",
                             sender_type="CUSTOMER", sender_id="foreign-customer", content="Private"))
        self.db.commit()
        for role in ("admin", "supervisor", "agent"):
            token = create_access_token(role)
            for path in ("/conversations/assigned/messages", "/messages/by-conversation/assigned"):
                status, body, _ = await self.request("GET", path, token=token)
                self.assertEqual(status, 200)
                self.assertEqual([row["id"] for row in body["data"]], ["earlier", "later"])
            self.assertEqual((await self.request("GET", "/messages/earlier", token=token))[0], 200)
            for path in ("/conversations/foreign-conversation/messages", "/messages/foreign-message"):
                self.assertEqual((await self.request("GET", path, token=token))[0], 404)
        self.assertEqual((await self.request("GET", "/conversations/unassigned/messages",
                                            token=create_access_token("agent")))[0], 403)

    async def test_authentication_required_and_no_edit_or_delete(self):
        for path, body in (("/conversations/assigned/messages", {"content": "Hello"}),
                           ("/messages", {"conversation_id": "assigned", "content": "Hello"})):
            self.assertEqual((await self.request("POST", path, body))[0], 401)
            self.assertEqual((await self.request("POST", path, body, "invalid-token"))[0], 401)
        for method in ("PATCH", "PUT", "DELETE"):
            self.assertEqual((await self.request(method, "/messages/id", token=create_access_token("admin")))[0], 405)

    async def test_blank_content_is_rejected(self):
        for nested in (True, False):
            self.assertEqual((await self.post("agent", nested=nested, extra={"content": " \n "}))[0], 422)
        self.assertEqual(self.db.query(Messages).count(), 0)
