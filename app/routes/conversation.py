
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.services import authorization_service as authorization

from app.schemas.conversations import (
    ConversationAssignment,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationUpdate,
)

from app.services import conversations as conversation_service
from app.services import conversation_assignment_service as assignment_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# GET ALL CONVERSATIONS
@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ConversationListResponse
)
def get_conversations(
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        conversations = authorization.list_conversations(db, actor)

        response = {
            "success": True,
            "message": "Conversations retrieved successfully",
            "data": conversations
        }

        # Validación temporal para identificar el error 500.
        validated_response = ConversationListResponse.model_validate(
            response
        )

        return validated_response

    except Exception:
        logger.exception(
            "ERROR: GET /conversations failed"
        )
        raise


# GET CONVERSATIONS BY ORGANIZATION
@router.get(
    "/by-organization/{organization_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationListResponse
)
def get_conversation_by_organization_id(
    organization_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    authorization.require_organization(actor, organization_id)
    conversations = (
        authorization.list_conversations(db, actor)
    )

    return {
        "success": True,
        "message": "Organization conversations retrieved successfully",
        "data": conversations
    }


# GET CONVERSATIONS BY CUSTOMER
@router.get(
    "/by-customer/{customer_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationListResponse
)
def get_conversation_by_customer_id(
    customer_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = (
        authorization.list_conversations(db, actor, customer_id=customer_id)
    )

    return {
        "success": True,
        "message": "Customer conversations retrieved successfully",
        "data": conversations
    }


@router.get("/me", response_model=ConversationListResponse)
def get_my_conversations(
    actor: Users = Depends(get_current_user), db: Session = Depends(get_db),
):
    conversations = assignment_service.list_my_conversations(db, actor)
    return {"success": True, "message": "Assigned conversations retrieved successfully", "data": conversations}


@router.get("/by-agent/{agent_id}", response_model=ConversationListResponse)
def get_agent_conversations(
    agent_id: str, actor: Users = Depends(get_current_user), db: Session = Depends(get_db),
):
    conversations = assignment_service.list_agent_conversations(db, actor, agent_id)
    return {"success": True, "message": "Agent conversations retrieved successfully", "data": conversations}


# GET CONVERSATION BY ID
@router.get(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    authorization.require_conversation(db, actor, conversation_id)
    conversation = conversation_service.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id
    )

    return {
        "success": True,
        "message": "Conversation retrieved successfully",
        "data": conversation
    }


# CREATE CONVERSATION
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ConversationDetailResponse
)
def create_conversation(
    data: ConversationCreate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    authorization.require_conversation_creation(db, actor, data.organization_id, data.customer_id)
    new_conversation = conversation_service.create_conversation(
        db=db,
        conversation=data
    )

    return {
        "success": True,
        "message": "Conversation created successfully",
        "data": new_conversation
    }


# UPDATE CONVERSATION
@router.patch(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationDetailResponse
)
def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updated = conversation_service.update_staff_conversation(
        db=db, actor=actor, data=data, conversation_id=conversation_id,
    )

    return {
        "success": True,
        "message": "Conversation updated successfully",
        "data": updated
    }


@router.patch("/{conversation_id}/assign", response_model=ConversationDetailResponse)
def assign_conversation(
    conversation_id: str, data: ConversationAssignment,
    actor: Users = Depends(get_current_user), db: Session = Depends(get_db),
):
    conversation = assignment_service.assign_conversation(db, actor, conversation_id, data.agent_id)
    return {"success": True, "message": "Conversation assigned successfully", "data": conversation}


@router.patch("/{conversation_id}/unassign", response_model=ConversationDetailResponse)
def unassign_conversation(
    conversation_id: str, actor: Users = Depends(get_current_user), db: Session = Depends(get_db),
):
    conversation = assignment_service.unassign_conversation(db, actor, conversation_id)
    return {"success": True, "message": "Conversation unassigned successfully", "data": conversation}
