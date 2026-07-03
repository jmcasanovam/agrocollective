from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.sensor import DeviceSensorAssign
from app.schemas.sensor import SensorCreate
from app.schemas.sensor import SensorResponse
from app.schemas.sensor import SensorUpdate
from app.schemas.sensor_reading import SensorReadingPoint

from app.repositories.sensor_repository import sensor_repository
from app.repositories.device_repository import device_repository
from app.repositories.plot_repository import plot_repository

from app.database.influx import Measurements, get_influx_client, get_query_api
from app.core.config import settings


router = APIRouter(tags=["Sensors"])

# Campo InfluxDB -> nombre expuesto en la API (coincide con la lista de la Fase 1: MQTT)
_SENSOR_FIELD_MAP = {
    "soil_humidity": "soil_humidity",
    "soil_temp": "soil_temp",
    "air_temp": "air_temp",
    "relative_humidity": "air_humidity",
}


def _get_plot_or_404(db: Session, plot_id: UUID, user_id: UUID):
    plot = plot_repository.get_by_id_and_user(db, plot_id, user_id)
    if not plot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcela no encontrada o sin acceso.")
    return plot


def _query_sensor_points(hash_plot: str, since_flux_duration: str) -> list[SensorReadingPoint]:
    fields_filter = " or ".join(f'r._field == "{field}"' for field in _SENSOR_FIELD_MAP)
    flux = f"""
        from(bucket: "{settings.INFLUXDB_BUCKET_MEASUREMENTS}")
          |> range(start: {since_flux_duration})
          |> filter(fn: (r) => r._measurement == "{Measurements.SENSORS}")
          |> filter(fn: (r) => r.hash_plot == "{hash_plot}")
          |> filter(fn: (r) => {fields_filter})
          |> sort(columns: ["_time"])
    """
    points: list[SensorReadingPoint] = []
    client = get_influx_client()
    try:
        tables = get_query_api(client).query(flux, org=settings.INFLUXDB_ORG)
        for table in tables:
            for record in table.records:
                sensor = _SENSOR_FIELD_MAP.get(record.get_field())
                if sensor is None:
                    continue
                points.append(
                    SensorReadingPoint(
                        sensor=sensor,
                        value=record.get_value(),
                        recorded_at=record.get_time(),
                    )
                )
    finally:
        client.close()
    return points


# ── Platform sensor catalog ────────────────────────────────────────────────────

@router.get(
    "/sensors",
    response_model=list[SensorResponse]
)
def list_sensors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return sensor_repository.get_all(db)


@router.post(
    "/sensors",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED
)
def create_sensor(
    data: SensorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return sensor_repository.create(db, data)


@router.put(
    "/sensors/{sensor_id}",
    response_model=SensorResponse
)
def update_sensor(
    sensor_id: UUID,
    data: SensorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sensor = sensor_repository.get_by_id(db, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor_repository.update(db, sensor, data)


@router.delete("/sensors/{sensor_id}")
def delete_sensor(
    sensor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sensor = sensor_repository.get_by_id(db, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    sensor_repository.delete(db, sensor)
    return {"message": "Sensor deleted"}


# ── Device sensor assignment ───────────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/devices/{device_id}/sensors",
    response_model=list[SensorResponse]
)
def get_device_sensors(
    plot_id: UUID,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = device_repository.get_by_id_and_user(db, device_id, current_user.id)
    if not device or device.plot_id != plot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device.sensors


@router.post(
    "/plots/{plot_id}/devices/{device_id}/sensors",
    response_model=list[SensorResponse]
)
def assign_sensors_to_device(
    plot_id: UUID,
    device_id: UUID,
    data: DeviceSensorAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = device_repository.get_by_id_and_user(db, device_id, current_user.id)
    if not device or device.plot_id != plot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    device = sensor_repository.assign_to_device(db, device, data.sensor_ids)
    return device.sensors


@router.delete(
    "/plots/{plot_id}/devices/{device_id}/sensors/{sensor_id}"
)
def remove_sensor_from_device(
    plot_id: UUID,
    device_id: UUID,
    sensor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = device_repository.get_by_id_and_user(db, device_id, current_user.id)
    if not device or device.plot_id != plot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    sensor = sensor_repository.get_by_id(db, sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    sensor_repository.remove_sensor_from_device(db, device, sensor)
    return {"message": "Sensor removed from device"}


# ── Plot sensor readings (InfluxDB) ────────────────────────────────────────────

@router.get(
    "/plots/{plot_id}/sensors/latest",
    response_model=list[SensorReadingPoint],
    summary="Última lectura de cada sensor de la parcela",
)
def get_plot_sensors_latest(
    plot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plot = _get_plot_or_404(db, plot_id, current_user.id)
    if not plot.hash_plot:
        return []

    points = _query_sensor_points(plot.hash_plot, "-30d")

    latest_by_sensor: dict[str, SensorReadingPoint] = {}
    for point in points:
        current = latest_by_sensor.get(point.sensor)
        if current is None or point.recorded_at > current.recorded_at:
            latest_by_sensor[point.sensor] = point

    return list(latest_by_sensor.values())


@router.get(
    "/plots/{plot_id}/sensors/history",
    response_model=list[SensorReadingPoint],
    summary="Histórico de lecturas de sensores de la parcela",
)
def get_plot_sensors_history(
    plot_id: UUID,
    hours: int = Query(default=24, ge=1, le=168, description="Ventana de horas hacia atrás"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plot = _get_plot_or_404(db, plot_id, current_user.id)
    if not plot.hash_plot:
        return []

    return _query_sensor_points(plot.hash_plot, f"-{hours}h")
