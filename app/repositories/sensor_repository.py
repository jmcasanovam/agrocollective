from uuid import UUID

from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.models.plot import Plot
from app.models.farm import Farm
from app.schemas.sensor import SensorCreate, SensorUpdate


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
                Sensor.id == sensor_id,
                Sensor.is_active == True
            )
            .first()
        )


    def get_by_id_and_user(
        self,
        db: Session,
        sensor_id: UUID,
        user_id: UUID
    ) -> Sensor | None:

        return (
            db.query(Sensor)
            .join(Plot)
            .join(Farm)
            .filter(
                Sensor.id == sensor_id,
                Farm.user_id == user_id,
                Sensor.is_active == True,
                Plot.is_active == True,
                Farm.is_active == True
            )
            .first()
        )


    def get_by_esp32_id(
        self,
        db: Session,
        esp32_id: str
    ) -> list[Sensor]:

        return (
            db.query(Sensor)
            .filter(
                Sensor.esp32_id == esp32_id,
                Sensor.is_active == True
            )
            .all()
        )


    def get_all_by_plot(
        self,
        db: Session,
        plot_id: UUID,
        user_id: UUID
    ) -> list[Sensor]:

        return (
            db.query(Sensor)
            .join(Plot)
            .join(Farm)
            .filter(
                Sensor.plot_id == plot_id,
                Farm.user_id == user_id,
                Sensor.is_active == True,
                Plot.is_active == True,
                Farm.is_active == True
            )
            .all()
        )


    def update(
        self,
        db: Session,
        sensor: Sensor,
        sensor_data: SensorUpdate
    ):

        if sensor_data.sensor_type is not None:
            sensor.sensor_type = sensor_data.sensor_type

        if sensor_data.depth_cm is not None:
            sensor.depth_cm = sensor_data.depth_cm

        if sensor_data.status is not None:
            sensor.status = sensor_data.status

        db.commit()
        db.refresh(sensor)

        return sensor


    def delete(
        self,
        db: Session,
        sensor: Sensor
    ):

        sensor.is_active = False

        db.commit()


sensor_repository = SensorRepository()