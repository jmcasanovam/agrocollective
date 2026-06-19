from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db

from app.schemas.user import UserCreate
from app.schemas.user import UserLogin
from app.schemas.user import UserResponse
from app.schemas.user import TokenResponse

from app.services.auth.auth_service import auth_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):

    return auth_service.register(
        db,
        user_data
    )


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):

    return auth_service.login(
        db,
        credentials
    )