from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerCreate(BaseModel):
    organization_id: str
    name: str
    email: EmailStr


class CustomerUpdate(BaseModel):
   
    name: str | None = None
    email: EmailStr | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    email: str
    created_at: datetime | None
    
class CustomerDetailResponse(BaseModel):
    success: bool
    message: str
    data: CustomerResponse


class CustomerListResponse(BaseModel):
    success: bool
    message: str
    data: list[CustomerResponse]