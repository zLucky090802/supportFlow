
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


ConversationStatus = Literal[
    "OPEN",
    "ESCALATED",
    "RESOLVED",
    "CLOSED"
]


class ConversationCreate(BaseModel):
    organization_id: str
    customer_id: str


class ConversationUpdate(BaseModel):
    status: ConversationStatus | None = None


class ConversationAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    customer_id: str
    assigned_agent_id: str | None = None
    status: ConversationStatus

    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None


class ConversationDetailResponse(BaseModel):
    success: bool
    message: str
    data: ConversationResponse


class ConversationListResponse(BaseModel):
    success: bool
    message: str
    data: list[ConversationResponse]
