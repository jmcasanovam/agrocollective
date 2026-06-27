from uuid import UUID

from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.repositories.plot_repository import plot_repository
from app.repositories.device_repository import device_repository

from app.schemas.device import DeviceCreate
from app.schemas.device import DeviceUpdate


class DeviceService:

    def create(
        self,
        db: Session,
        device_data: DeviceCreate,
        plot_id: UUID,
        user_id: UUID
    ):

        plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)

        if not plot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plot not found"
            )

        return device_repository.create(db, device_data, plot_id)

    def get_by_plot(
        self,
        db: Session,
        plot_id: UUID,
        user_id: UUID
    ):

        plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)

        if not plot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plot not found"
            )

        device = device_repository.get_by_plot(db, plot_id, user_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        return device

    def get_by_id(
        self,
        db: Session,
        device_id: UUID,
        user_id: UUID
    ):

        device = device_repository.get_by_id_and_user(db, device_id, user_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        return device

    def update(
        self,
        db: Session,
        device_id: UUID,
        device_data: DeviceUpdate,
        user_id: UUID
    ):

        device = device_repository.get_by_id_and_user(db, device_id, user_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        return device_repository.update(db, device, device_data)

    def delete(
        self,
        db: Session,
        device_id: UUID,
        plot_id: UUID,
        user_id: UUID
    ):

        plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)

        if not plot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plot not found"
            )

        device = device_repository.get_by_id_and_user(db, device_id, user_id)

        if not device or device.plot_id != plot_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        device_repository.delete(db, device)


device_service = DeviceService()
