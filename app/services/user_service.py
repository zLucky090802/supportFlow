from collections.abc import Sequence

from email_validator import EmailNotValidError, validate_email
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import organization_exceptions, user_exceptions
from app.models.generated_models import Organizations, Users
from app.repositories import organization_repository, users_repository
from app.schemas.users import UserCreate, UserUpdate
from app.security.passwords import hash_password


ALLOWED_ROLES = frozenset({"ADMIN", "SUPERVISOR", "AGENT"})
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name or len(name) > 50:
        raise user_exceptions.InvalidUserNameError()
    return name


def _validate_email(email: str) -> str:
    try:
        email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise user_exceptions.InvalidUserEmailError() from None
    if len(email) > 100:
        raise user_exceptions.InvalidUserEmailError()
    return email


def _validate_role(role: str) -> str:
    if role not in ALLOWED_ROLES:
        raise user_exceptions.InvalidUserRoleError(
            "Role must be ADMIN, SUPERVISOR or AGENT"
        )
    return role


def _validate_password(password: SecretStr) -> str:
    value = password.get_secret_value()
    if not value.strip() or not MIN_PASSWORD_LENGTH <= len(value) <= MAX_PASSWORD_LENGTH:
        raise user_exceptions.InvalidUserPasswordError(
            f"Password must contain between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters"
        )
    # Spaces are part of the password and must not be stripped before hashing.
    return value


def _get_organization(db: Session, organization_id: str) -> Organizations:
    if not organization_id or not organization_id.strip():
        raise organization_exceptions.OrganizationIDRequired()
    organization = organization_repository.get_organization_by_id(
        db=db, organization_id=organization_id.strip(),
    )
    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()
    return organization


def _check_email_available(db: Session, email: str, user_id: str | None = None) -> None:
    existing = users_repository.get_user_by_email(db=db, user_email=email)
    if existing is not None and existing.id != user_id:
        raise user_exceptions.ExistingEmailError()


def _mysql_error_code(exc: IntegrityError) -> int | None:
    code = getattr(exc.orig, "errno", None)
    if code is None and exc.orig.args:
        code = exc.orig.args[0]
    return code if isinstance(code, int) else None


def get_users(db: Session) -> Sequence[Users]:
    return users_repository.get_users(db=db)


def get_user_by_id(db: Session, user_id: str) -> Users:
    if not user_id or not user_id.strip():
        raise user_exceptions.UserIDRequiredError()
    user = users_repository.get_user_by_id(db=db, user_id=user_id.strip())
    if user is None:
        raise user_exceptions.UserNotFoundError()
    return user


def get_user_by_email(db: Session, user_email: str) -> Users:
    email = _validate_email(user_email)
    user = users_repository.get_user_by_email(db=db, user_email=email)
    if user is None:
        raise user_exceptions.UserNotFoundError()
    return user


def get_users_by_organization_id(db: Session, organization_id: str) -> Sequence[Users]:
    organization = _get_organization(db, organization_id)
    return users_repository.get_users_by_organization_id(db=db, organization_id=organization.id)


def create_user(db: Session, user: UserCreate) -> Users:
    organization = _get_organization(db, user.organization_id)
    name = _validate_name(user.name)
    email = _validate_email(user.email)
    role = _validate_role(user.role)
    password = _validate_password(user.password)
    _check_email_available(db, email)
    password_hash = hash_password(password)
    try:
        return users_repository.create_user(
            db=db, organization_id=organization.id, name=name,
            email=email, password_hash=password_hash, role=role,
        )
    except IntegrityError as exc:
        # MySQL's unique index also protects against concurrent duplicate emails.
        if _mysql_error_code(exc) == 1062:
            raise user_exceptions.ExistingEmailError() from None
        raise


def update_user(db: Session, user: UserUpdate, user_id: str) -> Users:
    existing = get_user_by_id(db, user_id)
    name = _validate_name(user.name) if user.name is not None else existing.name
    email = _validate_email(user.email) if user.email is not None else existing.email
    role = _validate_role(user.role) if user.role is not None else existing.role
    password = _validate_password(user.password) if user.password is not None else None
    if user.email is not None:
        _check_email_available(db, email, existing.id)
    password_hash = hash_password(password) if password is not None else None
    try:
        updated = users_repository.update_user(
            db=db, user_id=existing.id, name=name, email=email,
            role=role, password_hash=password_hash,
        )
    except IntegrityError as exc:
        if _mysql_error_code(exc) == 1062:
            raise user_exceptions.ExistingEmailError() from None
        raise
    if updated is None:
        raise user_exceptions.UserNotFoundError()
    return updated


def delete_user(db: Session, user_id: str) -> bool:
    user = get_user_by_id(db, user_id)
    if users_repository.has_assigned_conversations(db=db, user_id=user.id):
        raise user_exceptions.UserInUseError()
    try:
        deleted = users_repository.delete_user(db=db, user_id=user.id)
    except IntegrityError as exc:
        # An assignment can be created between the precheck and the DELETE.
        if _mysql_error_code(exc) == 1451:
            raise user_exceptions.UserInUseError() from None
        raise
    if not deleted:
        raise user_exceptions.UserNotFoundError()
    return True
