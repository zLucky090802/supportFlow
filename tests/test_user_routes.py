import json
import os
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import organization_exceptions, user_exceptions
from app.handlers.organization_handlers import register_exception_handlers
from app.handlers.user_handlers import register_user_handlers
from app.models.generated_models import Users

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
    from app.db.database import get_db
    from app.routes.users import router


class UserRoutesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Exercise the router independently; application registration is a later task.
        self.app = FastAPI()
        self.app.include_router(router)
        register_user_handlers(self.app)
        register_exception_handlers(self.app)
        self.db = Mock(spec=Session)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.user = Users(
            id="user", organization_id="org", name="Agent", email="agent@example.com",
            role="AGENT", password_hash="private-stored-hash",
        )
        self.payload = {
            "organization_id": "org", "name": "Agent", "email": "agent@example.com",
            "password": "long password for testing", "role": "AGENT",
        }

    async def request(self, method, url, body=None):
        events = []
        parts = urlsplit(url)
        payload = json.dumps(body).encode() if body is not None else b""

        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(event):
            events.append(event)

        await self.app(
            {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": parts.path,
                "raw_path": parts.path.encode(), "query_string": parts.query.encode(),
                "root_path": "", "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 1234), "server": ("test", 80),
            }, receive, send,
        )
        status = next(e["status"] for e in events if e["type"] == "http.response.start")
        content = b"".join(e.get("body", b"") for e in events if e["type"] == "http.response.body")
        return status, json.loads(content) if content else None

    def assert_safe_user(self, body):
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["id"], "user")
        self.assertNotIn("password", body["data"])
        self.assertNotIn("password_hash", body["data"])
        self.assertNotIn("private-stored-hash", json.dumps(body))

    async def test_detail_and_email_queries_use_correct_service_and_hide_credentials(self):
        cases = (
            ("/users/user", "get_user_by_id", {"user_id": "user"}),
            ("/users/by-email?" + urlencode({"email": "agent+team@example.com"}),
             "get_user_by_email", {"user_email": "agent+team@example.com"}),
        )
        for path, method, kwargs in cases:
            with self.subTest(method=method):
                with patch("app.routes.users.user_service." + method, return_value=self.user) as service:
                    status, body = await self.request("GET", path)
                self.assertEqual(status, 200)
                self.assert_safe_user(body)
                service.assert_called_once_with(db=self.db, **kwargs)

    async def test_lists_support_empty_results_and_hide_credentials(self):
        for path, method, kwargs in (
            ("/users", "get_users", {}),
            ("/users/by-organization/org", "get_users_by_organization_id", {"organization_id": "org"}),
        ):
            for users in ([], [self.user]):
                with self.subTest(path=path, count=len(users)):
                    with patch("app.routes.users.user_service." + method, return_value=users) as service:
                        status, body = await self.request("GET", path)
                    self.assertEqual(status, 200)
                    self.assertTrue(body["success"])
                    self.assertEqual(len(body["data"]), len(users))
                    for item in body["data"]:
                        self.assert_safe_user({"success": True, "data": item})
                    service.assert_called_once_with(db=self.db, **kwargs)

    async def test_create_passes_schema_and_returns_201(self):
        with patch("app.routes.users.user_service.create_user", return_value=self.user) as service:
            status, body = await self.request("POST", "/users", self.payload)
        self.assertEqual(status, 201)
        self.assert_safe_user(body)
        self.assertIs(service.call_args.kwargs["db"], self.db)
        self.assertEqual(service.call_args.kwargs["user"].password.get_secret_value(), self.payload["password"])

    async def test_patch_passes_only_supplied_fields(self):
        with patch("app.routes.users.user_service.update_user", return_value=self.user) as service:
            status, body = await self.request("PATCH", "/users/user", {"role": "SUPERVISOR"})
        self.assertEqual(status, 200)
        self.assert_safe_user(body)
        self.assertEqual(service.call_args.kwargs["user_id"], "user")
        self.assertEqual(service.call_args.kwargs["user"].model_dump(exclude_unset=True), {"role": "SUPERVISOR"})

    async def test_delete_returns_204_without_body(self):
        with patch("app.routes.users.user_service.delete_user", return_value=True) as service:
            status, body = await self.request("DELETE", "/users/user")
        self.assertEqual((status, body), (204, None))
        service.assert_called_once_with(db=self.db, user_id="user")

    async def test_business_errors_propagate_to_handlers(self):
        cases = (
            ("GET", "/users/missing", "get_user_by_id", user_exceptions.UserNotFoundError(), 404),
            ("POST", "/users", "create_user", user_exceptions.ExistingEmailError(), 409),
            ("PATCH", "/users/user", "update_user", user_exceptions.InvalidUserRoleError(), 400),
            ("DELETE", "/users/user", "delete_user", user_exceptions.UserInUseError(), 409),
            ("GET", "/users/by-organization/missing", "get_users_by_organization_id",
             organization_exceptions.OrganizationNotFoundError(), 404),
        )
        for method, path, service_name, error, expected_status in cases:
            with self.subTest(service=service_name):
                payload = self.payload if method == "POST" else {"role": "OWNER"} if method == "PATCH" else None
                with patch("app.routes.users.user_service." + service_name, side_effect=error):
                    status, body = await self.request(method, path, payload)
                self.assertEqual(status, expected_status)
                self.assertEqual(body, {"success": False, "message": str(error), "data": None})

    async def test_real_service_rejects_invalid_role_before_persistence(self):
        with patch("app.services.user_service.organization_repository.get_organization_by_id", return_value=Mock(id="org")), \
             patch("app.services.user_service.users_repository") as repo:
            for role in ("OWNER", "admin", "", "OTHER"):
                with self.subTest(role=role):
                    status, body = await self.request("POST", "/users", self.payload | {"role": role})
                    self.assertEqual(status, 400)
                    self.assertFalse(body["success"])
            repo.create_user.assert_not_called()

    async def test_schema_errors_block_service_calls(self):
        with patch("app.routes.users.user_service") as service:
            for method, path, payload in (
                ("POST", "/users", {}),
                ("POST", "/users", self.payload | {"password_hash": "injected"}),
                ("PATCH", "/users/user", {"organization_id": "other"}),
                ("GET", "/users/by-email", None),
            ):
                with self.subTest(method=method, path=path):
                    status, _ = await self.request(method, path, payload)
                    self.assertEqual(status, 422)
            self.assertEqual(service.mock_calls, [])

    async def test_database_failure_hides_sql_details(self):
        with patch("app.routes.users.user_service.create_user", side_effect=SQLAlchemyError("private SQL")):
            status, body = await self.request("POST", "/users", self.payload)
        self.assertEqual(status, 500)
        self.assertEqual(body, {
            "success": False, "message": "An unexpected database error occurred", "data": None,
        })


if __name__ == "__main__":
    unittest.main()
