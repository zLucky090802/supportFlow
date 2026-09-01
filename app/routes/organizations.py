from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.organization import(
    OrganizarionCreate,
    OrganizationResponse
)
from app.repositories.organization_repository import(
    create_organization,
    get_organizations,
    get_organization_by_id
)

router = APIRouter(
    prefix='/organizarions',
    tags=['Organizations']
)

@router.post(
    '',
    response_model=OrganizationResponse
)
def create(
    data: OrganizarionCreate,
    db: Session = Depends(get_db)
):
    return create_organization(
        db,
        data.name,
        data.email
    )

@router.get('')
def get_all(
    db:Session = Depends(get_db)
):
    return get_organizations(db)


@router.get('/{organization_id}')
def get_by_id(
    organization_id:str,
    db:Session = Depends(get_db)
):
    organization = get_organization_by_id(
        db, 
        organization_id
    )
    
    if not organization:
        raise HTTPException(
            status_code=404,
            detail='Organization not found'
        )
        
    return organization