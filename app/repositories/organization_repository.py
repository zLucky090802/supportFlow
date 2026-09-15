from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError 
from sqlalchemy.orm import Session
from app.models.generated_models import Organizations

def create_organization(
    db:Session,
    name: str,
    email: str | None
):
   try:
        
        organization = Organizations(
            name= name,
            email= email
        )
        
        db.add(organization)
        db.commit()
        db.refresh(organization)
        
        return organization

   except SQLAlchemyError:
       db.rollback()
       raise


def get_organizations(db: Session):
    try:
        stmt = select(Organizations)
    
        return db.scalars(stmt).all()
    except SQLAlchemyError:
        raise

def get_organization_by_id(
    db:Session,
    organization_id:str
):
    stmt = select(Organizations).where(
        Organizations.id == organization_id
    )
    
    return db.scalar(stmt)

def update_organization(db:Session, organization_id:str, name:str, email:str):
    try:
        stmt = (
            update(Organizations)
            .where(Organizations.id == organization_id)
            .values(
                name= name,
                email=email
            )
        )
        
        db.execute(stmt)
        db.commit()
        
        return get_organization_by_id(db, organization_id)
    
    except SQLAlchemyError:
        db.rollback()
        raise

def delete_organization(db:Session, organization_id:str):
    try:
        stmt = (
            delete(Organizations)
            .where(Organizations.id == organization_id)
        )
        result = db.execute(stmt)
        db.commit()
        
        return result.rowcount > 0
    
    except SQLAlchemyError:
        db.rollback()
        raise
 


def get_organization_by_email(db:Session, email:str):
    try:
        stmt = select(Organizations) .where(Organizations.email == email)
        
        return db.scalar(stmt)
    
    except SQLAlchemyError:
        raise