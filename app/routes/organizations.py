from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.services import authorization_service as authorization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationDetailResponse,
    OrganizationListResponse
)
from app.services import organization_service


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrganizationCreate
)
def create_organization(
    data: OrganizationCreate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
    
):
    authorization.deny_platform_operation()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=OrganizationListResponse
)
def get_organizations(
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    organizations = [organization_service.get_organization_by_id(db=db, organization_id=actor.organization_id)]

    return {
        "success": True,
        "message": "Organizations retrieved successfully",
        "data": organizations
    }


@router.get(
    "/{organization_id}",
    status_code=status.HTTP_200_OK,
    response_model= OrganizationDetailResponse
)
def get_organization_by_id(
    organization_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
    
):
    authorization.require_organization(actor, organization_id)
    organization = organization_service.get_organization_by_id(
        db=db,
        organization_id=organization_id
    )

    return {
        "success": True,
        "message": "Organization retrieved successfully",
        "data": organization
    }


@router.patch(
    "/{organization_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrganizationDetailResponse
)
def update_organization(
    organization_id: str,
    organization: OrganizationUpdate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
    
):
    authorization.require_organization_management(actor, organization_id)
    updated = organization_service.update_organization(
        db=db,
        organization_id=organization_id,
        organization_update=organization
    )

    return {
        "success": True,
        "message": "Organization updated successfully",
        "data": updated
    }


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_organization(
    organization_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    authorization.deny_platform_operation()
