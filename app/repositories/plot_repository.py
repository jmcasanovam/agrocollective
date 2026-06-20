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
            crop_type=plot_data.crop_type,
            soil_type=plot_data.soil_type,
            area_ha=plot_data.area_ha,
            depth_cm=plot_data.depth_cm,
            province=plot_data.province,
            name=plot_data.name
        )

        db.add(plot)
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
                Plot.is_active.is_(True),
                Farm.is_active.is_(True)
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

        if plot_data.crop_type is not None:
            plot.crop_type = plot_data.crop_type

        if plot_data.soil_type is not None:
            plot.soil_type = plot_data.soil_type

        if plot_data.area_ha is not None:
            plot.area_ha = plot_data.area_ha

        if plot_data.depth_cm is not None:
            plot.depth_cm = plot_data.depth_cm

        if plot_data.province is not None:
            plot.province = plot_data.province

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