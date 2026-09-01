from pydantic import BaseModel, EmailStr
 
class OrganizarionCreate(BaseModel):
    name:str
    email: EmailStr | None = None
    
    
    
class OrganizationResponse(BaseModel):
    id: str
    name: str
    email: EmailStr | None = None
    
    model_config = {
        'from_attributes':True
    }