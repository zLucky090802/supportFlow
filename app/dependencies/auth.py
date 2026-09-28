from collections.abc import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.exceptions.auth_exceptions import AuthenticationError, PermissionDeniedError
from app.models.generated_models import Users
from app.services import auth_service
from app.services.user_service import ALLOWED_ROLES


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    db: Session = Depends(get_db), token: str | None = Depends(oauth2_scheme),
) -> Users:
    if token is None:
        raise AuthenticationError()
    return auth_service.get_authenticated_user(db=db, token=token)


def require_roles(*roles: str) -> Callable:
    if not roles or not set(roles).issubset(ALLOWED_ROLES):
        raise ValueError("At least one supported role is required")

    def check_role(user: Users = Depends(get_current_user)) -> Users:
        if user.role not in roles:
            raise PermissionDeniedError()
        return user

    return check_role
