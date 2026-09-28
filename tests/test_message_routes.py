import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import (
    conversation_exceptions,
    customer_exceptions,
    message_exceptions,
)
from app.models.generated_models import Messages, MessagesSenderType

# Import the real application without requiring a configured MySQL server.
with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
    from app.db.database import get_db
    from app.main import app


class MessageRoutesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = Mock(spec=Session)
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        self.payload = {
            "conversation_id": "conversation",
            "sender_type": "AI",
            "content": "hello",
        }
        self.message = Messages(
            id="message", conversation_id="conversation",
            sender_type=MessagesSenderType.AI, sender_id=None,
            content="hello", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def tearDown(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    async def request(self, method, path, body=None):
        """Exercise the HTTP ASGI stack using only the standard library."""
        events = []
        payload = json.dumps(body).encode() if body is not None else b""

        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(event):
            events.append(event)

        await app(
            {
                "type": "http", "asgi": {"version": "3.0"},
                "http_version": "1.1", "method": method, "scheme": "http",
                "path": path, "raw_path": path.encode(), "query_string": b"",
                "root_path": "", "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 1234), "server": ("test", 80),
            },
            receive,
            send,
        )
        status = next(e["status"] for e in events if e["type"] == "http.response.start")
        content = b"".join(e.get("body", b"") for e in events if e["type"] == "http.response.body")
        return status, json.loads(content)

    async def test_create_serializes_orm_message_and_passes_validated_schema(self):
        with patch("app.routes.messages.message_service.create_message", return_value=self.message) as create:
            status, body = await self.request("POST", "/messages", self.payload)
        self.assertEqual(status, 201)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["id"], "message")
        self.assertEqual(body["data"]["sender_type"], "AI")
        self.assertIsNone(body["data"]["sender_id"])
        self.assertTrue(body["data"]["created_at"].startswith("2026-01-01T00:00:00"))
        self.assertIs(create.call_args.kwargs["db"], self.db)
        self.assertEqual(create.call_args.kwargs["message"].content, "hello")

    async def test_get_message(self):
        with patch("app.routes.messages.message_service.get_message_by_id", return_value=self.message) as get:
            status, body = await self.request("GET", "/messages/message")
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["id"], "message")
        get.assert_called_once_with(db=self.db, message_id="message")

    async def test_history_preserves_order_and_accepts_empty_list(self):
        second = Messages(id="second", conversation_id="conversation", sender_type="AI", content="reply")
        for history in ([], [self.message, second]):
            with self.subTest(history=len(history)):
                with patch("app.routes.messages.message_service.get_messages_by_conversation_id", return_value=history) as get:
                    status, body = await self.request("GET", "/messages/by-conversation/conversation")
                self.assertEqual(status, 200)
                self.assertTrue(body["success"])
                self.assertEqual([m["id"] for m in body["data"]], [m.id for m in history])
                get.assert_called_once_with(db=self.db, conversation_id="conversation")

    async def test_all_message_exceptions_are_registered(self):
        for exception, expected_status in (
            (message_exceptions.MessageIDRequiredError(), 400),
            (message_exceptions.MessageNotFoundError(), 404),
            (message_exceptions.InvalidMessageContentError(), 400),
            (message_exceptions.InvalidMessageSenderError(), 400),
        ):
            with self.subTest(exception=type(exception).__name__):
                with patch("app.routes.messages.message_service.create_message", side_effect=exception):
                    status, body = await self.request("POST", "/messages", self.payload)
                self.assertEqual(status, expected_status)
                self.assertEqual(body, {"success": False, "message": str(exception), "data": None})

    async def test_related_service_exceptions_are_registered(self):
        for exception, expected_status in (
            (conversation_exceptions.ConversationIdRequiered(), 400),
            (conversation_exceptions.ConversationNotFound(), 404),
            (customer_exceptions.CustomerNotFoundError(), 404),
            (customer_exceptions.CustomerOrganizationMismatchError(), 400),
        ):
            with self.subTest(exception=type(exception).__name__):
                with patch("app.routes.messages.message_service.create_message", side_effect=exception):
                    status, body = await self.request("POST", "/messages", self.payload)
                self.assertEqual(status, expected_status)
                self.assertEqual(body, {"success": False, "message": str(exception), "data": None})

    async def test_schema_rejects_invalid_requests_before_service(self):
        for overrides in ({"content": " "}, {"sender_type": "UNKNOWN"}, {"conversation_id": None}):
            with self.subTest(overrides=overrides):
                with patch("app.routes.messages.message_service.create_message") as create:
                    status, _ = await self.request("POST", "/messages", self.payload | overrides)
                self.assertEqual(status, 422)
                create.assert_not_called()

    async def test_database_errors_do_not_leak_details(self):
        with patch("app.routes.messages.message_service.create_message", side_effect=SQLAlchemyError("secret SQL details")):
            status, body = await self.request("POST", "/messages", self.payload)
        self.assertEqual(status, 500)
        self.assertEqual(body, {
            "success": False, "message": "An unexpected database error occurred", "data": None,
        })

    async def test_no_message_edit_or_delete_endpoints(self):
        for method in ("PUT", "PATCH", "DELETE"):
            status, _ = await self.request(method, "/messages/message")
            self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
