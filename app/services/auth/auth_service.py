# app/services/user_service.py
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from fastapi import HTTPException, status

class UserService:

    def __init__(self):
        self.repo = UserRepository()

    def create_user(self, db: Session, data: UserCreate):
        if self.repo.get_by_email(db, data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        return self.repo.create(db, data)

    def list_users(self, db: Session):
        return self.repo.list(db)
