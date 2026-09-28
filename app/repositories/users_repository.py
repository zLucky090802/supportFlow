from sqlalchemy.orm import Session

from app.models.generated_models import Users


def get_user_by_id(db: Session, user_id: str) -> Users | None:
    return db.get(Users, user_id)
