from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.sensor import DeviceSensorAssign
from app.schemas.sensor import SensorCreate
from app.schemas.sensor import SensorResponse
from app.schemas.sensor import SensorUpdate

from app.repositories.sensor_repository import sensor_repository
from app.repositories.device_repository import device_repository


router = APIRouter(tags=["Sensors"])


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
