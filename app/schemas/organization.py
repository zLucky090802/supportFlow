from pydantic import BaseModel, EmailStr, ConfigDict


class OrganizationCreate(BaseModel):
    name: str
    email: EmailStr


class OrganizationUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str | None