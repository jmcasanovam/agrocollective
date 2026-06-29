from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.plot import Plot
from app.models.farm import Farm
from app.models.user import User
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceRepository:

    def create(self, db: Session, device_data: DeviceCreate, plot_id: UUID) -> Device:
        device = Device(plot_id=plot_id, code=device_data.code)
        db.add(device)
        db.commit()
        db.refresh(device)
        return device

    def get_by_id(self, db: Session, device_id: UUID) -> Device | None:
        return db.query(Device).filter(Device.id == device_id).first()

    def get_by_id_and_user(self, db: Session, device_id: UUID, user_id: UUID) -> Device | None:
        return (
            db.query(Device)
            .join(Plot, Plot.id == Device.plot_id)
            .join(Farm, Farm.id == Plot.farm_id)
            .join(User, User.id == Farm.user_id)
            .filter(Device.id == device_id, Farm.user_id == user_id, User.is_active == True)
            .first()
        )

    def get_by_code(self, db: Session, code: str) -> Device | None:
        return db.query(Device).filter(Device.code == code).first()

    def get_by_plot(self, db: Session, plot_id: UUID, user_id: UUID) -> Device | None:
        return (
            db.query(Device)
            .join(Plot, Plot.id == Device.plot_id)
            .join(Farm, Farm.id == Plot.farm_id)
            .join(User, User.id == Farm.user_id)
            .filter(Device.plot_id == plot_id, Farm.user_id == user_id, User.is_active == True)
            .first()
        )

    def update(self, db: Session, device: Device, device_data: DeviceUpdate) -> Device:
        if device_data.code is not None:
            device.code = device_data.code
        if device_data.is_active is not None:
            device.is_active = device_data.is_active
        db.commit()
        db.refresh(device)
        return device

    def delete(self, db: Session, device: Device) -> None:
        db.delete(device)
        db.commit()


device_repository = DeviceRepository()
