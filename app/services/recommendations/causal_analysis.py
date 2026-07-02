"""
Fase 6: Análisis causal inteligente para parcelas anómalas.

Para cada feature anómala detectada en la Fase 5, calcula la correlación de Pearson
entre su serie temporal (InfluxDB) y las variables candidatas a ser causa:
  - Volumen de riego semanal (PostgreSQL → irrigation_records)
  - Otras lecturas de sensores (InfluxDB)

La variable con mayor correlación absoluta se identifica como causa probable
y se genera una explicación textual.

Parámetros .env:
  CAUSAL_MIN_PERIODS    = 4   (mínimo de semanas necesarias para calcular correlación)
  CAUSAL_MIN_CORR       = 0.6 (correlación mínima para considerar relación causal)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.influx import Measurements, get_influx_client, get_query_api
from app.models.irrigation_record import IrrigationRecord
from app.services.anomalies.lof_service import AnomalyResult

logger = logging.getLogger(__name__)

# Mapeo feature → explicación cuando correlación es positiva / negativa
_EXPLANATIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("soil_humidity",  "irrigation_mm"):     ("exceso de volumen de riego",          "déficit de riego"),
    ("soil_humidity",  "air_humidity"):      ("alta humedad ambiental",               "baja humedad ambiental"),
    ("soil_humidity",  "air_temp"):          ("bajas temperaturas (menor evaporación)", "altas temperaturas (mayor evaporación)"),
    ("total_water_mm", "soil_humidity"):     ("alta retención de humedad en el suelo", "baja retención de humedad"),
    ("avg_air_temp",   "irrigation_mm"):     ("exceso de riego afecta la temperatura del suelo", "déficit de riego"),
    ("water_efficiency","irrigation_mm"):   ("exceso de agua reduce la eficiencia",   "déficit de agua limita la producción"),
    ("water_efficiency","soil_humidity"):   ("humedad excesiva reduce la eficiencia", "humedad insuficiente"),
}


@dataclass
class CausalResult:
    plot_id: UUID
    hash_plot: str
    run_date: date
    cluster_id: int
    anomalous_feature: str
    causal_feature: str | None = None
    correlation: float | None = None
    explanation: str | None = None


class CausalAnalysisService:

    def run(
        self,
        anomaly_results: list[AnomalyResult],
        db: Session,
        window_days: int | None = None,
    ) -> list[CausalResult]:
        """
        Analiza causas para todas las parcelas anómalas.

        Args:
            anomaly_results: resultados de la Fase 5.
            db: sesión PostgreSQL activa.
            window_days: ventana de análisis. None → usa AGGREGATION_WINDOW_DAYS.

        Returns:
            Lista de CausalResult (una por feature anómala de cada parcela anómala).
        """
        anomalous = [r for r in anomaly_results if r.is_anomaly and r.anomalous_features]
        if not anomalous:
            logger.info("[Fase 6] Sin parcelas anómalas con features identificadas.")
            return []

        days = window_days if window_days is not None else settings.AGGREGATION_WINDOW_DAYS
        since = datetime.now(timezone.utc) - timedelta(days=days)
        all_results: list[CausalResult] = []

        for anomaly in anomalous:
            for feature in anomaly.anomalous_features:
                result = self._analyze_feature(anomaly, feature, db, since)
                all_results.append(result)
                logger.info(
                    "[Fase 6] Parcela %s... | feature=%s → causa=%s (r=%.2f) | %s",
                    str(anomaly.plot_id)[:8],
                    feature,
                    result.causal_feature or "—",
                    result.correlation or 0,
                    result.explanation or "sin correlación suficiente",
                )

        return all_results

    # -------------------------------------------------------------------------
    # Análisis por feature
    # -------------------------------------------------------------------------

    def _analyze_feature(
        self,
        anomaly: AnomalyResult,
        feature: str,
        db: Session,
        since: datetime,
    ) -> CausalResult:
        result = CausalResult(
            plot_id=anomaly.plot_id,
            hash_plot=anomaly.hash_plot,
            run_date=anomaly.run_date,
            cluster_id=anomaly.cluster_id,
            anomalous_feature=feature,
        )

        # Serie temporal de la feature anómala (semanal, InfluxDB)
        target_series = self._get_sensor_weekly(anomaly.hash_plot, feature, since)
        if len(target_series) < settings.CAUSAL_MIN_PERIODS:
            logger.debug("Parcela %s...: pocos datos para '%s' (%d semanas).",
                         str(anomaly.plot_id)[:8], feature, len(target_series))
            return result

        # Candidatos causales: irrigación (PG) + otros sensores (InfluxDB)
        candidates: dict[str, dict[date, float]] = {}

        irrigation = self._get_irrigation_weekly(db, anomaly.plot_id, since)
        if irrigation:
            candidates["irrigation_mm"] = irrigation

        for sensor_field in ("soil_humidity", "air_temp", "soil_temp", "relative_humidity"):
            if sensor_field == feature:
                continue
            series = self._get_sensor_weekly(anomaly.hash_plot, sensor_field, since)
            if series:
                candidates[sensor_field] = series

        if not candidates:
            return result

        # Calcular correlación con cada candidato y quedarse con el máximo absoluto
        best_feature, best_corr = self._best_correlation(target_series, candidates)

        if best_feature and abs(best_corr) >= settings.CAUSAL_MIN_CORR:
            result.causal_feature = best_feature
            result.correlation = round(best_corr, 4)
            result.explanation = self._build_explanation(feature, best_feature, best_corr)

        return result

    # -------------------------------------------------------------------------
    # Correlación de Pearson
    # -------------------------------------------------------------------------

    @staticmethod
    def _best_correlation(
        target: dict[date, float],
        candidates: dict[str, dict[date, float]],
    ) -> tuple[str | None, float]:
        """Devuelve (feature_name, pearson_r) con mayor |r| sobre semanas comunes."""
        best_name: str | None = None
        best_r: float = 0.0

        for name, series in candidates.items():
            common_weeks = sorted(set(target) & set(series))
            if len(common_weeks) < settings.CAUSAL_MIN_PERIODS:
                continue
            y = np.array([target[w] for w in common_weeks])
            x = np.array([series[w] for w in common_weeks])
            if np.std(x) == 0 or np.std(y) == 0:
                continue
            r = float(np.corrcoef(x, y)[0, 1])
            if abs(r) > abs(best_r):
                best_r = r
                best_name = name

        return best_name, best_r

    # -------------------------------------------------------------------------
    # InfluxDB: serie semanal de un campo sensor
    # -------------------------------------------------------------------------

    def _get_sensor_weekly(
        self, hash_plot: str, field: str, since: datetime
    ) -> dict[date, float]:
        """Devuelve {week_start: avg_value} desde InfluxDB para el hash_plot."""
        # Mapear nombre interno → campo InfluxDB
        field_map = {
            "soil_humidity":  "soil_humidity",
            "air_temp":       "air_temp",
            "soil_temp":      "soil_temp",
            "air_humidity":   "relative_humidity",
            "relative_humidity": "relative_humidity",
        }
        influx_field = field_map.get(field, field)
        since_rfc = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        flux = f"""
            from(bucket: "{settings.INFLUXDB_BUCKET_MEASUREMENTS}")
              |> range(start: {since_rfc})
              |> filter(fn: (r) => r._measurement == "{Measurements.SENSORS}")
              |> filter(fn: (r) => r.hash_plot == "{hash_plot}")
              |> filter(fn: (r) => r._field == "{influx_field}")
              |> aggregateWindow(every: 1w, fn: mean, createEmpty: false)
              |> yield(name: "weekly")
        """
        result: dict[date, float] = {}
        try:
            client = get_influx_client()
            try:
                tables = get_query_api(client).query(flux, org=settings.INFLUXDB_ORG)
            finally:
                client.close()
            for table in tables:
                for record in table.records:
                    week = record.get_time().date()
                    result[week] = float(record.get_value())
        except Exception as exc:
            logger.error("[Fase 6] Error InfluxDB hash=%s field=%s: %s", hash_plot[:8], influx_field, exc)
        return result

    # -------------------------------------------------------------------------
    # PostgreSQL: riego semanal
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_irrigation_weekly(
        db: Session, plot_id: UUID, since: datetime
    ) -> dict[date, float]:
        records: list[IrrigationRecord] = (
            db.query(IrrigationRecord)
            .filter(
                IrrigationRecord.plot_id == plot_id,
                IrrigationRecord.week_start >= since.date(),
            )
            .all()
        )
        return {r.week_start: float(r.irrigation_mm) for r in records}

    # -------------------------------------------------------------------------
    # Explicación textual
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_explanation(anomalous: str, causal: str, r: float) -> str:
        key = (anomalous, causal)
        if key in _EXPLANATIONS:
            positive_text, negative_text = _EXPLANATIONS[key]
            cause_text = positive_text if r > 0 else negative_text
        else:
            direction = "positiva" if r > 0 else "negativa"
            cause_text = f"correlación {direction} con {causal}"

        return (
            f"La correlación histórica entre '{anomalous}' y '{causal}' es {r:+.2f}. "
            f"Causa probable: {cause_text}."
        )


causal_analysis_service = CausalAnalysisService()
