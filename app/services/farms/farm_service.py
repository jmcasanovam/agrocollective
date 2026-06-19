from uuid import UUID

from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.repositories.farm_repository import farm_repository

from app.schemas.farm import FarmCreate


class FarmService:


    def create(
        self,
        db: Session,
        farm_data: FarmCreate,
        user_id: UUID
    ):

        return farm_repository.create(
            db,
            farm_data,
            user_id
        )


    def get_all(
        self,
        db: Session,
        user_id: UUID
    ):

        return farm_repository.get_all_by_user(
            db,
            user_id
        )


    def get_by_id(
        self,
        db: Session,
        farm_id: UUID,
        user_id: UUID
    ):

        farm = farm_repository.get_by_id(
            db,
            farm_id,
            user_id
        )

        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Farm not found"
            )

        return farm


farm_service = FarmService()