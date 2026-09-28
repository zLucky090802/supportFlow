from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.generated_models import Users
from app.schemas.auth import TokenResponse
from app.schemas.users import UserDetailResponse
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return auth_service.login(db=db, email=form.username, password=form.password)


@router.get("/me", response_model=UserDetailResponse)
def current_user(user: Users = Depends(get_current_user)):
    return {"success": True, "message": "Current user retrieved successfully", "data": user}
