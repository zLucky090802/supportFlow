import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
    from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.exceptions.auth_exceptions import PermissionDeniedError
from app.models.generated_models import Base, Conversations
from app.routes import conversation, customers, messages, organizations, users
from app.services import authorization_service as authorization


class ASGIClient:
    """Small ASGI harness matching the existing project's dependency-free tests."""
    def __init__(self, app):
        self.app = app

    def request(self, method, path, payload=None):
        async def invoke():
            from urllib.parse import urlsplit
            parsed = urlsplit(path)
            output = []
            body = json.dumps(payload).encode() if payload is not None else b""
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            async def send(message):
                output.append(message)
            scope = {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": parsed.path,
                "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(),
                "root_path": "", "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 123), "server": ("test", 80),
            }
            await self.app(scope, receive, send)
            return SimpleNamespace(status_code=next(item["status"] for item in output if item["type"] == "http.response.start"))
        return asyncio.run(invoke())

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, json):
        return self.request("POST", path, json)

    def patch(self, path, json):
        return self.request("PATCH", path, json)

    def delete(self, path):
        return self.request("DELETE", path)


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.actor = SimpleNamespace(id="agent", organization_id="org", role="AGENT")

    def test_cross_tenant_access_denied(self):
        with self.assertRaises(PermissionDeniedError):
            authorization.require_organization(self.actor, "other")

    def test_agent_access_requires_assignment(self):
        record = SimpleNamespace(organization_id="org", assigned_agent_id="other-agent")
        with patch.object(authorization.conversations, "get_conversation_by_id", return_value=record):
            with self.assertRaises(PermissionDeniedError):
                authorization.require_conversation(None, self.actor, "conversation")
            record.assigned_agent_id = self.actor.id
            self.assertIs(authorization.require_conversation(None, self.actor, "conversation"), record)
            record.organization_id = "other"
            with self.assertRaises(PermissionDeniedError):
                authorization.require_conversation(None, self.actor, "conversation")

    def test_staff_cannot_impersonate_message_sender(self):
        with patch.object(authorization, "require_conversation"):
            for sender_type, sender_id in [("AI", None), ("CUSTOMER", "customer"), ("AGENT", "someone")]:
                with self.subTest(sender_type=sender_type), self.assertRaises(PermissionDeniedError):
                    authorization.require_message_sender(None, self.actor, SimpleNamespace(
                        conversation_id="conversation", sender_type=sender_type, sender_id=sender_id,
                    ))
            authorization.require_message_sender(None, self.actor, SimpleNamespace(
                conversation_id="conversation", sender_type="AGENT", sender_id="agent",
            ))

    def test_lists_filter_tenant_and_assignment_in_database(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, record):
            connection.create_function("char_length", 1, len)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                Conversations(id="own", organization_id="org", customer_id="customer", assigned_agent_id="agent", status="OPEN"),
                Conversations(id="unassigned", organization_id="org", customer_id="customer", status="OPEN"),
                Conversations(id="foreign", organization_id="other", customer_id="customer", assigned_agent_id="agent", status="OPEN"),
            ])
            db.commit()
            self.assertEqual([c.id for c in authorization.list_conversations(db, self.actor)], ["own"])
            self.actor.role = "SUPERVISOR"
            self.assertEqual({c.id for c in authorization.list_conversations(db, self.actor)}, {"own", "unassigned"})


class ProtectedRoutesTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        for module in (conversation, customers, messages, organizations, users):
            self.app.include_router(module.router)
        self.app.dependency_overrides[get_db] = lambda: None
        from fastapi.responses import JSONResponse
        @self.app.exception_handler(PermissionDeniedError)
        async def forbidden(request, exc):
            return JSONResponse(status_code=403, content={"success": False})
        self.client = ASGIClient(self.app)

    def login(self, role="AGENT"):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id="agent", organization_id="org", role=role,
        )

    def test_non_admin_cannot_manage_users(self):
        for role in ("AGENT", "SUPERVISOR"):
            self.login(role)
            for path in ("/users", "/users/agent", "/users/by-email?email=a@example.com"):
                with self.subTest(role=role, path=path):
                    self.assertEqual(self.client.get(path).status_code, 403)

    def test_agent_cannot_manage_customers_or_settings(self):
        self.login()
        self.assertEqual(self.client.get("/customer").status_code, 403)
        self.assertEqual(self.client.patch("/organizations/org", json={"name": "Changed"}).status_code, 403)
        self.assertEqual(self.client.post("/conversations", json={"organization_id": "org", "customer_id": "customer"}).status_code, 403)

    def test_admin_cannot_cross_tenant_or_delete_organization(self):
        self.login("ADMIN")
        self.assertEqual(self.client.get("/users/by-organization/other").status_code, 403)
        self.assertEqual(self.client.get("/conversations/by-organization/other").status_code, 403)
        self.assertEqual(self.client.get("/organizations/other").status_code, 403)
        self.assertEqual(self.client.delete("/organizations/org").status_code, 403)

    def test_foreign_user_update_does_not_write(self):
        self.login("ADMIN")
        foreign = SimpleNamespace(organization_id="other")
        with patch.object(authorization.user_service, "get_user_by_id", return_value=foreign), patch.object(authorization.user_service, "update_user") as update:
            self.assertEqual(self.client.patch("/users/foreign", json={"name": "Changed"}).status_code, 403)
            update.assert_not_called()
