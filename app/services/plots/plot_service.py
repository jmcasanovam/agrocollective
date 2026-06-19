from uuid import UUID

from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.repositories.plot_repository import plot_repository
from app.repositories.farm_repository import farm_repository

from app.schemas.plot import PlotCreate


class PlotService:


    def create(
        self,
        db: Session,
        plot_data: PlotCreate,
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

        return plot_repository.create(
            db,
            plot_data,
            farm_id
        )


    def get_all(
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


        return plot_repository.get_all_by_farm(
            db,
            farm_id
        )


plot_service = PlotService()