
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories import (
    conversations_repository,
    organization_repository,
    customers_repository,
)

from app.schemas.conversations import (
    ConversationCreate,
    ConversationUpdate,
)

from app.exceptions import (
    conversation_exceptions,
    organization_exceptions,
    customer_exceptions,
)


def get_conversations(db: Session):
    return conversations_repository.get_conversations(db=db)


def get_conversation_by_id(db: Session, conversation_id: str):

    if not conversation_id or not conversation_id.strip():
        raise conversation_exceptions.ConversationIdRequiered()

    conversation = conversations_repository.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id.strip(),
    )

    if conversation is None:
        raise conversation_exceptions.ConversationNotFound()

    return conversation


def get_conversation_by_organization_id(
    db: Session,
    organization_id: str,
):

    if not organization_id or not organization_id.strip():
        raise organization_exceptions.OrganizationIDRequired()

    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=organization_id.strip(),
    )

    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()

    return conversations_repository.get_conversations_by_organization_id(
        db=db,
        organization_id=organization.id,
    )


def get_conversation_by_customer_id(
    db: Session,
    customer_id: str,
):

    if not customer_id or not customer_id.strip():
        raise customer_exceptions.CustomerIDRequiredError()

    customer = customers_repository.get_customer_by_id(
        db=db,
        customer_id=customer_id.strip(),
    )

    if customer is None:
        raise customer_exceptions.CustomerNotFoundError()

    return conversations_repository.get_conversations_by_customer_id(
        db=db,
        customer_id=customer.id,
    )


def create_conversation(
    db: Session,
    conversation: ConversationCreate,
):

    if not conversation.organization_id or not conversation.organization_id.strip():
        raise organization_exceptions.OrganizationIDRequired()

    if not conversation.customer_id or not conversation.customer_id.strip():
        raise customer_exceptions.CustomerIDRequiredError()

    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=conversation.organization_id.strip(),
    )

    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()

    customer = customers_repository.get_customer_by_id(
        db=db,
        customer_id=conversation.customer_id.strip(),
    )

    if customer is None:
        raise customer_exceptions.CustomerNotFoundError()

    # El cliente debe pertenecer a la organización.
    if customer.organization_id != organization.id:
        raise customer_exceptions.CustomerOrganizationMismatchError()

    return conversations_repository.create_conversation(
        db=db,
        organization_id=organization.id,
        customer_id=customer.id,
        status="OPEN",
    )


def update_conversation(
    db: Session,
    data: ConversationUpdate,
    conversation_id: str,
):

    if not conversation_id or not conversation_id.strip():
        raise conversation_exceptions.ConversationIdRequiered()

    conversation = conversations_repository.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id.strip(),
    )

    if conversation is None:
        raise conversation_exceptions.ConversationNotFound()

    if data.status is None:
        raise conversation_exceptions.InvalidConversationStatusError()

    resolved_at = conversation.resolved_at

    if data.status == "RESOLVED":
        if conversation.status != "RESOLVED" or resolved_at is None:
            resolved_at = datetime.now(timezone.utc)

    elif data.status in ("OPEN", "ESCALATED"):
        resolved_at = None

    # CLOSED conserva la fecha de resolución si existe.

    return conversations_repository.update_conversation(
        db=db,
        conversation_id=conversation.id,
        status=data.status,
        resolved_at=resolved_at,
    )