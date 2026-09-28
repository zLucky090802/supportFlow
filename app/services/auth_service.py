from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import Session

from app.exceptions.auth_exceptions import AuthenticationError
from app.models.generated_models import Users
from app.repositories import users_repository
from app.security.passwords import verify_password
from app.security.tokens import ACCESS_TOKEN_EXPIRE_SECONDS, create_access_token, decode_access_token
from app.services.user_service import ALLOWED_ROLES


# A syntactically valid dummy digest makes unknown-email attempts perform scrypt too.
_DUMMY_HASH = "scrypt$131072$8$1$" + "00" * 16 + "$" + "00" * 64


def login(db: Session, email: str, password: str) -> dict:
    if len(email) > 320 or not 1 <= len(password) <= 128:
        raise AuthenticationError()
    try:
        email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        verify_password(password, _DUMMY_HASH)
        raise AuthenticationError() from None
    user = users_repository.get_user_by_email(db=db, user_email=email)
    valid_password = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not valid_password or user is None or user.role not in ALLOWED_ROLES:
        raise AuthenticationError()
    return {"access_token": create_access_token(user.id), "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS}


def get_authenticated_user(db: Session, token: str) -> Users:
    user_id = decode_access_token(token)
    user = users_repository.get_user_by_id(db=db, user_id=user_id)
    if user is None or user.role not in ALLOWED_ROLES:
        raise AuthenticationError()
    return user
