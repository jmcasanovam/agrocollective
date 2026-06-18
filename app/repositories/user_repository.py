# app/repositories/user_repository.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password  # si tienes hashing

class UserRepository:

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, user_data: UserCreate) -> User:
        db_user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            region=user_data.region
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def list(self, db: Session) -> list[User]:
        return db.query(User).all()
