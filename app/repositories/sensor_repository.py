from uuid import UUID

from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.schemas.sensor import SensorCreate


class SensorRepository:


    def create(
        self,
        db: Session,
        sensor_data: SensorCreate,
        plot_id: UUID
    ) -> Sensor:

        sensor = Sensor(
            plot_id=plot_id,
            esp32_id=sensor_data.esp32_id,
            sensor_type=sensor_data.sensor_type,
            depth_cm=sensor_data.depth_cm
        )

        db.add(sensor)
        db.commit()
        db.refresh(sensor)

        return sensor


    def get_by_id(
        self,
        db: Session,
        sensor_id: UUID
    ) -> Sensor | None:

        return (
            db.query(Sensor)
            .filter(
                Sensor.id == sensor_id
            )
            .first()
        )


    def get_by_esp32_id(
        self,
        db: Session,
        esp32_id: str
    ) -> Sensor | None:

        return (
            db.query(Sensor)
            .filter(
                Sensor.esp32_id == esp32_id
            )
            .first()
        )


    def get_all_by_plot(
        self,
        db: Session,
        plot_id: UUID
    ) -> list[Sensor]:

        return (
            db.query(Sensor)
            .filter(
                Sensor.plot_id == plot_id
            )
            .all()
        )


sensor_repository = SensorRepository()