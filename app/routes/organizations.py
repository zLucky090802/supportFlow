from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate
)
from app.services import organization_service


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    created = organization_service.create_organization(
        db=db,
        organization_create=data
    )

    return {
        "success": True,
        "message": "Organization created successfully",
        "data": created
    }


@router.get(
    "",
    status_code=status.HTTP_200_OK
)
def get_organizations(
    db: Session = Depends(get_db)
):
    organizations = organization_service.get_organizations(
        db=db
    )

    return {
        "success": True,
        "message": "Organizations retrieved successfully",
        "data": organizations
    }


@router.get(
    "/{organization_id}",
    status_code=status.HTTP_200_OK
)
def get_organization_by_id(
    organization_id: str,
    db: Session = Depends(get_db)
):
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
    status_code=status.HTTP_200_OK
)
def update_organization(
    organization_id: str,
    organization: OrganizationUpdate,
    db: Session = Depends(get_db)
):
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
    db: Session = Depends(get_db)
):
    organization_service.delete_organization(
        db=db,
        organization_id=organization_id
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )