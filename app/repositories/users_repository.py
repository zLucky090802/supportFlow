from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.generated_models import Users


def get_users(db: Session) -> Sequence[Users]:
    return db.scalars(select(Users)).all()


def get_user_by_id(db: Session, user_id: str) -> Users | None:
    return db.get(Users, user_id)


def get_user_by_email(db: Session, user_email: str) -> Users | None:
    stmt = select(Users).where(Users.email == user_email)
    return db.scalar(stmt)


def get_users_by_organization_id(
    db: Session,
    organization_id: str,
) -> Sequence[Users]:
    stmt = select(Users).where(Users.organization_id == organization_id)
    return db.scalars(stmt).all()


def create_user(
    db: Session,
    organization_id: str,
    name: str,
    email: str,
    password_hash: str,
    role: str,
) -> Users:
    """Persist a user with a password hash already calculated by the caller."""
    try:
        user = Users(
            organization_id=organization_id,
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise


def update_user(
    db: Session,
    user_id: str,
    name: str,
    email: str,
    role: str,
    password_hash: str | None = None,
) -> Users | None:
    """Update profile fields; None keeps the existing password hash."""
    try:
        user = get_user_by_id(db=db, user_id=user_id)
        if user is None:
            return None

        user.name = name
        user.email = email
        user.role = role
        if password_hash is not None:
            user.password_hash = password_hash

        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise


def delete_user(db: Session, user_id: str) -> bool:
    try:
        stmt = delete(Users).where(Users.id == user_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError:
        db.rollback()
        raise
