"""HTTP responses must not disclose whether another tenant owns an identifier."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from test_authorization import ASGIClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.handlers.auth_handlers import register_auth_handlers
from app.models.generated_models import Base, Organizations, Customers, Conversations, Users, Messages
from app.routes import users, organizations, customers, conversation, messages
from app.services import authorization_service
from app.exceptions.auth_exceptions import ResourceNotFoundError, PermissionDeniedError


class ResourcePrivacyTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        @event.listens_for(engine, "connect")
        def configure(connection, record):
            connection.create_function("char_length", 1, len)
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        self.db.add_all([
            Organizations(id="own", name="Own"), Organizations(id="foreign", name="Foreign"),
            Users(id="foreign", organization_id="foreign", name="Foreign", email="foreign@example.com", password_hash="testhash", role="AGENT"),
            Customers(id="foreign", organization_id="foreign", name="Foreign", email="customer@example.com"),
            Conversations(id="foreign", organization_id="foreign", customer_id="foreign", status="OPEN"),
            Messages(id="foreign", conversation_id="foreign", sender_type="CUSTOMER", sender_id="foreign", content="Private"),
        ])
        self.db.commit()
        app = FastAPI()
        for module in (users, organizations, customers, conversation, messages):
            app.include_router(module.router)
        register_auth_handlers(app)
        app.dependency_overrides[get_db] = lambda: self.db
        self.actor = SimpleNamespace(id="actor", organization_id="own", role="ADMIN")
        app.dependency_overrides[get_current_user] = lambda: self.actor
        self.client = ASGIClient(app)

    def assert_hidden(self, first, second):
        self.assertEqual(first.status_code, 404)
        self.assertEqual(second.status_code, 404)
        self.assertEqual(first.body, second.body)
        self.assertEqual(json.loads(first.body), {"success": False, "message": "Resource not found", "data": None})

    def test_missing_and_foreign_ids_share_response(self):
        for prefix in ("/users", "/organizations", "/customer", "/conversations", "/messages"):
            with self.subTest(prefix=prefix):
                self.assert_hidden(self.client.get(prefix + "/missing"), self.client.get(prefix + "/foreign"))

    def test_missing_and_foreign_user_email_share_response(self):
        self.assert_hidden(
            self.client.get("/users/by-email?email=missing@example.com"),
            self.client.get("/users/by-email?email=foreign@example.com"),
        )

    def test_collection_filters_do_not_expose_foreign_resources(self):
        for prefix in ("/users/by-organization", "/conversations/by-organization", "/conversations/by-customer", "/messages/by-conversation"):
            with self.subTest(prefix=prefix):
                self.assert_hidden(self.client.get(prefix + "/missing"), self.client.get(prefix + "/foreign"))

    def test_foreign_and_missing_update_targets_share_response(self):
        for prefix, payload in (("/users", {"name": "changed"}), ("/customer", {"name": "changed"}), ("/conversations", {"status": "RESOLVED"})):
            with self.subTest(prefix=prefix):
                self.assert_hidden(self.client.patch(prefix + "/missing", json=payload), self.client.patch(prefix + "/foreign", json=payload))

    def test_missing_and_foreign_org_in_body_share_response(self):
        payload = {"organization_id": "missing", "name": "New", "email": "new@example.com", "password": "long test password", "role": "AGENT"}
        self.assert_hidden(self.client.post("/users", json=payload), self.client.post("/users", json=payload | {"organization_id": "foreign"}))

    def test_locked_authorization_checks_fresh_assignment(self):
        self.actor.role = "AGENT"
        record = SimpleNamespace(organization_id="own", assigned_agent_id="other")
        with patch.object(authorization_service.conversations_repository, "get_conversation_for_update", return_value=record) as locked:
            with self.assertRaises(PermissionDeniedError):
                authorization_service.require_conversation(self.db, self.actor, "conversation", lock=True)
            locked.assert_called_once_with(self.db, "conversation")
        with patch.object(authorization_service.conversations_repository, "get_conversation_for_update", return_value=None):
            with self.assertRaises(ResourceNotFoundError):
                authorization_service.require_conversation(self.db, self.actor, "missing", lock=True)
