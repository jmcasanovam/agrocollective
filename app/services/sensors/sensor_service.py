from uuid import UUID

from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.repositories.plot_repository import plot_repository
from app.repositories.sensor_repository import sensor_repository

from app.schemas.sensor import SensorCreate


class SensorService:


    def create(
        self,
        db: Session,
        sensor_data: SensorCreate,
        plot_id: UUID,
        user_id: UUID
    ):

        plot = plot_repository.get_by_id(
            db,
            plot_id
        )

        if not plot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plot not found"
            )

        existing_sensor = (
            sensor_repository.get_by_esp32_id(
                db,
                sensor_data.esp32_id
            )
        )

        if existing_sensor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ESP32 already registered"
            )

        return sensor_repository.create(
            db,
            sensor_data,
            plot_id
        )


    def get_all(
        self,
        db: Session,
        plot_id: UUID
    ):

        return sensor_repository.get_all_by_plot(
            db,
            plot_id
        )


    def get_by_id(
        self,
        db: Session,
        sensor_id: UUID
    ):

        sensor = sensor_repository.get_by_id(
            db,
            sensor_id
        )

        if not sensor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sensor not found"
            )

        return sensor


sensor_service = SensorService()