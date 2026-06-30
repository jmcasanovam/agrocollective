from datetime import date

from sqlalchemy.orm import Session

from app.models.plot_ml_prediction import PlotMlPrediction
from app.services.ml.prediction_service import MlPredictionResult


class MlPredictionRepository:

    def save_results(self, db: Session, results: list[MlPredictionResult]) -> None:
        """Reemplaza las predicciones del run_date (idempotente)."""
        if not results:
            return

        run_date = results[0].run_date
        db.query(PlotMlPrediction).filter(PlotMlPrediction.run_date == run_date).delete()

        for r in results:
            db.add(PlotMlPrediction(
                plot_id=r.plot_id,
                run_date=r.run_date,
                cluster_id=r.cluster_id,
                target=r.target,
                predicted_value=r.predicted_value,
                model_r2=r.model_r2,
                n_training_samples=r.n_training_samples,
            ))

        db.commit()

    def get_by_plot_and_date(
        self, db: Session, plot_id, run_date: date
    ) -> list[PlotMlPrediction]:
        return (
            db.query(PlotMlPrediction)
            .filter(
                PlotMlPrediction.plot_id == plot_id,
                PlotMlPrediction.run_date == run_date,
            )
            .all()
        )


ml_prediction_repository = MlPredictionRepository()
