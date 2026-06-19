from uuid import UUID

from sqlalchemy.orm import Session

from app.models.plot import Plot

from app.schemas.plot import PlotCreate


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
                Plot.farm_id == farm_id
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
                Plot.id == plot_id
            )
            .first()
        )


plot_repository = PlotRepository()