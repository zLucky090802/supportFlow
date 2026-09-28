from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
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
    db: Session = Depends(get_db),
):
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
def get_message_by_id(message_id: str, db: Session = Depends(get_db)):
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
def create_message(data: MessageCreate, db: Session = Depends(get_db)):
    message = message_service.create_message(db=db, message=data)
    return {
        "success": True,
        "message": "Message created successfully",
        "data": message,
    }
