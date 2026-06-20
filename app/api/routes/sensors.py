from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.sensor import SensorCreate
from app.schemas.sensor import SensorUpdate
from app.schemas.sensor import SensorResponse

from app.services.sensors.sensor_service import sensor_service


router = APIRouter(
    prefix="/plots/{plot_id}/sensors",
    tags=["Sensors"]
)


@router.post(
    "",
    response_model=SensorResponse
)
def create_sensor(
    plot_id: UUID,
    sensor_data: SensorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return sensor_service.create(
        db,
        sensor_data,
        plot_id,
        current_user.id
    )


@router.get(
    "",
    response_model=list[SensorResponse]
)
def get_sensors(
    plot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return sensor_service.get_all(
        db,
        plot_id,
        current_user.id
    )


@router.put(
    "/{sensor_id}",
    response_model=SensorResponse
)
def update_sensor(
    plot_id: UUID,
    sensor_id: UUID,
    sensor_data: SensorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return sensor_service.update(
        db,
        sensor_id,
        sensor_data,
        current_user.id
    )


@router.delete(
    "/{sensor_id}"
)
def delete_sensor(
    plot_id: UUID,
    sensor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sensor_service.delete(
        db,
        sensor_id,
        plot_id,
        current_user.id
    )

    return {
        "message": "Sensor deleted"
    }

@router.get(
    "/{sensor_id}",
    response_model=SensorResponse
)
def get_sensor(
    plot_id: UUID,
    sensor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return sensor_service.get_by_id(
        db,
        sensor_id,
        current_user.id
    )