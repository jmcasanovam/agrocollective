from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.plot import Plot
from app.models.farm import Farm
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceRepository:

    def create(
        self,
        db: Session,
        device_data: DeviceCreate,
        plot_id: UUID
    ) -> Device:

        device = Device(
            plot_id=plot_id,
            esp32_id=device_data.esp32_id
        )

        db.add(device)
        db.commit()
        db.refresh(device)

        return device

    def get_by_id(
        self,
        db: Session,
        device_id: UUID
    ) -> Device | None:

        return (
            db.query(Device)
            .filter(
                Device.id == device_id,
                Device.is_active == True
            )
            .first()
        )

    def get_by_id_and_user(
        self,
        db: Session,
        device_id: UUID,
        user_id: UUID
    ) -> Device | None:

        return (
            db.query(Device)
            .join(Plot)
            .join(Farm)
            .filter(
                Device.id == device_id,
                Device.is_active == True,
                Plot.is_active == True,
                Farm.is_active == True,
                Farm.user_id == user_id
            )
            .first()
        )

    def get_by_esp32_id(
        self,
        db: Session,
        esp32_id: str
    ) -> Device | None:

        return (
            db.query(Device)
            .filter(
                Device.esp32_id == esp32_id,
                Device.is_active == True
            )
            .first()
        )

    def get_by_plot(
        self,
        db: Session,
        plot_id: UUID,
        user_id: UUID
    ) -> Device | None:

        return (
            db.query(Device)
            .join(Plot)
            .join(Farm)
            .filter(
                Device.plot_id == plot_id,
                Device.is_active == True,
                Plot.is_active == True,
                Farm.is_active == True,
                Farm.user_id == user_id
            )
            .first()
        )

    def update(
        self,
        db: Session,
        device: Device,
        device_data: DeviceUpdate
    ) -> Device:

        if device_data.status is not None:
            device.status = device_data.status

        if device_data.battery_mv is not None:
            device.battery_mv = device_data.battery_mv

        db.commit()
        db.refresh(device)

        return device

    def delete(
        self,
        db: Session,
        device: Device
    ) -> None:

        device.is_active = False
        db.commit()


device_repository = DeviceRepository()
