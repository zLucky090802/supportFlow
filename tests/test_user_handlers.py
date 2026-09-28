import json
import unittest

from fastapi import FastAPI

from app.exceptions import user_exceptions
from app.handlers.user_handlers import register_user_handlers


ERROR_CASES = (
    (user_exceptions.UserIDRequiredError, 400),
    (user_exceptions.UserNotFoundError, 404),
    (user_exceptions.InvalidUserNameError, 400),
    (user_exceptions.InvalidUserEmailError, 400),
    (user_exceptions.InvalidUserPasswordError, 400),
    (user_exceptions.InvalidUserRoleError, 400),
    (user_exceptions.ExistingEmailError, 409),
    (user_exceptions.UserOrganizationMismatchError, 400),
    (user_exceptions.UserInUseError, 409),
)


class UserHandlersTests(unittest.IsolatedAsyncioTestCase):
    async def request_with_error(self, exception):
        # A separate application verifies registration without changing main.py.
        app = FastAPI()
        register_user_handlers(app)

        @app.get("/test-user-error")
        def failing_route():
            raise exception

        events = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(event):
            events.append(event)

        await app(
            {
                "type": "http", "asgi": {"version": "3.0"},
                "http_version": "1.1", "method": "GET", "scheme": "http",
                "path": "/test-user-error", "raw_path": b"/test-user-error",
                "query_string": b"", "root_path": "", "headers": [],
                "client": ("127.0.0.1", 1234), "server": ("test", 80),
            },
            receive,
            send,
        )
        response = next(event for event in events if event["type"] == "http.response.start")
        body = b"".join(event.get("body", b"") for event in events if event["type"] == "http.response.body")
        self.assertIn((b"content-type", b"application/json"), response["headers"])
        return response["status"], json.loads(body)

    async def test_each_exception_returns_its_status_and_error_envelope(self):
        for exception_type, expected_status in ERROR_CASES:
            with self.subTest(exception=exception_type.__name__):
                exception = exception_type()
                self.assertTrue(str(exception))
                status, body = await self.request_with_error(exception)
                self.assertEqual(status, expected_status)
                self.assertEqual(body, {
                    "success": False, "message": str(exception), "data": None,
                })

    async def test_each_handler_preserves_custom_business_message(self):
        for exception_type, expected_status in ERROR_CASES:
            with self.subTest(exception=exception_type.__name__):
                exception = exception_type("Custom validation message")
                status, body = await self.request_with_error(exception)
                self.assertEqual(status, expected_status)
                self.assertEqual(body, {
                    "success": False, "message": "Custom validation message", "data": None,
                })

    def test_all_user_exceptions_have_handlers(self):
        app = FastAPI()
        original_handlers = dict(app.exception_handlers)
        register_user_handlers(app)
        exception_types = {
            value for value in vars(user_exceptions).values()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        self.assertEqual(exception_types, {case[0] for case in ERROR_CASES})
        self.assertTrue(exception_types <= app.exception_handlers.keys())
        for exception_type, handler in original_handlers.items():
            self.assertIs(app.exception_handlers[exception_type], handler)


if __name__ == "__main__":
    unittest.main()
