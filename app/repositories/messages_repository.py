
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.generated_models import (
    Messages,
    MessagesSenderType,
)


def get_message_by_id(
    db: Session,
    message_id: str
):
    return db.get(Messages, message_id)


def get_messages_by_conversation_id(
    db: Session,
    conversation_id: str
):
    stmt = (
        select(Messages)
        .where(Messages.conversation_id == conversation_id)
        .order_by(
            Messages.created_at.asc(),
            Messages.id.asc()
        )
    )

    return db.scalars(stmt).all()


def create_message(
    db: Session,
    conversation_id: str,
    sender_type: MessagesSenderType,
    content: str,
    sender_id: str | None = None
):
    try:
        new_message = Messages(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content
        )

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        return new_message

    except SQLAlchemyError:
        db.rollback()
        raise
