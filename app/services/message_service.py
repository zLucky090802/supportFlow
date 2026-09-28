from sqlalchemy.orm import Session

from app.exceptions import customer_exceptions, message_exceptions
from app.models.generated_models import Messages, MessagesSenderType
from app.repositories import (
    customers_repository,
    messages_repository,
    users_repository,
)
from app.schemas.messages import MessageCreate
from app.services import conversations as conversation_service


def get_message_by_id(db: Session, message_id: str) -> Messages:
    if not message_id or not message_id.strip():
        raise message_exceptions.MessageIDRequiredError()

    message = messages_repository.get_message_by_id(
        db=db,
        message_id=message_id.strip(),
    )
    if message is None:
        raise message_exceptions.MessageNotFoundError()

    return message


def get_messages_by_conversation_id(
    db: Session,
    conversation_id: str,
) -> list[Messages]:
    conversation = conversation_service.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
    )
    return messages_repository.get_messages_by_conversation_id(
        db=db,
        conversation_id=conversation.id,
    )


def create_message(db: Session, message: MessageCreate) -> Messages:
    conversation = conversation_service.get_conversation_by_id(
        db=db,
        conversation_id=message.conversation_id,
    )

    content = message.content.strip()
    if not content:
        raise message_exceptions.InvalidMessageContentError()

    try:
        sender_type = MessagesSenderType(message.sender_type)
    except (ValueError, TypeError):
        raise message_exceptions.InvalidMessageSenderError(
            "Sender type must be CUSTOMER, AI or AGENT"
        ) from None

    sender_id = message.sender_id.strip() if message.sender_id is not None else None

    if sender_type == MessagesSenderType.AI:
        if sender_id is not None:
            raise message_exceptions.InvalidMessageSenderError(
                "AI messages must not have a sender ID"
            )
    else:
        if not sender_id:
            raise message_exceptions.InvalidMessageSenderError(
                "Customer and agent messages require a sender ID"
            )

        if sender_type == MessagesSenderType.CUSTOMER:
            if sender_id != conversation.customer_id:
                raise message_exceptions.InvalidMessageSenderError(
                    "Sender must be the customer of the conversation"
                )
            customer = customers_repository.get_customer_by_id(
                db=db,
                customer_id=sender_id,
            )
            if customer is None:
                raise customer_exceptions.CustomerNotFoundError()
            if customer.organization_id != conversation.organization_id:
                raise customer_exceptions.CustomerOrganizationMismatchError()
        else:
            agent = users_repository.get_user_by_id(db=db, user_id=sender_id)
            if agent is None:
                raise message_exceptions.InvalidMessageSenderError(
                    "Agent not found"
                )
            if agent.organization_id != conversation.organization_id:
                raise message_exceptions.InvalidMessageSenderError(
                    "Agent must belong to the conversation organization"
                )

    return messages_repository.create_message(
        db=db,
        conversation_id=conversation.id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
    )
