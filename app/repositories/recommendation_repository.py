from datetime import date

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.models.plot_recommendation import PlotRecommendation
from app.services.recommendations.recommendation_service import RecommendationResult

# order_by(priority) por si solo ordena alfabetico (high, low, medium).
# Este case fuerza el orden real de severidad: high -> medium -> low.
_PRIORITY_ORDER = case(
    (PlotRecommendation.priority == "high", 0),
    (PlotRecommendation.priority == "medium", 1),
    (PlotRecommendation.priority == "low", 2),
    else_=3,
)


class RecommendationRepository:

    def save_results(self, db: Session, results: list[RecommendationResult]) -> None:
        """Reemplaza las recomendaciones del run_date (idempotente)."""
        if not results:
            return

        run_date = results[0].run_date
        db.query(PlotRecommendation).filter(PlotRecommendation.run_date == run_date).delete()

        for r in results:
            db.add(PlotRecommendation(
                plot_id=r.plot_id,
                run_date=r.run_date,
                category=r.category,
                priority=r.priority,
                title=r.title,
                body=r.body,
            ))

        db.commit()

    def get_by_plot_and_date(
        self, db: Session, plot_id, run_date: date
    ) -> list[PlotRecommendation]:
        return (
            db.query(PlotRecommendation)
            .filter(
                PlotRecommendation.plot_id == plot_id,
                PlotRecommendation.run_date == run_date,
            )
            .order_by(_PRIORITY_ORDER)
            .all()
        )

    def get_latest_by_plot(self, db: Session, plot_id) -> list[PlotRecommendation]:
        """Devuelve las recomendaciones del último run_date disponible."""
        latest_row = (
            db.query(PlotRecommendation.run_date)
            .filter(PlotRecommendation.plot_id == plot_id)
            .order_by(PlotRecommendation.run_date.desc())
            .first()
        )
        if not latest_row:
            return []
        return self.get_by_plot_and_date(db, plot_id, latest_row[0])


recommendation_repository = RecommendationRepository()
