# Fase 4: Clustering K-Means de parcelas

## Descripción

Tras calcular las variables agregadas de cada parcela, el sistema ejecuta el algoritmo K-Means para agrupar las parcelas con comportamiento agronómico similar. Cada parcela recibe un `cluster_id` y su distancia al centroide del cluster.

---

## Variables de entrada

Las features provienen directamente del `PlotAggregates` calculado en la Fase 3:

| Feature | Descripción | Unidad |
|---|---|---|
| `avg_soil_humidity` | Humedad media del suelo | % |
| `avg_air_temp` | Temperatura media del aire | °C |
| `avg_soil_temp` | Temperatura media del suelo | °C |
| `avg_air_humidity` | Humedad relativa media del aire | % |
| `irrigation_frequency` | Número de riegos en la ventana | — |
| `avg_irrigation_mm` | Media de mm por riego | mm |
| `total_water_mm` | Total de mm aplicados | mm |
| `yield_kg_ha` | Producción de la última cosecha | kg/ha |
| `water_efficiency` | Eficiencia hídrica | kg/m³ |

Los valores `None` se tratan como `0` para el clustering. Las features se normalizan con `StandardScaler` antes de ejecutar K-Means.

---

## Parámetros configurables

```env
KMEANS_MAX_CLUSTERS=5    # k máximo; se reduce si hay menos parcelas que k
```

---

## Manejo de casos borde

| Situación | Comportamiento |
|---|---|
| 0 parcelas | Devuelve resultado vacío, no falla |
| 1 parcela | Asigna `cluster_id=0`, `distance=0.0` sin ejecutar K-Means |
| N < `KMEANS_MAX_CLUSTERS` | Reduce k a N automáticamente |
| N ≥ `KMEANS_MAX_CLUSTERS` | Ejecuta K-Means con k = `KMEANS_MAX_CLUSTERS` |

---

## Resultado almacenado en PostgreSQL (`plot_clusters`)

Por cada ejecución se inserta una fila por parcela. Las del mismo `run_date` se reemplazan (idempotente).

| Columna | Descripción |
|---|---|
| `plot_id` | Referencia a la parcela |
| `run_date` | Fecha de ejecución del clustering |
| `cluster_id` | Número de cluster asignado (0-indexed) |
| `distance_to_centroid` | Distancia euclidiana al centroide (espacio normalizado) |
| `cluster_size` | Número de parcelas en el mismo cluster |
| `cluster_avg_soil_humidity` | Humedad media del cluster |
| `cluster_avg_air_temp` | Temperatura media del cluster |
| `cluster_avg_irrigation_mm` | Riego medio del cluster |
| `cluster_avg_efficiency` | Eficiencia hídrica media del cluster |

---

## Flujo dentro del pipeline

```
clustering_worker.run_pipeline()
  │
  ├─ [Fase 3] aggregation_service.compute() × N parcelas
  │    → list[PlotAggregates]
  │
  └─ [Fase 4] kmeans_service.run(aggregates)
        ├─ Construir matriz de features (None → 0)
        ├─ Determinar k = min(KMEANS_MAX_CLUSTERS, N)
        ├─ Si k == 1 → cluster único sin K-Means
        ├─ Si k > 1  → StandardScaler + KMeans(k, random_state=42)
        ├─ Calcular distancias a centroides
        ├─ Calcular estadísticas por cluster
        └─ save_clustering_result(db, result)
              └─ DELETE + INSERT en plot_clusters
```

---

## Ficheros

| Fichero | Responsabilidad |
|---|---|
| `app/services/clustering/kmeans_service.py` | Algoritmo K-Means, normalización, estadísticas |
| `app/services/clustering/cluster_statistics.py` | Persistencia en `plot_clusters` |
| `app/models/plot_cluster.py` | Modelo ORM de la tabla |
| `app/workers/clustering_worker.py` | Orquestación Fases 3-4 (y siguientes) |

Migración: `f3a4b5c6d7e8_add_plot_clusters_table`

---

## Ejecución manual

```bash
docker exec -it agro_backend bash

# Ventana de .env (30 días por defecto)
python -m app.workers.clustering_worker

# Forzar ventana distinta
python -m app.workers.clustering_worker 7
```

### Salida esperada (con varias parcelas)

```
[Fase 3] Parcelas a procesar: 5
[Fase 3][1/5] Parcela a1b2c3d4... | hum=45.0 air=22.5 riego=4 total_mm=180.0 yield=4200.0 eff=2.3333
...
[Fase 4] Iniciando K-Means sobre 5 parcelas...
  Parcela a1b2c3d4... → cluster 0 (dist=0.4821, cluster_size=3)
  Parcela ff1122ab... → cluster 1 (dist=0.3104, cluster_size=2)
K-Means completado | k=2 | inertia=3.42 | parcelas=5
Clustering guardado | run_date=2026-06-29 | k=2 | parcelas=5
=== Pipeline completado | Fases 3-4 | 5 parcelas | k=2 | 1.2s ===
```

### Salida con 1 parcela (caso borde actual)

```
[Fase 4] Iniciando K-Means sobre 1 parcelas...
K-Means: solo 1 parcela(s) — asignando cluster único.
Clustering guardado | run_date=2026-06-29 | k=1 | parcelas=1
=== Pipeline completado | Fases 3-4 | 1 parcelas | k=1 | 0.1s ===
```

---

## Verificar resultado en PostgreSQL

```sql
SELECT
    pc.run_date,
    pc.cluster_id,
    pc.distance_to_centroid,
    pc.cluster_size,
    pc.cluster_avg_soil_humidity,
    pc.cluster_avg_air_temp,
    p.name AS parcela
FROM plot_clusters pc
JOIN plots p ON p.id = pc.plot_id
ORDER BY pc.run_date DESC, pc.cluster_id;
```
