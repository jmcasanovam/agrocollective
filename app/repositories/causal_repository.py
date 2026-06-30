from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_causal_result import PlotCausalResult
from app.services.recommendations.causal_analysis import CausalResult


class CausalRepository:

    def save_results(self, db: Session, results: list[CausalResult]) -> None:
        """Reemplaza los resultados causales del run_date (idempotente)."""
        if not results:
            return

        run_date = results[0].run_date
        db.query(PlotCausalResult).filter(PlotCausalResult.run_date == run_date).delete()

        for r in results:
            db.add(PlotCausalResult(
                plot_id=r.plot_id,
                run_date=r.run_date,
                cluster_id=r.cluster_id,
                anomalous_feature=r.anomalous_feature,
                causal_feature=r.causal_feature,
                correlation=r.correlation,
                explanation=r.explanation,
            ))

        db.commit()

    def get_by_date(self, db: Session, run_date: date) -> list[PlotCausalResult]:
        return (
            db.query(PlotCausalResult)
            .filter(PlotCausalResult.run_date == run_date)
            .all()
        )


causal_repository = CausalRepository()
