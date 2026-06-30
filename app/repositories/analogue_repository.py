from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_analogue import PlotAnalogue
from app.services.clustering.analogue_service import AnalogueResult


class AnalogueRepository:

    def save_results(self, db: Session, results: list[AnalogueResult]) -> None:
        """Reemplaza las análogas del run_date (idempotente)."""
        if not results:
            return

        run_date = results[0].run_date
        db.query(PlotAnalogue).filter(PlotAnalogue.run_date == run_date).delete()

        for r in results:
            db.add(PlotAnalogue(
                plot_id=r.plot_id,
                analogue_plot_id=r.analogue_plot_id,
                run_date=r.run_date,
                rank=r.rank,
                distance=r.distance,
                same_cluster=r.same_cluster,
            ))

        db.commit()

    def get_analogues_for_plot(
        self, db: Session, plot_id, run_date: date
    ) -> list[PlotAnalogue]:
        return (
            db.query(PlotAnalogue)
            .filter(
                PlotAnalogue.plot_id == plot_id,
                PlotAnalogue.run_date == run_date,
            )
            .order_by(PlotAnalogue.rank)
            .all()
        )


analogue_repository = AnalogueRepository()
