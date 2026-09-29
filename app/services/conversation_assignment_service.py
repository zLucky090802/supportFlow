from sqlalchemy.orm import Session

from app.exceptions.auth_exceptions import ResourceNotFoundError
from app.exceptions.user_exceptions import InvalidUserRoleError
from app.models.generated_models import Users
from app.repositories import conversations_repository, users_repository
from app.services import authorization_service as authorization


def _get_agent(db: Session, actor: Users, agent_id: str, *, lock: bool = False) -> Users:
    lookup = users_repository.get_user_for_update if lock else users_repository.get_user_by_id
    agent = lookup(db=db, user_id=agent_id.strip())
    if agent is None or agent.organization_id != actor.organization_id:
        raise ResourceNotFoundError()
    if agent.role != "AGENT":
        raise InvalidUserRoleError("Assigned user must have role AGENT")
    return agent


def assign_conversation(db: Session, actor: Users, conversation_id: str, agent_id: str):
    try:
        conversation = authorization.require_conversation(db, actor, conversation_id, lock=True)
        authorization.require_role(actor, "ADMIN", "SUPERVISOR")
        agent = _get_agent(db, actor, agent_id, lock=True)
        return conversations_repository.set_conversation_assignment(db, conversation, agent.id)
    except Exception:
        db.rollback()
        raise


def unassign_conversation(db: Session, actor: Users, conversation_id: str):
    try:
        conversation = authorization.require_conversation(db, actor, conversation_id, lock=True)
        authorization.require_role(actor, "ADMIN", "SUPERVISOR")
        return conversations_repository.set_conversation_assignment(db, conversation, None)
    except Exception:
        db.rollback()
        raise


def list_my_conversations(db: Session, actor: Users):
    authorization.require_organization(actor, actor.organization_id)
    authorization.require_role(actor, "ADMIN", "SUPERVISOR", "AGENT")
    return conversations_repository.get_scoped_conversations(
        db=db, organization_id=actor.organization_id, assigned_agent_id=actor.id,
    )


def list_agent_conversations(db: Session, actor: Users, agent_id: str):
    agent = _get_agent(db, actor, agent_id)
    authorization.require_role(actor, "ADMIN", "SUPERVISOR")
    return conversations_repository.get_scoped_conversations(
        db=db, organization_id=actor.organization_id, assigned_agent_id=agent.id,
    )
