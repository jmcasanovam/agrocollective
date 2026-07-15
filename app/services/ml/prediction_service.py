"""
Fase 8: Predicción ML de rendimiento y eficiencia hídrica.

Estrategia (MVP):
  - Se entrena un modelo Random Forest global (sobre todas las parcelas)
    para cada variable objetivo: yield_kg_ha y water_efficiency.
  - Features de entrada: las 7 variables sensoriales y de riego que NO
    son la variable objetivo (no se usan yield/efficiency como features
    entre sí para evitar leakage).
  - Si hay menos de ML_MIN_SAMPLES parcelas con valor no nulo en el target,
    la predicción se omite (predicted_value = None).
  - La calidad del modelo se estima con R² en OOB (oob_score=True) cuando
    hay suficientes muestras, o con Leave-One-Out si n < 2·ML_MIN_SAMPLES.

Parámetros .env:
  ML_MIN_SAMPLES  = 10   (mínimo de muestras con target no nulo para entrenar)
  ML_N_ESTIMATORS = 100  (árboles del Random Forest)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.services.measurements.aggregation_service import PlotAggregates
from app.services.clustering.kmeans_service import ClusteringResult, FEATURE_COLUMNS

logger = logging.getLogger(__name__)

# Features usadas como entrada para predecir yield_kg_ha
YIELD_FEATURES = [
    "avg_soil_humidity",
    "avg_air_temp",
    "avg_soil_temp",
    "avg_air_humidity",
    "irrigation_frequency",
    "avg_irrigation_mm",
    "total_water_mm",
]

# Features usadas para predecir water_efficiency
EFFICIENCY_FEATURES = [
    "avg_soil_humidity",
    "avg_air_temp",
    "avg_soil_temp",
    "avg_air_humidity",
    "irrigation_frequency",
    "avg_irrigation_mm",
    "total_water_mm",
    "yield_kg_ha",
]

TARGETS = {
    "yield_kg_ha": YIELD_FEATURES,
    "water_efficiency": EFFICIENCY_FEATURES,
}


@dataclass
class MlPredictionResult:
    plot_id: UUID
    run_date: date
    cluster_id: int
    target: str
    predicted_value: float | None = None
    model_r2: float | None = None
    n_training_samples: int = 0


class PredictionService:

    def run(
        self,
        aggregates: list[PlotAggregates],
        clustering_result: ClusteringResult,
    ) -> list[MlPredictionResult]:
        """
        Genera predicciones ML para yield_kg_ha y water_efficiency.

        Entrena un Random Forest global por target y predice para todas las parcelas.

        Returns:
            Lista de MlPredictionResult (2 por parcela: yield + efficiency).
        """
        run_date = clustering_result.run_date
        cluster_map: dict[UUID, int] = {
            a.plot_id: a.cluster_id for a in clustering_result.assignments
        }

        all_results: list[MlPredictionResult] = []

        for target, feature_cols in TARGETS.items():
            predictions = self._train_and_predict(aggregates, target, feature_cols, run_date)
            for plot_id, pred in predictions.items():
                all_results.append(MlPredictionResult(
                    plot_id=plot_id,
                    run_date=run_date,
                    cluster_id=cluster_map.get(plot_id, -1),
                    target=target,
                    predicted_value=pred["predicted_value"],
                    model_r2=pred["model_r2"],
                    n_training_samples=pred["n_training_samples"],
                ))

        logger.info(
            "[Fase 8] %d predicciones generadas (%d parcelas × %d targets).",
            len(all_results), len(aggregates), len(TARGETS),
        )
        return all_results

    # -------------------------------------------------------------------------
    # Entrenamiento y predicción por target
    # -------------------------------------------------------------------------

    def _train_and_predict(
        self,
        aggregates: list[PlotAggregates],
        target: str,
        feature_cols: list[str],
        run_date: date,
    ) -> dict[UUID, dict]:
        """
        Entrena un Random Forest global y devuelve predicciones para cada parcela.

        Solo las parcelas con target no nulo participan en el entrenamiento.
        Todas las parcelas reciben una predicción (usando el modelo entrenado).
        """
        results: dict[UUID, dict] = {
            agg.plot_id: {"predicted_value": None, "model_r2": None, "n_training_samples": 0}
            for agg in aggregates
        }

        # Separar parcelas con target conocido (entrenamiento) de las que no
        train_indices = [
            i for i, agg in enumerate(aggregates)
            if getattr(agg, target) is not None
        ]
        n_train = len(train_indices)

        if n_train < settings.ML_MIN_SAMPLES:
            logger.info(
                "[Fase 8] Target '%s': solo %d muestras con valor (mínimo %d). Predicción omitida.",
                target, n_train, settings.ML_MIN_SAMPLES,
            )
            return results

        # Construir X e y de entrenamiento
        X_train = np.array([
            [float(getattr(aggregates[i], col) or 0) for col in feature_cols]
            for i in train_indices
        ], dtype=float)
        y_train = np.array([
            float(getattr(aggregates[i], target))
            for i in train_indices
        ], dtype=float)

        # X completa (todas las parcelas) para predecir
        X_all = np.array([
            [float(getattr(agg, col) or 0) for col in feature_cols]
            for agg in aggregates
        ], dtype=float)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_all_scaled = scaler.transform(X_all)

        # Usar OOB cuando hay suficientes muestras; LOO cuando son pocas
        use_oob = n_train >= 2 * settings.ML_MIN_SAMPLES
        rf = RandomForestRegressor(
            n_estimators=settings.ML_N_ESTIMATORS,
            oob_score=use_oob,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train_scaled, y_train)

        if use_oob:
            r2 = round(float(rf.oob_score_), 4)
        else:
            loo_scores = cross_val_score(rf, X_train_scaled, y_train, cv=LeaveOneOut(), scoring="r2")
            r2 = round(float(np.mean(loo_scores)), 4)

        logger.info(
            "[Fase 8] Target '%s' | n_train=%d | R²=%.3f | method=%s",
            target, n_train, r2, "OOB" if use_oob else "LOO",
        )

        # Predicción para todas las parcelas
        y_pred = rf.predict(X_all_scaled)

        for i, agg in enumerate(aggregates):
            results[agg.plot_id] = {
                "predicted_value": round(float(y_pred[i]), 6),
                "model_r2": r2,
                "n_training_samples": n_train,
            }

        return results


prediction_service = PredictionService()
