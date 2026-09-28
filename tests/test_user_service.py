import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import organization_exceptions, user_exceptions
from app.schemas.users import UserCreate, UserResponse, UserUpdate
from app.security.passwords import hash_password
from app.services import user_service


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock(spec=Session)
        self.user = SimpleNamespace(
            id="user", organization_id="org", name="Agent", email="agent@example.com",
            role="AGENT", password_hash="stored-hash", created_at=None,
        )
        for name in ("users_repository", "organization_repository", "hash_password"):
            patcher = patch("app.services.user_service." + name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.repo = self.users_repository
        self.repo.get_user_by_id.return_value = self.user
        self.repo.get_user_by_email.return_value = None
        self.repo.has_assigned_conversations.return_value = False
        self.repo.create_user.return_value = self.user
        self.repo.update_user.return_value = self.user
        self.repo.delete_user.return_value = True
        self.organization_repository.get_organization_by_id.return_value = SimpleNamespace(id="org")
        self.hash_password.return_value = "hashed-password"

    def create(self, **overrides):
        data = dict(organization_id=" org ", name=" Agent ", email=" Agent@Example.com ",
                    password="a long password for testing", role="AGENT")
        data.update(overrides)
        return user_service.create_user(self.db, UserCreate(**data))

    def test_create_accepts_exactly_three_roles_and_normalizes_profile(self):
        for role in ("ADMIN", "SUPERVISOR", "AGENT"):
            with self.subTest(role=role):
                self.assertIs(self.create(role=role), self.user)
                self.repo.create_user.assert_called_with(
                    db=self.db, organization_id="org", name="Agent", email="agent@example.com",
                    password_hash="hashed-password", role=role,
                )
        self.organization_repository.get_organization_by_id.assert_called_with(db=self.db, organization_id="org")

    def test_create_and_update_reject_other_roles_in_service(self):
        for role in ("OWNER", "admin", " AGENT ", "", "OTHER"):
            with self.subTest(role=role):
                with self.assertRaises(user_exceptions.InvalidUserRoleError):
                    self.create(role=role)
                with self.assertRaises(user_exceptions.InvalidUserRoleError):
                    user_service.update_user(self.db, UserUpdate(role=role), "user")
        self.repo.create_user.assert_not_called()
        self.repo.update_user.assert_not_called()
        self.hash_password.assert_not_called()

    def test_invalid_fields_block_create_and_update(self):
        cases = (
            ("name", " ", user_exceptions.InvalidUserNameError),
            ("name", "x" * 51, user_exceptions.InvalidUserNameError),
            ("email", "not-an-email", user_exceptions.InvalidUserEmailError),
            ("email", "x" * 64 + "@" + "y" * 40 + ".com", user_exceptions.InvalidUserEmailError),
            ("password", "short", user_exceptions.InvalidUserPasswordError),
            ("password", " " * 20, user_exceptions.InvalidUserPasswordError),
            ("password", "x" * 129, user_exceptions.InvalidUserPasswordError),
        )
        for field, value, error in cases:
            with self.subTest(field=field, length=len(value)):
                with self.assertRaises(error):
                    self.create(**{field: value})
                with self.assertRaises(error):
                    user_service.update_user(self.db, UserUpdate(**{field: value}), "user")
        self.repo.create_user.assert_not_called()
        self.repo.update_user.assert_not_called()

    def test_organization_required_and_must_exist_for_create_and_list(self):
        with self.assertRaises(organization_exceptions.OrganizationIDRequired):
            self.create(organization_id=" ")
        with self.assertRaises(organization_exceptions.OrganizationIDRequired):
            user_service.get_users_by_organization_id(self.db, " ")
        self.organization_repository.get_organization_by_id.return_value = None
        with self.assertRaises(organization_exceptions.OrganizationNotFoundError):
            self.create()
        with self.assertRaises(organization_exceptions.OrganizationNotFoundError):
            user_service.get_users_by_organization_id(self.db, "missing")
        self.repo.create_user.assert_not_called()
        self.repo.get_users_by_organization_id.assert_not_called()

    def test_duplicate_email_prevents_writes(self):
        self.repo.get_user_by_email.return_value = SimpleNamespace(id="other")
        with self.assertRaises(user_exceptions.ExistingEmailError):
            self.create()
        with self.assertRaises(user_exceptions.ExistingEmailError):
            user_service.update_user(self.db, UserUpdate(email="taken@example.com"), "user")
        self.repo.create_user.assert_not_called()
        self.repo.update_user.assert_not_called()
        self.hash_password.assert_not_called()

    def test_update_preserves_omitted_fields_and_accepts_own_email(self):
        self.repo.get_user_by_email.return_value = self.user
        user_service.update_user(self.db, UserUpdate(email=" Agent@Example.com "), " user ")
        self.repo.update_user.assert_called_once_with(
            db=self.db, user_id="user", name="Agent", email="agent@example.com",
            role="AGENT", password_hash=None,
        )
        self.hash_password.assert_not_called()

    def test_update_changes_password_without_trimming_and_role(self):
        password = "  long password with spaces  "
        user_service.update_user(self.db, UserUpdate(password=password, role="SUPERVISOR"), "user")
        self.hash_password.assert_called_once_with(password)
        self.assertEqual(self.repo.update_user.call_args.kwargs["role"], "SUPERVISOR")
        self.assertEqual(self.repo.update_user.call_args.kwargs["password_hash"], "hashed-password")

    def test_empty_update_preserves_all_fields(self):
        user_service.update_user(self.db, UserUpdate(), "user")
        self.repo.update_user.assert_called_once_with(
            db=self.db, user_id="user", name="Agent", email="agent@example.com",
            role="AGENT", password_hash=None,
        )

    def test_lookup_and_lists(self):
        self.assertIs(user_service.get_user_by_id(self.db, " user "), self.user)
        self.repo.get_user_by_id.assert_called_with(db=self.db, user_id="user")
        self.repo.get_user_by_email.return_value = self.user
        self.assertIs(user_service.get_user_by_email(self.db, " Agent@Example.com "), self.user)
        self.repo.get_user_by_email.assert_called_with(db=self.db, user_email="agent@example.com")
        self.repo.get_users.return_value = []
        self.assertEqual(user_service.get_users(self.db), [])
        self.repo.get_users_by_organization_id.return_value = [self.user]
        self.assertEqual(user_service.get_users_by_organization_id(self.db, " org "), [self.user])
        self.repo.get_users_by_organization_id.assert_called_with(db=self.db, organization_id="org")

    def test_missing_and_blank_users(self):
        for user_id in (None, "", " "):
            with self.assertRaises(user_exceptions.UserIDRequiredError):
                user_service.get_user_by_id(self.db, user_id)
        self.repo.get_user_by_id.return_value = None
        for operation in (
            lambda: user_service.get_user_by_id(self.db, "missing"),
            lambda: user_service.get_user_by_email(self.db, "missing@example.com"),
            lambda: user_service.update_user(self.db, UserUpdate(name="Changed"), "missing"),
            lambda: user_service.delete_user(self.db, "missing"),
        ):
            with self.assertRaises(user_exceptions.UserNotFoundError):
                operation()
        self.repo.update_user.assert_not_called()
        self.repo.delete_user.assert_not_called()

    def test_delete_blocks_assigned_users(self):
        self.repo.has_assigned_conversations.return_value = True
        with self.assertRaises(user_exceptions.UserInUseError):
            user_service.delete_user(self.db, "user")
        self.repo.delete_user.assert_not_called()
        self.repo.has_assigned_conversations.return_value = False
        self.assertTrue(user_service.delete_user(self.db, "user"))

    def test_known_mysql_conflicts_are_translated_and_other_errors_propagate(self):
        for method, operation, code, error in (
            ("create_user", self.create, 1062, user_exceptions.ExistingEmailError),
            ("update_user", lambda: user_service.update_user(self.db, UserUpdate(), "user"), 1062, user_exceptions.ExistingEmailError),
            ("delete_user", lambda: user_service.delete_user(self.db, "user"), 1451, user_exceptions.UserInUseError),
        ):
            with self.subTest(method=method):
                repo_method = getattr(self.repo, method)
                repo_method.side_effect = IntegrityError("statement", {}, Exception(code, "DB details"))
                with self.assertRaises(error):
                    operation()
                unknown = IntegrityError("statement", {}, Exception(9999, "other error"))
                repo_method.side_effect = unknown
                with self.assertRaises(IntegrityError) as caught:
                    operation()
                self.assertIs(caught.exception, unknown)
                repo_method.side_effect = None

    def test_user_disappearing_during_write_returns_not_found(self):
        self.repo.update_user.return_value = None
        with self.assertRaises(user_exceptions.UserNotFoundError):
            user_service.update_user(self.db, UserUpdate(), "user")
        self.repo.delete_user.return_value = False
        with self.assertRaises(user_exceptions.UserNotFoundError):
            user_service.delete_user(self.db, "user")

    def test_response_excludes_credentials_and_update_cannot_change_organization(self):
        output = UserResponse.model_validate(self.user).model_dump()
        self.assertNotIn("password", output)
        self.assertNotIn("password_hash", output)
        with self.assertRaises(ValidationError):
            UserUpdate(organization_id="other")
        with self.assertRaises(ValidationError):
            UserUpdate(password_hash="caller-controlled-hash")


class PasswordHashTests(unittest.TestCase):
    def test_real_hash_uses_unique_salt_and_preserves_password(self):
        password = "  a long password for testing  "
        first = hash_password(password)
        second = hash_password(password)
        self.assertNotEqual(first, second)
        self.assertNotIn(password, first)
        self.assertLessEqual(len(first), 255)
        algorithm, n, r, p, salt, digest = first.split("$")
        self.assertEqual((algorithm, int(n), int(r), int(p)), ("scrypt", 131072, 8, 1))
        self.assertEqual(len(bytes.fromhex(salt)), 16)
        expected = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
            maxmem=256 * 1024 * 1024, dklen=64,
        )
        self.assertEqual(expected.hex(), digest)


if __name__ == "__main__":
    unittest.main()
