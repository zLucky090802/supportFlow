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
            return status, json.loads(response) if response else None
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
        message = {"conversation_id": self.ids["conversation"], "content": "MySQL integration message"}
        status, response = self.request("POST", "/messages", message, tokens["second"])
        self.assertEqual(status, 201)
        self.assertEqual(response["data"]["sender_id"], self.ids["second"])
        self.assertEqual(response["data"]["sender_type"], "AGENT")
        for role in ("admin", "supervisor", "second"):
            status, response = self.request("POST", path + "/messages", {"content": "Nested message"}, tokens[role])
            self.assertEqual(status, 201)
            self.assertEqual(response["data"]["sender_id"], self.ids[role])
            self.assertEqual(response["data"]["sender_type"], "AGENT")
        self.assertEqual(self.request("POST", path + "/messages", {"content": "Spoof", "sender_type": "AI"}, tokens["admin"])[0], 422)
        self.assertEqual(self.request("POST", "/messages", message | {"sender_id": self.ids["admin"]}, tokens["second"])[0], 422)
        status, history = self.request("GET", path + "/messages", token=tokens["second"])
        self.assertEqual(status, 200)
        self.assertEqual(len(history["data"]), 4)
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
        from app.schemas.messages import StaffMessageCreate

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
                                    create_message(StaffMessageCreate(conversation_id=self.ids["conversation"],
                                        content="Must be rejected"), actor, db)
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

    def test_status_lifecycle_and_access_after_reassignment(self):
        tokens = {role: self.login(role) for role in ("admin", "supervisor", "agent", "second")}
        path = "/conversations/" + self.ids["conversation"]
        for role in ("admin", "supervisor", "agent"):
            with self.subTest(role=role):
                self.assertEqual(self.request("PATCH", path, {"status": "OPEN"}, tokens[role])[0], 200)
                status, resolved = self.request("PATCH", path, {"status": "RESOLVED"}, tokens[role])
                self.assertEqual(status, 200)
                timestamp = resolved["data"]["resolved_at"]
                self.assertIsNotNone(timestamp)
                for state in ("RESOLVED", "CLOSED"):
                    status, result = self.request("PATCH", path, {"status": state}, tokens[role])
                    self.assertEqual(status, 200)
                    self.assertEqual(result["data"]["resolved_at"], timestamp)
                for state in ("ESCALATED", "OPEN"):
                    status, result = self.request("PATCH", path, {"status": state}, tokens[role])
                    self.assertEqual(status, 200)
                    self.assertIsNone(result["data"]["resolved_at"])
                foreign = "/conversations/" + self.ids["foreign_conversation"]
                self.assertEqual(self.request("PATCH", foreign, {"status": "CLOSED"}, tokens[role])[0], 404)
                self.assertEqual(self.request("PATCH", path, {"status": "CLOSED", "assigned_agent_id": self.ids["second"]}, tokens[role])[0], 422)
        status, result = self.request("POST", path + "/messages", {"content": "Preserved history"}, tokens["agent"])
        self.assertEqual(status, 201)
        message_path = "/messages/" + result["data"]["id"]
        self.assertEqual(self.request("PATCH", path + "/assign", {"agent_id": self.ids["second"]}, tokens["supervisor"])[0], 200)
        for url in (path, path + "/messages", "/messages/by-conversation/" + self.ids["conversation"], message_path):
            self.assertEqual(self.request("GET", url, token=tokens["agent"])[0], 403)
            self.assertEqual(self.request("GET", url, token=tokens["second"])[0], 200)
        self.assertEqual(self.request("PATCH", path, {"status": "RESOLVED"}, tokens["agent"])[0], 403)
        self.assertEqual(self.request("POST", path + "/messages", {"content": "Denied"}, tokens["agent"])[0], 403)
        with self.session() as db:
            row = db.get(self.Conversations, self.ids["conversation"])
            self.assertEqual((row.status, row.resolved_at, row.assigned_agent_id), ("OPEN", None, self.ids["second"]))
            other = db.get(self.Conversations, self.ids["foreign_conversation"])
            self.assertEqual(other.status, "OPEN")

    def test_users_customers_organizations_role_and_tenant_matrix(self):
        tokens = {role: self.login(role) for role in ("admin", "supervisor", "agent")}
        org_path = "/organizations/" + self.ids["org"]
        customer_path = "/customer/" + self.ids["customer"]
        user_path = "/users/" + self.ids["second"]
        for role, token in tokens.items():
            with self.subTest(role=role):
                status, body = self.request("GET", "/auth/me", token=token)
                self.assertEqual(status, 200)
                self.assertNotIn("password", json.dumps(body))
                self.assertNotIn("scrypt", json.dumps(body))
                status, body = self.request("GET", "/organizations", token=token)
                self.assertEqual(status, 200)
                self.assertEqual([row["id"] for row in body["data"]], [self.ids["org"]])
                for path, allowed in ((org_path, True), (customer_path, role != "agent"),
                                      (user_path, role == "admin")):
                    self.assertEqual(self.request("GET", path, token=token)[0], 200 if allowed else 403)
                for path, allowed in ((org_path, role == "admin"), (customer_path, role != "agent"),
                                      (user_path, role == "admin")):
                    self.assertEqual(self.request("PATCH", path, {"name": "Integration updated"}, token)[0],
                                     200 if allowed else 403)
                for prefix, key in (("/organizations/", "other"), ("/customer/", "foreign_customer"),
                                    ("/users/", "foreign")):
                    foreign = self.request("GET", prefix + self.ids[key], token=token)
                    missing = self.request("GET", prefix + str(uuid4()), token=token)
                    self.assertEqual(foreign, missing)
                    self.assertEqual(foreign[0], 404)
                    self.assertEqual(self.request("PATCH", prefix + self.ids[key], {"name": "Denied"}, token)[0], 404)
        self.assertEqual(self.request("PATCH", user_path, {"role": "OWNER"}, tokens["admin"])[0], 400)
        # A real role change is reflected when reusing an already-issued JWT.
        self.assertEqual(self.request("PATCH", "/users/" + self.ids["admin"], {"role": "AGENT"}, tokens["admin"])[0], 200)
        self.assertEqual(self.request("GET", "/users", token=tokens["admin"])[0], 403)
        with self.session() as db:
            for model, key in ((self.Organizations, "other"), (self.Customers, "foreign_customer"), (self.Users, "foreign")):
                self.assertEqual(db.get(model, self.ids[key]).name, "QA temporary")


if __name__ == "__main__":
    unittest.main()
