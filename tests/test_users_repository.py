import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.generated_models import Base, Conversations, Customers, Organizations
from app.repositories import users_repository


class UsersRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)

        @event.listens_for(self.engine, "connect")
        def configure_sqlite(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("char_length", 1, len)

        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        self.db.add_all([
            Organizations(id="org", name="Organization"),
            Organizations(id="other", name="Other organization"),
        ])
        self.db.commit()

    def create_user(self, **overrides):
        values = dict(
            organization_id="org", name="Agent", email="agent@example.com",
            password_hash="test-hash-original", role="AGENT",
        )
        values.update(overrides)
        return users_repository.create_user(db=self.db, **values)

    def test_create_and_lookup(self):
        user = self.create_user()
        self.assertIsNotNone(user.id)
        self.assertIsNotNone(user.created_at)
        self.assertEqual(user.password_hash, "test-hash-original")
        self.assertEqual(user.role, "AGENT")
        self.db.expire_all()
        self.assertEqual(users_repository.get_user_by_id(self.db, user.id).name, "Agent")
        self.assertEqual(users_repository.get_user_by_email(self.db, user.email).id, user.id)
        self.assertIsNone(users_repository.get_user_by_id(self.db, "missing"))
        self.assertIsNone(users_repository.get_user_by_email(self.db, "missing@example.com"))

    def test_list_and_organization_filter(self):
        self.assertEqual(list(users_repository.get_users(self.db)), [])
        first = self.create_user()
        second = self.create_user(organization_id="other", email="other@example.com")
        self.assertEqual({u.id for u in users_repository.get_users(self.db)}, {first.id, second.id})
        self.assertEqual([u.id for u in users_repository.get_users_by_organization_id(self.db, "org")], [first.id])
        self.assertEqual(list(users_repository.get_users_by_organization_id(self.db, "missing")), [])

    def test_update_preserves_organization_and_optional_password(self):
        user = self.create_user()
        updated = users_repository.update_user(
            self.db, user.id, "Updated", "updated@example.com", "ADMIN"
        )
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.email, "updated@example.com")
        self.assertEqual(updated.role, "ADMIN")
        self.assertEqual(updated.organization_id, "org")
        self.assertEqual(updated.password_hash, "test-hash-original")
        updated = users_repository.update_user(
            self.db, user.id, updated.name, updated.email, updated.role,
            password_hash="test-hash-replacement",
        )
        self.assertEqual(updated.password_hash, "test-hash-replacement")

    def test_update_missing_user(self):
        self.assertIsNone(users_repository.update_user(
            self.db, "missing", "Agent", "agent@example.com", "AGENT"
        ))

    def test_delete_existing_and_missing_user(self):
        user_id = self.create_user().id
        self.assertTrue(users_repository.delete_user(self.db, user_id))
        self.assertIsNone(users_repository.get_user_by_id(self.db, user_id))
        self.assertFalse(users_repository.delete_user(self.db, user_id))

    def test_duplicate_email_rolls_back_create_and_session_remains_usable(self):
        user = self.create_user()
        with self.assertRaises(IntegrityError):
            self.create_user()
        self.assertEqual([u.id for u in users_repository.get_users(self.db)], [user.id])
        self.assertIsNotNone(self.create_user(email="new@example.com").id)

    def test_invalid_organization_rolls_back_create(self):
        with self.assertRaises(IntegrityError):
            self.create_user(organization_id="missing")
        self.assertEqual(list(users_repository.get_users(self.db)), [])

    def test_duplicate_email_rolls_back_entire_update(self):
        first = self.create_user()
        second = self.create_user(email="second@example.com")
        with self.assertRaises(IntegrityError):
            users_repository.update_user(
                self.db, second.id, "Changed", first.email, "ADMIN",
                password_hash="test-hash-changed",
            )
        self.db.refresh(second)
        self.assertEqual(second.email, "second@example.com")
        self.assertEqual(second.name, "Agent")
        self.assertEqual(second.role, "AGENT")
        self.assertEqual(second.password_hash, "test-hash-original")

    def test_assigned_user_cannot_be_deleted_and_conversation_is_preserved(self):
        user = self.create_user()
        self.db.add(Customers(id="customer", organization_id="org", name="Customer", email="customer@example.com"))
        self.db.commit()
        self.db.add(Conversations(
            id="conversation", organization_id="org", customer_id="customer",
            assigned_agent_id=user.id, status="OPEN",
        ))
        self.db.commit()
        with self.assertRaises(IntegrityError):
            users_repository.delete_user(self.db, user.id)
        self.assertIsNotNone(users_repository.get_user_by_id(self.db, user.id))
        self.assertEqual(self.db.get(Conversations, "conversation").assigned_agent_id, user.id)


if __name__ == "__main__":
    unittest.main()
