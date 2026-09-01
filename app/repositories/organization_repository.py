from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.generated_models import Organizations

def create_organization(
    db:Session,
    name: str,
    email: str | None
):
    organization = Organizations(
        name= name,
        email= email
    )
    
    db.add(organization)
    db.commit()
    db.refresh(organization)
    
    return organization

def get_organizations(db: Session):
    stmt = select(Organizations)
    
    return db.scalars(stmt).all()

def get_organization_by_id(
    db:Session,
    organization_id:str
):
    stmt = select(Organizations).where(
        Organizations.id == organization_id
    )
    
    return db.scalar(stmt)

