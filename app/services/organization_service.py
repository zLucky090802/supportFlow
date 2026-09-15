from app.repositories import organization_repository
from app.db.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends

def get_organizations(db:Session):
    organizations = organization_repository.get_organizations(db)
    
    return {
        'success': True,
        'message':'Organizations retrieved succesfully',
        'data': organizations
    }