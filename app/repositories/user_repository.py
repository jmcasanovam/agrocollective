from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:

    def get_by_email(
        self,
        db: Session,
        email: str
    ) -> User | None:
        return (
            db.query(User)
            .filter(User.email == email)
            .first()
        )


    def get_by_id(
        self,
        db: Session,
        user_id: UUID
    ) -> User | None:
        return (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )


    def create(
        self,
        db: Session,
        user: UserCreate,
        password_hash: str
    ) -> User:

        db_user = User(
            email=user.email,
            password_hash=password_hash,
            region=user.region
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user


    def exists_by_email(
        self,
        db: Session,
        email: str
    ) -> bool:

        return (
            db.query(User)
            .filter(User.email == email)
            .first()
            is not None
        )
    
user_repository = UserRepository()