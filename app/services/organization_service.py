from app.repositories import organization_repository
from app.db.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from app.exceptions import organization_exceptions
from app.models.generated_models import Organizations

def get_organizations(db:Session):
    organizations = organization_repository.get_organizations(db)
    
    return {
        'success': True,
        'message':'Organizations retrieved succesfully',
        'data': organizations
    }
    
def get_organization_by_id(db:Session, organization_id:str):
    organization = organization_repository.get_organization_by_id(db=db, organization_id=organization_id)
    
    if organization is None:
        
        raise organization_exceptions.OrganizationNotFoundError()

    return {
        'success': True,
        'message':'Organization retrieved succesfully',
        'data': organization
    }
    
def create_organization(db:Session, name:str, email:str):
   
    if email is None:
        raise organization_exceptions.EmailRequieredError()
    if name is None:
        raise organization_exceptions.NameRequieredError()
    
    email = email.strip().lower()
    name = name.strip()
    existing = organization_repository.get_organization_by_email(db, email=email)
    
    if(existing): 
        raise organization_exceptions.ExistingEmailError()
    
    
    result = organization_repository.create_organization(db=db, name=name, email=email)
    
    return {
        'success': True,
        'message':'Organization created successfully',
        'data': result
    }
    
def update_organization(db:Session, organization_update:Organizations):
    organization = organization_repository.get_organization_by_id(db=db, organization_id=organization_update.id)
    
    existing = organization_repository.get_organization_by_email(db, organization_update.email)
    if organization_update.email is not None:
        organization_update.email = organization_update.email.strip().lower()
    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()
    
    if organization_update.name is not None:
        organization_update.name = organization_update.name.strip()
        
    if (
        existing is not None
        and existing.id != organization_update.id
    ):
        raise organization_exceptions.ExistingEmailError()
    
    updated = organization_repository.update_organization(db=db, organization_id=organization_update.id, name=organization_update.name, email= organization_update.email)

    return {
        'success': True,
        'message': 'Organization updated successfully',
        'data': updated
    }
    
def delete_organization(db:Session, organization_id:str):
    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=organization_id
    )
    
    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()
    
    deleted = organization_repository.delete_organization(
        db=db,
        organization_id=organization_id
    )
    
    return{
        'success':True,
        'message': 'Organization deleted succesfully',
        'data': deleted
    }