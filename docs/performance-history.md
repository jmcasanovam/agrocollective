# Fase 10: Actualización del Historial de Rendimiento

## Objetivo

Cerrar cada ejecución del pipeline guardando una **instantánea completa del estado de cada parcela** en la tabla `plot_performance_history`. Esto permite:

- Analizar tendencias temporales por parcela (evolución semana a semana)
- Alimentar dashboards con datos históricos sin recalcular en tiempo real
- Proveer al modelo ML (Fase 8) un conjunto de entrenamiento que crece con cada ejecución
- Auditar el comportamiento del pipeline en el pasado

---

## Qué consolida

Cada registro agrega en un único lugar los resultados de las fases anteriores:

| Campo | Fuente |
|---|---|
| `cluster_id` | Fase 4: K-Means |
| `avg_soil_humidity`, `avg_air_temp`, `avg_soil_temp`, `avg_air_humidity` | Fase 3: Agregación InfluxDB |
| `irrigation_frequency`, `avg_irrigation_mm`, `total_water_mm` | Fase 3: Agregación PostgreSQL |
| `yield_kg_ha`, `water_efficiency` | Fase 3: Cosecha + cálculo de eficiencia |
| `is_anomaly`, `lof_score` | Fase 5: LOF |
| `predicted_yield`, `predicted_efficiency` | Fase 8: Random Forest |
| `n_recommendations`, `n_high_priority` | Fase 9: Recomendaciones |

---

## Persistencia

Tabla `plot_performance_history`, **un registro por (plot_id, run_date)**. Idempotente: DELETE por `run_date` + INSERT.

Hay una restricción UNIQUE sobre `(plot_id, run_date)` para garantizar integridad incluso ante ejecuciones paralelas accidentales.

### Esquema de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK auto-generado |
| `plot_id` | UUID | FK → `plots.id` |
| `run_date` | Date | Fecha de ejecución del pipeline |
| `cluster_id` | Integer | Cluster K-Means asignado |
| `avg_soil_humidity` | Float | Media humedad suelo (%) |
| `avg_air_temp` | Float | Media temperatura aire (°C) |
| `avg_soil_temp` | Float | Media temperatura suelo (°C) |
| `avg_air_humidity` | Float | Media humedad aire (%) |
| `irrigation_frequency` | Integer | Número de riegos en la ventana |
| `avg_irrigation_mm` | Float | Volumen medio por riego (mm) |
| `total_water_mm` | Float | Agua total aplicada (mm) |
| `yield_kg_ha` | Float | Rendimiento cosecha (kg/ha) |
| `water_efficiency` | Float | Eficiencia hídrica (kg/mm·ha) |
| `is_anomaly` | Boolean | Parcela anómala según LOF |
| `lof_score` | Float | Score LOF |
| `predicted_yield` | Float | Rendimiento predicho por ML |
| `predicted_efficiency` | Float | Eficiencia predicha por ML |
| `n_recommendations` | Integer | Total de recomendaciones generadas |
| `n_high_priority` | Integer | Recomendaciones de alta prioridad |

---

## Estructura de archivos

```
app/
  services/
    history/
      __init__.py
      performance_history_service.py   ← PerformanceHistoryService + PerformanceSnapshot
  repositories/
    performance_history_repository.py  ← save_snapshots(), get_history_for_plot()
  models/
    plot_performance_history.py        ← ORM PlotPerformanceHistory
  workers/
    clustering_worker.py               ← última fase del pipeline

alembic/versions/
  l9a0b1c2d3e4_add_plot_performance_history_table.py
```

---

## Salida del pipeline completo (ejemplo MVP con 1 parcela)

```
=== Inicio pipeline clustering | 2026-06-30T17:18:29Z ===
[Fase 3] Parcelas a procesar: 1
[Fase 3][1/1] Parcela 3af2e32d... | hum=45.0 air=22.5 riego=0 total_mm=None yield=None eff=None
[Fase 4] Iniciando K-Means sobre 1 parcelas...
K-Means: solo 1 parcela(s), asignando cluster único.
[Fase 5] 0 anomalías detectadas de 1 parcelas.
[Fase 6] Sin parcelas anómalas con features identificadas.
[Fase 7] Menos de 2 parcelas, sin análogas que calcular.
[Fase 8] Target 'yield_kg_ha': solo 0 muestras (mínimo 10), predicción omitida.
[Fase 8] Target 'water_efficiency': solo 0 muestras (mínimo 10), predicción omitida.
[Fase 9] 0 recomendaciones generadas para 1 parcelas.
[Fase 10] 1 instantáneas de rendimiento registradas para run_date=2026-06-30.
=== Pipeline completado | Fases 3-10 | 1 parcelas | k=1 | 0 anomalías | 0 causas | 0 predicciones | 0 recomendaciones | 0.1s ===
```

Los ceros reflejan el MVP con una sola parcela. Conforme el sistema crezca:
- K-Means formará clusters reales con ≥ 2 parcelas
- LOF detectará anomalías comparando entre parcelas del mismo cluster
- El modelo ML se activará con ≥ `ML_MIN_SAMPLES` parcelas con cosecha registrada
- Las recomendaciones se generarán combinando los hallazgos de todas las fases
