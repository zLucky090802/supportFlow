"""Opt-in tests against the DATABASE_URL used by get_db; no schema changes."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from threading import Event
import unittest
from urllib.parse import urlencode
from uuid import uuid4

from sqlalchemy import delete, event, select, text


@unittest.skipUnless(os.getenv("SUPPORTFLOW_RUN_MYSQL_TESTS") == "1", "MySQL integration is opt-in")
class MySQLPermissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import here: normal test discovery must never connect to the real database.
        from app.db.database import engine, get_db
        from app.main import app
        from app.models.generated_models import Conversations, Customers, Messages, Organizations, Users
        from app.security.passwords import hash_password

        cls.engine, cls.app = engine, app
        cls.get_db = staticmethod(get_db)
        cls.Conversations, cls.Customers, cls.Messages = Conversations, Customers, Messages
        cls.Organizations, cls.Users = Organizations, Users
        if engine.dialect.name != "mysql":
            raise RuntimeError("Run this suite separately with the configured MySQL DATABASE_URL")
        if get_db in app.dependency_overrides:
            raise RuntimeError("Integration requires the real get_db dependency")
        with engine.connect() as connection:
            engines = dict(connection.execute(text(
                "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                "('organizations','customers','users','conversations','messages')"
            )).all())
        if len(engines) != 5 or any(value != "InnoDB" for value in engines.values()):
            raise RuntimeError("Integration requires all five tables to use InnoDB")
        cls.password = "Temporary integration password 123!"
        cls.password_hash = hash_password(cls.password)

    @contextmanager
    def session(self):
        dependency = self.get_db()
        db = next(dependency)
        try:
            yield db
        finally:
            dependency.close()

    def setUp(self):
        self.ids = {key: str(uuid4()) for key in (
            "org", "other", "customer", "foreign_customer", "admin", "supervisor",
            "agent", "second", "foreign", "conversation", "foreign_conversation",
        )}
        self.addCleanup(self.cleanup_rows)
        with self.session() as db:
            db.add_all([self.Organizations(id=self.ids[key], name="QA temporary") for key in ("org", "other")])
            db.commit()
            for key, org in (("customer", "org"), ("foreign_customer", "other")):
                db.add(self.Customers(id=self.ids[key], organization_id=self.ids[org], name="QA temporary",
                                      email=self.ids[key] + "@example.com"))
            for key, role, org in (("admin", "ADMIN", "org"), ("supervisor", "SUPERVISOR", "org"),
                                   ("agent", "AGENT", "org"), ("second", "AGENT", "org"),
                                   ("foreign", "AGENT", "other")):
                db.add(self.Users(id=self.ids[key], organization_id=self.ids[org], name="QA temporary",
                                  email=self.ids[key] + "@example.com", role=role, password_hash=self.password_hash))
            db.commit()
            db.add_all([
                self.Conversations(id=self.ids["conversation"], organization_id=self.ids["org"],
                                   customer_id=self.ids["customer"], assigned_agent_id=self.ids["agent"], status="OPEN"),
                self.Conversations(id=self.ids["foreign_conversation"], organization_id=self.ids["other"],
                                   customer_id=self.ids["foreign_customer"], status="OPEN"),
            ])
            db.commit()

    def cleanup_rows(self):
        # Only exact UUIDs created by this test. This is fixture cleanup, never API CRUD.
        conversation_ids = [self.ids[key] for key in ("conversation", "foreign_conversation")]
        with self.session() as db:
            db.execute(delete(self.Messages).where(self.Messages.conversation_id.in_(conversation_ids)))
            db.execute(delete(self.Conversations).where(self.Conversations.id.in_(conversation_ids)))
            db.execute(delete(self.Users).where(self.Users.id.in_([self.ids[key] for key in
                       ("admin", "supervisor", "agent", "second", "foreign")])))
            db.execute(delete(self.Customers).where(self.Customers.id.in_([
                self.ids["customer"], self.ids["foreign_customer"]])))
            db.execute(delete(self.Organizations).where(self.Organizations.id.in_([
                self.ids["org"], self.ids["other"]])))
            db.commit()
            for model in (self.Organizations, self.Customers, self.Users, self.Conversations):
                self.assertIsNone(db.scalar(select(model.id).where(model.id.in_(list(self.ids.values())))))
            self.assertIsNone(db.scalar(select(self.Messages.id).where(self.Messages.conversation_id.in_(conversation_ids))))

    def request(self, method, path, body=None, token=None, form=False):
        async def call():
            events = []
            payload = urlencode(body).encode() if form else json.dumps(body).encode() if body is not None else b""
            headers = [(b"content-type", b"application/x-www-form-urlencoded" if form else b"application/json")]
            if token:
                headers.append((b"authorization", ("Bearer " + token).encode()))
            async def receive():
                return {"type": "http.request", "body": payload, "more_body": False}
            async def send(message):
                events.append(message)
            await self.app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                            "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                            "root_path": "", "query_string": b"", "headers": headers,
                            "client": ("127.0.0.1", 5555), "server": ("integration", 80)}, receive, send)
            status = next(item["status"] for item in events if item["type"] == "http.response.start")
            response = b"".join(item.get("body", b"") for item in events if item["type"] == "http.response.body")
            return status, json.loads(response)
        return asyncio.run(call())

    def login(self, role):
        status, body = self.request("POST", "/auth/login", {
            "username": self.ids[role] + "@example.com", "password": self.password,
        }, form=True)
        self.assertEqual(status, 200)
        return body["access_token"]

    def test_authenticated_assignment_privacy_and_messages(self):
        tokens = {role: self.login(role) for role in ("admin", "supervisor", "agent", "second")}
        path = "/conversations/" + self.ids["conversation"]
        for role in ("admin", "supervisor", "agent"):
            foreign = self.request("GET", "/conversations/" + self.ids["foreign_conversation"], token=tokens[role])
            missing = self.request("GET", "/conversations/" + str(uuid4()), token=tokens[role])
            self.assertEqual(foreign, missing)
            self.assertEqual(foreign[0], 404)
        self.assertEqual(self.request("PATCH", path + "/assign", {"agent_id": self.ids["agent"]}, tokens["agent"])[0], 403)
        for invalid in ("foreign", "admin"):
            self.assertEqual(self.request("PATCH", path + "/assign", {"agent_id": self.ids[invalid]}, tokens["admin"])[0],
                             404 if invalid == "foreign" else 400)
        self.assertEqual(self.request("PATCH", path + "/assign", {"agent_id": self.ids["second"]}, tokens["supervisor"])[0], 200)
        self.assertEqual(self.request("GET", "/conversations/me", token=tokens["agent"])[1]["data"], [])
        mine = self.request("GET", "/conversations/me", token=tokens["second"])[1]["data"]
        self.assertEqual([item["id"] for item in mine], [self.ids["conversation"]])
        message = {"conversation_id": self.ids["conversation"], "sender_type": "AGENT",
                   "sender_id": self.ids["second"], "content": "MySQL integration message"}
        self.assertEqual(self.request("POST", "/messages", message, tokens["second"])[0], 201)
        status, body = self.request("PATCH", path, {"status": "RESOLVED"}, tokens["second"])
        self.assertEqual(status, 200)
        self.assertIsNotNone(body["data"]["resolved_at"])
        self.assertEqual(self.request("PATCH", path + "/unassign", token=tokens["admin"])[0], 200)
        self.assertEqual(self.request("POST", "/messages", message, tokens["second"])[0], 403)

    def test_reassignment_revokes_waiting_message_and_status_writes(self):
        from app.exceptions.auth_exceptions import PermissionDeniedError
        from app.repositories.conversations_repository import get_conversation_for_update
        from app.routes.conversation import update_conversation
        from app.routes.messages import create_message
        from app.schemas.conversations import ConversationUpdate
        from app.schemas.messages import MessageCreate

        for operation in ("message", "status"):
            with self.subTest(operation=operation), self.session() as owner:
                row = get_conversation_for_update(owner, self.ids["conversation"])
                row.assigned_agent_id = self.ids["agent"]
                owner.commit()
                row = get_conversation_for_update(owner, self.ids["conversation"])
                row.assigned_agent_id = self.ids["second"]
                owner.flush()
                waiting, finished = Event(), Event()

                def worker():
                    with self.session() as db:
                        actor = db.get(self.Users, self.ids["agent"])
                        stale = db.get(self.Conversations, self.ids["conversation"])
                        self.assertEqual(stale.assigned_agent_id, self.ids["agent"])
                        def before_execute(conn, cursor, statement, parameters, context, many):
                            if "FOR UPDATE" in statement.upper():
                                waiting.set()
                        event.listen(db.connection(), "before_cursor_execute", before_execute)
                        try:
                            with self.assertRaises(PermissionDeniedError):
                                if operation == "message":
                                    create_message(MessageCreate(conversation_id=self.ids["conversation"],
                                        sender_type="AGENT", sender_id=actor.id, content="Must be rejected"), actor, db)
                                else:
                                    update_conversation(self.ids["conversation"], ConversationUpdate(status="RESOLVED"), actor, db)
                        finally:
                            finished.set()

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(worker)
                    try:
                        self.assertTrue(waiting.wait(5), "Worker never attempted the locking read")
                        self.assertFalse(finished.wait(0.2), "Write should wait for the assignment lock")
                    finally:
                        owner.commit()
                    future.result(timeout=10)
                owner.expire_all()
                self.assertEqual(owner.get(self.Conversations, self.ids["conversation"]).status, "OPEN")
                self.assertIsNone(owner.scalar(select(self.Messages.id).where(
                    self.Messages.conversation_id == self.ids["conversation"])))


if __name__ == "__main__":
    unittest.main()
