# Fase 5: Detección de anomalías con Local Outlier Factor (LOF)

## Descripción

Tras asignar cada parcela a un cluster (Fase 4), el sistema aplica LOF **dentro de cada cluster** para identificar parcelas cuyo comportamiento difiere significativamente del resto. Una parcela anómala puede indicar exceso de riego, humedad inusualmente alta, baja eficiencia productiva u otros problemas agronómicos.

LOF mide la densidad local de cada punto respecto a sus vecinos: cuanto mayor es el score, más aislado está el punto dentro del cluster y más anómalo es su comportamiento.

---

## Parámetros configurables

```env
LOF_N_NEIGHBORS=5    # vecinos para calcular densidad local (se reduce si el cluster es pequeño)
LOF_THRESHOLD=1.5    # score LOF a partir del cual se considera anomalía
```

---

## Manejo de casos borde

| Situación | Comportamiento |
|---|---|
| Cluster con 1 parcela | `lof_score=1.0`, `is_anomaly=False` (sin comparación posible) |
| Cluster con N < `LOF_N_NEIGHBORS` | `n_neighbors` se reduce a `N-1` automáticamente |
| Score ≤ `LOF_THRESHOLD` | Parcela normal |
| Score > `LOF_THRESHOLD` | Parcela anómala → se identifican features desviadas |

---

## Identificación de features anómalas

Cuando una parcela es anómala, el sistema detecta qué variables concretas se desvían más de `1.5σ` respecto al centroide del cluster:

```
anomalous_features = "soil_humidity,total_water_mm"
```

Esto alimentará el análisis causal de la Fase 6.

---

## Resultado almacenado en PostgreSQL (`plot_anomalies`)

| Columna | Descripción |
|---|---|
| `plot_id` | Referencia a la parcela |
| `run_date` | Fecha de ejecución |
| `cluster_id` | Cluster al que pertenece |
| `lof_score` | Score LOF (1.0 = normal, > `LOF_THRESHOLD` = anómala) |
| `is_anomaly` | `true` si supera el umbral |
| `anomalous_features` | Features desviadas, separadas por coma |

Las filas del mismo `run_date` se reemplazan en cada ejecución (idempotente).

---

## Flujo dentro del pipeline

```
clustering_worker.run_pipeline()
  │
  ├─ [Fase 3] aggregation_service → list[PlotAggregates]
  ├─ [Fase 4] kmeans_service      → ClusteringResult
  │
  └─ [Fase 5] lof_service.run(aggregates, clustering_result)
        │
        ├─ Agrupar parcelas por cluster_id
        │
        └─ Por cada cluster:
              ├─ Construir matriz de features (None → 0)
              ├─ Ajustar n_neighbors = min(LOF_N_NEIGHBORS, n-1)
              ├─ LocalOutlierFactor.fit_predict(X)
              ├─ Convertir negative_outlier_factor_ a score positivo
              ├─ is_anomaly = score > LOF_THRESHOLD
              └─ Si anómala → detectar features con desviación > 1.5σ
        │
        └─ anomaly_repository.save_results(db, results)
              └─ DELETE + INSERT en plot_anomalies
```

---

## Ficheros

| Fichero | Responsabilidad |
|---|---|
| `app/services/anomalies/lof_service.py` | Algoritmo LOF por cluster, detección de features |
| `app/repositories/anomaly_repository.py` | Persistencia en `plot_anomalies` |
| `app/models/plot_anomaly.py` | Modelo ORM de la tabla |

Migración: `g4b5c6d7e8f9_add_plot_anomalies_table`

---

## Ejecución manual

```bash
docker exec -it agro_backend bash
python -m app.workers.clustering_worker
```

### Salida con anomalías detectadas (ejemplo con varias parcelas)

```
[Fase 5] Iniciando LOF sobre 5 parcelas...
  ⚠ Anomalía | Parcela a1b2c3d4... | cluster=0 | lof=2.341 | features=['total_water_mm', 'soil_humidity']
[Fase 5] Cluster 0 | 4 parcelas | 1 anomalías detectadas
[Fase 5] Cluster 1 | 1 parcelas | 0 anomalías detectadas
[Fase 5] 1 anomalías detectadas de 5 parcelas.
=== Pipeline completado | Fases 3-5 | 5 parcelas | k=2 | 1 anomalías | 1.3s ===
```

### Salida con 1 parcela (caso borde actual)

```
[Fase 5] Cluster 0 | 1 parcelas | 0 anomalías detectadas
[Fase 5] 0 anomalías detectadas de 1 parcelas.
lof_score=1.0, is_anomaly=False
```

---

## Verificar resultado en PostgreSQL

```sql
-- Todas las anomalías del último run
SELECT
    pa.run_date,
    pa.cluster_id,
    pa.lof_score,
    pa.anomalous_features,
    p.name AS parcela
FROM plot_anomalies pa
JOIN plots p ON p.id = pa.plot_id
WHERE pa.is_anomaly = true
ORDER BY pa.lof_score DESC;

-- Resumen por run_date
SELECT run_date, COUNT(*) FILTER (WHERE is_anomaly) AS anomalias, COUNT(*) AS total
FROM plot_anomalies
GROUP BY run_date
ORDER BY run_date DESC;
```
