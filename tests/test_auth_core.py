import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt

from app.exceptions.auth_exceptions import AuthenticationError, AuthConfigurationError
from app.security.passwords import hash_password, verify_password
from app.security import tokens
from app.services import auth_service


class PasswordTests(unittest.TestCase):
    def test_password_roundtrip_preserves_spaces_and_unicode(self):
        password = "  long contraseña for testing  "
        stored = hash_password(password)
        self.assertTrue(verify_password(password, stored))
        self.assertFalse(verify_password(password.strip(), stored))
        self.assertFalse(verify_password("incorrect", stored))

    def test_malformed_hashes_and_costs_do_not_run_scrypt(self):
        with patch("app.security.passwords.hashlib.scrypt") as scrypt:
            for stored in ("plain text", "scrypt$999999$8$1$" + "00" * 16 + "$" + "00" * 64,
                           "scrypt$131072$8$1$" + "zz" * 16 + "$" + "00" * 64):
                self.assertFalse(verify_password("password", stored))
            self.assertFalse(verify_password("a" * 129, auth_service._DUMMY_HASH))
            scrypt.assert_not_called()


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-for-authentication-tests-only-with-48-bytes"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_roundtrip_and_claims(self):
        token = tokens.create_access_token("user-id")
        self.assertEqual(tokens.decode_access_token(token), "user-id")
        claims = jwt.decode(token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"],
                            audience=tokens.JWT_AUDIENCE, issuer=tokens.JWT_ISSUER)
        self.assertEqual(claims["exp"] - claims["iat"], 1800)
        self.assertNotIn("password", claims)
        self.assertNotIn("role", claims)

    def test_invalid_claims_and_signature_are_rejected(self):
        now = int(datetime.now(timezone.utc).timestamp())
        base = {"sub": "user", "iat": now, "exp": now + 1800, "type": "access",
                "iss": tokens.JWT_ISSUER, "aud": tokens.JWT_AUDIENCE}
        cases = [{**base, "exp": now - 1}, {**base, "iat": now + 100},
                 {**base, "type": "refresh"}, {**base, "sub": ""},
                 {**base, "aud": "other"}, {**base, "iss": "other"},
                 {**base, "exp": now + 3600}, {**base, "iat": str(now)},
                 {**base, "exp": []}, {**base, "iat": {}}]
        for missing in base:
            cases.append({k: v for k, v in base.items() if k != missing})
        for claims in cases:
            with self.subTest(claims=claims):
                token = jwt.encode(claims, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
                with self.assertRaises(AuthenticationError):
                    tokens.decode_access_token(token)
        for key, algorithm in (("different-key-that-is-long-enough", "HS256"),
                               (os.environ["JWT_SECRET_KEY"], "HS384")):
            token = jwt.encode(base, key, algorithm=algorithm)
            with self.assertRaises(AuthenticationError):
                tokens.decode_access_token(token)

    def test_configuration_fails_closed(self):
        for key in ("", "too-short", " " * 40):
            with patch.dict(os.environ, {"JWT_SECRET_KEY": key}):
                with self.assertRaises(AuthConfigurationError):
                    tokens.create_access_token("user")
                with self.assertRaises(AuthConfigurationError):
                    tokens.decode_access_token("token")


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.user = SimpleNamespace(id="user", role="ADMIN", password_hash="stored")

    def test_login_normalizes_email_and_has_uniform_failure(self):
        with patch.object(auth_service, "users_repository") as repo, \
             patch.object(auth_service, "verify_password", return_value=False) as verify:
            for user in (self.user, None):
                repo.get_user_by_email.return_value = user
                with self.assertRaisesRegex(AuthenticationError, "Invalid authentication credentials"):
                    auth_service.login(self.db, " ADMIN@example.com ", "password")
                repo.get_user_by_email.assert_called_with(db=self.db, user_email="admin@example.com")
            verify.assert_called_with("password", auth_service._DUMMY_HASH)

    def test_current_user_is_reloaded_and_unsupported_roles_rejected(self):
        with patch.object(auth_service, "decode_access_token", return_value="user"), \
             patch.object(auth_service, "users_repository") as repo:
            repo.get_user_by_id.return_value = self.user
            self.assertIs(auth_service.get_authenticated_user(self.db, "token"), self.user)
            self.user.role = "OWNER"
            with self.assertRaises(AuthenticationError):
                auth_service.get_authenticated_user(self.db, "token")
            repo.get_user_by_id.return_value = None
            with self.assertRaises(AuthenticationError):
                auth_service.get_authenticated_user(self.db, "token")


if __name__ == "__main__":
    unittest.main()
