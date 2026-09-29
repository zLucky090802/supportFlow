from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.services import authorization_service as authorization
from app.schemas.messages import (
    MessageCreate,
    MessageDetailResponse,
    MessageListResponse,
)
from app.services import message_service


router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get(
    "/by-conversation/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageListResponse,
)
def get_messages_by_conversation_id(
    conversation_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_conversation(db, actor, conversation_id)
    messages = message_service.get_messages_by_conversation_id(
        db=db,
        conversation_id=conversation_id,
    )
    return {
        "success": True,
        "message": "Conversation messages retrieved successfully",
        "data": messages,
    }


@router.get(
    "/{message_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageDetailResponse,
)
def get_message_by_id(
    message_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_message(db, actor, message_id)
    message = message_service.get_message_by_id(db=db, message_id=message_id)
    return {
        "success": True,
        "message": "Message retrieved successfully",
        "data": message,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageDetailResponse,
)
def create_message(
    data: MessageCreate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        authorization.require_message_sender(db, actor, data, lock=True)
        message = message_service.create_message(db=db, message=data)
    except Exception:
        db.rollback()
        raise
    return {
        "success": True,
        "message": "Message created successfully",
        "data": message,
    }
