import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.plot import Plot
from app.models.farm import Farm

from app.schemas.plot import PlotCreate, PlotUpdate


class PlotRepository:

    def create(
        self,
        db: Session,
        plot_data: PlotCreate,
        farm_id: UUID
    ) -> Plot:

        plot = Plot(
            farm_id=farm_id,
            crop_id=plot_data.crop_id,
            soil_id=plot_data.soil_id,
            region_id=plot_data.region_id,
            area_ha=plot_data.area_ha,
            depth_cm=plot_data.depth_cm,
            name=plot_data.name
        )

        db.add(plot)
        db.commit()
        db.refresh(plot)

        plot.hash_plot = hashlib.sha256(str(plot.id).encode()).hexdigest()
        db.commit()
        db.refresh(plot)

        return plot

    def get_all_by_farm(
        self,
        db: Session,
        farm_id: UUID
    ) -> list[Plot]:

        return (
            db.query(Plot)
            .filter(
                Plot.farm_id == farm_id,
                Plot.is_active.is_(True)
            )
            .all()
        )

    def get_by_id(
        self,
        db: Session,
        plot_id: UUID
    ) -> Plot | None:

        return (
            db.query(Plot)
            .filter(
                Plot.id == plot_id,
                Plot.is_active.is_(True)
            )
            .first()
        )

    def get_by_id_and_user(
        self,
        db: Session,
        plot_id: UUID,
        user_id: UUID
    ) -> Plot | None:

        return (
            db.query(Plot)
            .join(Farm)
            .filter(
                Plot.id == plot_id,
                Plot.is_active.is_(True),
                Farm.user_id == user_id,
                Farm.is_active.is_(True)
            )
            .first()
        )

    def update(
        self,
        db: Session,
        plot: Plot,
        plot_data: PlotUpdate
    ) -> Plot:

        if plot_data.crop_id is not None:
            plot.crop_id = plot_data.crop_id

        if plot_data.soil_id is not None:
            plot.soil_id = plot_data.soil_id

        if plot_data.region_id is not None:
            plot.region_id = plot_data.region_id

        if plot_data.area_ha is not None:
            plot.area_ha = plot_data.area_ha

        if plot_data.depth_cm is not None:
            plot.depth_cm = plot_data.depth_cm

        if plot_data.name is not None:
            plot.name = plot_data.name

        db.commit()
        db.refresh(plot)

        return plot

    def delete(
        self,
        db: Session,
        plot: Plot
    ) -> None:

        plot.is_active = False
        db.commit()


plot_repository = PlotRepository()
