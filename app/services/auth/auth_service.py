from sqlalchemy.orm import Session

from fastapi import HTTPException
from fastapi import status

from app.schemas.user import UserCreate
from app.schemas.user import UserLogin
from app.schemas.user import TokenResponse

from app.repositories.user_repository import user_repository

from app.core.security import hash_password
from app.core.security import verify_password
from app.core.security import create_access_token


class AuthService:

    def register(
        self,
        db: Session,
        user_data: UserCreate
    ):

        if user_repository.exists_by_email(
            db,
            user_data.email
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        password_hash = hash_password(
            user_data.password
        )

        return user_repository.create(
            db,
            user_data,
            password_hash
        )

    def login(
        self,
        db: Session,
        credentials: UserLogin
    ) -> TokenResponse:

        user = user_repository.get_by_email(
            db,
            credentials.email
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not verify_password(
            credentials.password,
            user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User disabled"
            )

        token = create_access_token(
            str(user.id)
        )

        return TokenResponse(
            access_token=token
        )


auth_service = AuthService()