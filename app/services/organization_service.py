from sqlalchemy.orm import Session

from app.repositories import organization_repository
from app.exceptions import organization_exceptions
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate
)


def get_organizations(db: Session):
    return organization_repository.get_organizations(db)


def get_organization_by_id(
    db: Session,
    organization_id: str
):
    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=organization_id
    )

    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()

    return organization


def create_organization(
    db: Session,
    organization_create: OrganizationCreate
):
    name = organization_create.name.strip()
    email = str(organization_create.email).strip().lower()

    if not name:
        raise organization_exceptions.InvalidOrganizationNameError()

    existing = organization_repository.get_organization_by_email(
        db=db,
        email=email
    )

    if existing is not None:
        raise organization_exceptions.ExistingEmailError()

    return organization_repository.create_organization(
        db=db,
        name=name,
        email=email
    )


def update_organization(
    db: Session,
    organization_id: str,
    organization_update: OrganizationUpdate
):
    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=organization_id
    )

    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()

    if organization_update.name is not None:
        name = organization_update.name.strip()

        if not name:
            raise organization_exceptions.InvalidOrganizationNameError()
    else:
        name = organization.name

    if organization_update.email is not None:
        email = str(organization_update.email).strip().lower()

        existing = organization_repository.get_organization_by_email(
            db=db,
            email=email
        )

        if existing is not None and existing.id != organization_id:
            raise organization_exceptions.ExistingEmailError()
    else:
        email = organization.email

    return organization_repository.update_organization(
        db=db,
        organization_id=organization_id,
        name=name,
        email=email
    )


def delete_organization(
    db: Session,
    organization_id: str
):
    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=organization_id
    )

    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()

    return organization_repository.delete_organization(
        db=db,
        organization_id=organization_id
    )