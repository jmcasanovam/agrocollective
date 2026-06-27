from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User

from app.schemas.device import DeviceCreate
from app.schemas.device import DeviceUpdate
from app.schemas.device import DeviceResponse

from app.services.devices.device_service import device_service


router = APIRouter(
    prefix="/plots/{plot_id}/devices",
    tags=["Devices"]
)


@router.post(
    "",
    response_model=DeviceResponse
)
def create_device(
    plot_id: UUID,
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return device_service.create(
        db,
        device_data,
        plot_id,
        current_user.id
    )


@router.get(
    "",
    response_model=DeviceResponse
)
def get_device(
    plot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return device_service.get_by_plot(
        db,
        plot_id,
        current_user.id
    )


@router.put(
    "/{device_id}",
    response_model=DeviceResponse
)
def update_device(
    plot_id: UUID,
    device_id: UUID,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return device_service.update(
        db,
        device_id,
        device_data,
        current_user.id
    )


@router.delete(
    "/{device_id}"
)
def delete_device(
    plot_id: UUID,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    device_service.delete(
        db,
        device_id,
        plot_id,
        current_user.id
    )

    return {"message": "Device deleted"}


@router.get(
    "/{device_id}",
    response_model=DeviceResponse
)
def get_device_by_id(
    plot_id: UUID,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return device_service.get_by_id(
        db,
        device_id,
        current_user.id
    )
