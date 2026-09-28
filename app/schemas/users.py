from datetime import datetime

from pydantic import BaseModel, ConfigDict, SecretStr


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    name: str
    email: str
    password: SecretStr
    role: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    password: SecretStr | None = None
    role: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    email: str
    role: str
    created_at: datetime | None = None


class UserDetailResponse(BaseModel):
    success: bool
    message: str
    data: UserResponse


class UserListResponse(BaseModel):
    success: bool
    message: str
    data: list[UserResponse]
