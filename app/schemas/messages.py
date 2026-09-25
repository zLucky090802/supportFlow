
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.generated_models import MessagesSenderType


class MessageCreate(BaseModel):
    conversation_id: str
    sender_type: MessagesSenderType
    sender_id: str | None = None
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message content cannot be empty")

        return value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_type: MessagesSenderType
    sender_id: str | None = None
    content: str
    created_at: datetime | None = None


class MessageDetailResponse(BaseModel):
    success: bool
    message: str
    data: MessageResponse


class MessageListResponse(BaseModel):
    success: bool
    message: str
    data: list[MessageResponse]
