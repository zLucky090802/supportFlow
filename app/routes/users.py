from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.services import authorization_service as authorization
from app.schemas.users import (
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserUpdate,
)
from app.services import user_service


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", status_code=status.HTTP_200_OK, response_model=UserListResponse)
def get_users(
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_user_management(actor, actor.organization_id)
    users = user_service.get_users_by_organization_id(db=db, organization_id=actor.organization_id)
    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users,
    }


@router.get(
    "/by-email",
    status_code=status.HTTP_200_OK,
    response_model=UserDetailResponse,
)
def get_user_by_email(
    email: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = user_service.get_user_by_email(db=db, user_email=email)
    authorization.require_user_management(actor, user.organization_id)
    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": user,
    }


@router.get(
    "/by-organization/{organization_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserListResponse,
)
def get_users_by_organization_id(
    organization_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_user_management(actor, organization_id)
    users = user_service.get_users_by_organization_id(
        db=db, organization_id=organization_id,
    )
    return {
        "success": True,
        "message": "Organization users retrieved successfully",
        "data": users,
    }


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserDetailResponse,
)
def get_user_by_id(
    user_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = user_service.get_user_by_id(db=db, user_id=user_id)
    authorization.require_user_management(actor, user.organization_id)
    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": user,
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserDetailResponse)
def create_user(
    data: UserCreate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_user_management(actor, data.organization_id)
    user = user_service.create_user(db=db, user=data)
    return {
        "success": True,
        "message": "User created successfully",
        "data": user,
    }


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserDetailResponse,
)
def update_user(
    user_id: str, data: UserUpdate,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization.require_user(db, actor, user_id)
    user = user_service.update_user(db=db, user=data, user_id=user_id)
    return {
        "success": True,
        "message": "User updated successfully",
        "data": user,
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    actor: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    authorization.require_user(db, actor, user_id)
    user_service.delete_user(db=db, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
