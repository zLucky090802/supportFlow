import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import (
    conversation_exceptions,
    customer_exceptions,
    message_exceptions,
)
from app.models.generated_models import MessagesSenderType
from app.schemas.messages import MessageCreate
from app.services import message_service


class MessageServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock(spec=Session)
        self.conversation = SimpleNamespace(
            id="conversation", customer_id="customer", organization_id="org"
        )
        self.repositories = {}
        for name in (
            "conversations_repository", "customers_repository",
            "messages_repository", "users_repository",
        ):
            target = (
                "app.services.conversations." if name == "conversations_repository"
                else "app.services.message_service."
            )
            patcher = patch(target + name)
            self.repositories[name] = patcher.start()
            self.addCleanup(patcher.stop)
        self.conversations = self.repositories["conversations_repository"]
        self.messages = self.repositories["messages_repository"]
        self.customers = self.repositories["customers_repository"]
        self.users = self.repositories["users_repository"]
        self.conversations.get_conversation_by_id.return_value = self.conversation
        self.customers.get_customer_by_id.return_value = SimpleNamespace(organization_id="org")
        self.users.get_user_by_id.return_value = SimpleNamespace(organization_id="org")

    def create(self, **overrides):
        data = dict(conversation_id=" conversation ", sender_type="AI", content=" hello ")
        data.update(overrides)
        return message_service.create_message(self.db, MessageCreate(**data))

    def test_valid_senders_and_normalization(self):
        for sender_type, sender_id in (("AI", None), ("CUSTOMER", " customer "), ("AGENT", " agent ")):
            with self.subTest(sender_type=sender_type):
                result = self.create(sender_type=sender_type, sender_id=sender_id)
                self.assertIs(result, self.messages.create_message.return_value)
                self.messages.create_message.assert_called_with(
                    db=self.db, conversation_id="conversation",
                    sender_type=MessagesSenderType(sender_type),
                    sender_id=sender_id.strip() if sender_id else None, content="hello",
                )
        self.conversations.get_conversation_by_id.assert_called_with(
            db=self.db, conversation_id="conversation"
        )

    def test_invalid_sender_combinations_do_not_write(self):
        cases = (("AI", "agent"), ("AI", " "), ("CUSTOMER", None),
                 ("CUSTOMER", " "), ("CUSTOMER", "other"), ("AGENT", None), ("AGENT", " "))
        for sender_type, sender_id in cases:
            with self.subTest(sender_type=sender_type, sender_id=sender_id):
                with self.assertRaises(message_exceptions.InvalidMessageSenderError):
                    self.create(sender_type=sender_type, sender_id=sender_id)
        self.messages.create_message.assert_not_called()

    def test_missing_or_foreign_agent_does_not_write(self):
        for agent in (None, SimpleNamespace(organization_id="other")):
            with self.subTest(agent=agent):
                self.users.get_user_by_id.return_value = agent
                with self.assertRaises(message_exceptions.InvalidMessageSenderError):
                    self.create(sender_type="AGENT", sender_id="agent")
        self.messages.create_message.assert_not_called()

    def test_missing_or_foreign_customer_does_not_write(self):
        for customer, error in (
            (None, customer_exceptions.CustomerNotFoundError),
            (SimpleNamespace(organization_id="other"), customer_exceptions.CustomerOrganizationMismatchError),
        ):
            with self.subTest(customer=customer):
                self.customers.get_customer_by_id.return_value = customer
                with self.assertRaises(error):
                    self.create(sender_type="CUSTOMER", sender_id="customer")
        self.messages.create_message.assert_not_called()

    def test_missing_conversation_blocks_create_and_list(self):
        self.conversations.get_conversation_by_id.return_value = None
        with self.assertRaises(conversation_exceptions.ConversationNotFound):
            self.create()
        with self.assertRaises(conversation_exceptions.ConversationNotFound):
            message_service.get_messages_by_conversation_id(self.db, "missing")
        self.messages.create_message.assert_not_called()
        self.messages.get_messages_by_conversation_id.assert_not_called()

    def test_blank_conversation_id_blocks_create_and_list(self):
        with self.assertRaises(conversation_exceptions.ConversationIdRequiered):
            self.create(conversation_id=" ")
        with self.assertRaises(conversation_exceptions.ConversationIdRequiered):
            message_service.get_messages_by_conversation_id(self.db, " ")
        self.conversations.get_conversation_by_id.assert_not_called()
        self.messages.create_message.assert_not_called()
        self.messages.get_messages_by_conversation_id.assert_not_called()

    def test_service_revalidates_mutated_content_and_sender_type(self):
        for field, value, error in (
            ("content", " \n ", message_exceptions.InvalidMessageContentError),
            ("sender_type", "UNKNOWN", message_exceptions.InvalidMessageSenderError),
        ):
            with self.subTest(field=field):
                data = MessageCreate(conversation_id="conversation", sender_type="AI", content="hello")
                setattr(data, field, value)
                with self.assertRaises(error):
                    message_service.create_message(self.db, data)
        self.messages.create_message.assert_not_called()

    def test_get_message_requires_id_and_existing_message(self):
        for value in (None, "", " "):
            with self.assertRaises(message_exceptions.MessageIDRequiredError):
                message_service.get_message_by_id(self.db, value)
        self.messages.get_message_by_id.assert_not_called()
        self.messages.get_message_by_id.return_value = None
        with self.assertRaises(message_exceptions.MessageNotFoundError):
            message_service.get_message_by_id(self.db, "missing")
        existing = object()
        self.messages.get_message_by_id.return_value = existing
        self.assertIs(message_service.get_message_by_id(self.db, " message "), existing)
        self.messages.get_message_by_id.assert_called_with(db=self.db, message_id="message")

    def test_list_preserves_repository_order_and_empty_history(self):
        for history in ([], [object(), object()]):
            self.messages.get_messages_by_conversation_id.return_value = history
            self.assertIs(
                message_service.get_messages_by_conversation_id(self.db, " conversation "), history
            )
        self.messages.get_messages_by_conversation_id.assert_called_with(
            db=self.db, conversation_id="conversation"
        )

    def test_database_failure_propagates_without_service_commit(self):
        self.messages.create_message.side_effect = SQLAlchemyError("write failed")
        with self.assertRaises(SQLAlchemyError):
            self.create()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
