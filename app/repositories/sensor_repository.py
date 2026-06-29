from uuid import UUID

from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.models.device import Device
from app.schemas.sensor import SensorCreate, SensorUpdate


class SensorRepository:

    def create(self, db: Session, data: SensorCreate) -> Sensor:
        sensor = Sensor(
            name=data.name,
            sensor_type=data.sensor_type,
            unit=data.unit,
            description=data.description,
        )
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        return sensor

    def get_by_id(self, db: Session, sensor_id: UUID) -> Sensor | None:
        return db.query(Sensor).filter(Sensor.id == sensor_id).first()

    def get_all(self, db: Session) -> list[Sensor]:
        return db.query(Sensor).all()

    def get_active(self, db: Session) -> list[Sensor]:
        return db.query(Sensor).filter(Sensor.is_active == True).all()

    def update(self, db: Session, sensor: Sensor, data: SensorUpdate) -> Sensor:
        if data.name is not None:
            sensor.name = data.name
        if data.sensor_type is not None:
            sensor.sensor_type = data.sensor_type
        if data.unit is not None:
            sensor.unit = data.unit
        if data.description is not None:
            sensor.description = data.description
        if data.is_active is not None:
            sensor.is_active = data.is_active
        db.commit()
        db.refresh(sensor)
        return sensor

    def delete(self, db: Session, sensor: Sensor) -> None:
        db.delete(sensor)
        db.commit()

    def assign_to_device(self, db: Session, device: Device, sensor_ids: list[UUID]) -> Device:
        sensors = db.query(Sensor).filter(Sensor.id.in_(sensor_ids)).all()
        device.sensors = sensors
        db.commit()
        db.refresh(device)
        return device

    def add_sensor_to_device(self, db: Session, device: Device, sensor: Sensor) -> Device:
        if sensor not in device.sensors:
            device.sensors.append(sensor)
            db.commit()
            db.refresh(device)
        return device

    def remove_sensor_from_device(self, db: Session, device: Device, sensor: Sensor) -> Device:
        if sensor in device.sensors:
            device.sensors.remove(sensor)
            db.commit()
            db.refresh(device)
        return device


sensor_repository = SensorRepository()
