from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.services import authorization_service as authorization
from app.schemas.messages import (
    StaffMessageCreate,
    MessageContent,
    MessageDetailResponse,
    MessageListResponse,
)
from app.services import message_service


router = APIRouter(prefix="/messages", tags=["Messages"])
conversation_router = APIRouter(prefix="/conversations", tags=["Messages"])


@conversation_router.get(
    "/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=MessageListResponse,
)
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
    data: StaffMessageCreate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = message_service.create_staff_message(
        db=db, actor=actor, conversation_id=data.conversation_id, content=data.content,
    )
    return {
        "success": True,
        "message": "Message created successfully",
        "data": message,
    }


@conversation_router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageDetailResponse,
)
def create_conversation_message(
    conversation_id: str,
    data: MessageContent,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = message_service.create_staff_message(
        db=db, actor=actor, conversation_id=conversation_id, content=data.content,
    )
    return {
        "success": True,
        "message": "Message created successfully",
        "data": message,
    }
