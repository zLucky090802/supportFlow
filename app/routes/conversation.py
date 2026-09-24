
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas.conversations import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationUpdate,
)

from app.services import conversations as conversation_service


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
    db: Session = Depends(get_db)
):
    try:
        conversations = conversation_service.get_conversations(
            db=db
        )

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
    db: Session = Depends(get_db)
):
    conversations = (
        conversation_service.get_conversation_by_organization_id(
            db=db,
            organization_id=organization_id
        )
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
    db: Session = Depends(get_db)
):
    conversations = (
        conversation_service.get_conversation_by_customer_id(
            db=db,
            customer_id=customer_id
        )
    )

    return {
        "success": True,
        "message": "Customer conversations retrieved successfully",
        "data": conversations
    }


# GET CONVERSATION BY ID
@router.get(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
    updated = conversation_service.update_conversation(
        db=db,
        data=data,
        conversation_id=conversation_id
    )

    return {
        "success": True,
        "message": "Conversation updated successfully",
        "data": updated
    }