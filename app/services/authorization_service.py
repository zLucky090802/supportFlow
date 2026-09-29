"""Resource authorization for authenticated staff endpoints."""
from sqlalchemy.orm import Session

from app.exceptions.auth_exceptions import PermissionDeniedError
from app.models.generated_models import Users
from app.repositories import conversations_repository
from app.services import conversations, customer_service, message_service, user_service


def require_organization(actor: Users, organization_id: str) -> None:
    if not actor.organization_id or not organization_id or actor.organization_id != organization_id.strip():
        raise PermissionDeniedError()


def require_role(actor: Users, *roles: str) -> None:
    if actor.role not in roles:
        raise PermissionDeniedError()


def require_user_management(actor: Users, organization_id: str) -> None:
    require_organization(actor, organization_id)
    require_role(actor, "ADMIN")


def require_customer_management(actor: Users, organization_id: str) -> None:
    require_organization(actor, organization_id)
    require_role(actor, "ADMIN", "SUPERVISOR")


def require_organization_management(actor: Users, organization_id: str) -> None:
    require_organization(actor, organization_id)
    require_role(actor, "ADMIN")


def deny_platform_operation() -> None:
    # Organization onboarding/deletion needs a separate platform permission.
    raise PermissionDeniedError()


def require_user(db: Session, actor: Users, user_id: str):
    user = user_service.get_user_by_id(db, user_id)
    require_user_management(actor, user.organization_id)
    return user


def require_customer(db: Session, actor: Users, customer_id: str):
    customer = customer_service.get_customer_by_id(db, customer_id)
    require_organization(actor, customer.organization_id)
    return customer


def require_conversation(db: Session, actor: Users, conversation_id: str):
    conversation = conversations.get_conversation_by_id(db, conversation_id)
    require_organization(actor, conversation.organization_id)
    require_role(actor, "ADMIN", "SUPERVISOR", "AGENT")
    if actor.role == "AGENT" and conversation.assigned_agent_id != actor.id:
        raise PermissionDeniedError()
    return conversation


def list_conversations(db: Session, actor: Users, customer_id: str | None = None):
    require_organization(actor, actor.organization_id)
    if customer_id is not None:
        require_customer(db, actor, customer_id)
    require_role(actor, "ADMIN", "SUPERVISOR", "AGENT")
    return conversations_repository.get_scoped_conversations(
        db=db, organization_id=actor.organization_id,
        assigned_agent_id=actor.id if actor.role == "AGENT" else None,
        customer_id=customer_id,
    )


def require_conversation_creation(db: Session, actor: Users, organization_id: str, customer_id: str) -> None:
    require_organization(actor, organization_id)
    require_customer(db, actor, customer_id)
    require_role(actor, "ADMIN", "SUPERVISOR")


def require_message(db: Session, actor: Users, message_id: str):
    message = message_service.get_message_by_id(db, message_id)
    require_conversation(db, actor, message.conversation_id)
    return message


def require_message_sender(db: Session, actor: Users, message) -> None:
    require_conversation(db, actor, message.conversation_id)
    if message.sender_type != "AGENT" or message.sender_id != actor.id:
        raise PermissionDeniedError()
