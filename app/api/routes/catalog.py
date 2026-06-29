from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.crop import Crop
from app.models.soil import Soil
from app.models.region import Region

from app.schemas.crop import CropCreate, CropUpdate, CropResponse
from app.schemas.soil import SoilCreate, SoilUpdate, SoilResponse
from app.schemas.region import RegionCreate, RegionUpdate, RegionResponse


router = APIRouter(tags=["Catalog"])


# ── Crops ──────────────────────────────────────────────────────────────────────

@router.get("/crops", response_model=list[CropResponse])
def list_crops(db: Session = Depends(get_db)):
    return db.query(Crop).all()


@router.post("/crops", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
def create_crop(
    data: CropCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crop = Crop(name=data.name, description=data.description)
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.put("/crops/{crop_id}", response_model=CropResponse)
def update_crop(
    crop_id: UUID,
    data: CropUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    if data.name is not None:
        crop.name = data.name
    if data.description is not None:
        crop.description = data.description
    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}")
def delete_crop(
    crop_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    db.delete(crop)
    db.commit()
    return {"message": "Crop deleted"}


# ── Soils ──────────────────────────────────────────────────────────────────────

@router.get("/soils", response_model=list[SoilResponse])
def list_soils(db: Session = Depends(get_db)):
    return db.query(Soil).all()


@router.post("/soils", response_model=SoilResponse, status_code=status.HTTP_201_CREATED)
def create_soil(
    data: SoilCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    soil = Soil(name=data.name, description=data.description)
    db.add(soil)
    db.commit()
    db.refresh(soil)
    return soil


@router.put("/soils/{soil_id}", response_model=SoilResponse)
def update_soil(
    soil_id: UUID,
    data: SoilUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    soil = db.query(Soil).filter(Soil.id == soil_id).first()
    if not soil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil not found")
    if data.name is not None:
        soil.name = data.name
    if data.description is not None:
        soil.description = data.description
    db.commit()
    db.refresh(soil)
    return soil


@router.delete("/soils/{soil_id}")
def delete_soil(
    soil_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    soil = db.query(Soil).filter(Soil.id == soil_id).first()
    if not soil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil not found")
    db.delete(soil)
    db.commit()
    return {"message": "Soil deleted"}


# ── Regions ────────────────────────────────────────────────────────────────────

@router.get("/regions", response_model=list[RegionResponse])
def list_regions(db: Session = Depends(get_db)):
    return db.query(Region).all()


@router.post("/regions", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
def create_region(
    data: RegionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    region = Region(
        code=data.code,
        name=data.name,
        latitude=data.latitude,
        longitude=data.longitude,
        siar_station_code=data.siar_station_code,
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@router.put("/regions/{region_id}", response_model=RegionResponse)
def update_region(
    region_id: UUID,
    data: RegionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
    if data.name is not None:
        region.name = data.name
    if data.latitude is not None:
        region.latitude = data.latitude
    if data.longitude is not None:
        region.longitude = data.longitude
    if data.siar_station_code is not None:
        region.siar_station_code = data.siar_station_code
    db.commit()
    db.refresh(region)
    return region


@router.delete("/regions/{region_id}")
def delete_region(
    region_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
    db.delete(region)
    db.commit()
    return {"message": "Region deleted"}
