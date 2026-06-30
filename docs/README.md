# AgroCollective — Documentación técnica

Documentación del pipeline de datos inteligente: desde la captura IoT hasta las recomendaciones agronómicas personalizadas.

---

## Índice

### Fase 1 — Captura MQTT en tiempo real

| Documento | Qué cubre |
|---|---|
| [mqtt-flow.md](mqtt-flow.md) | Los dispositivos ESP32 publican lecturas de sensores al broker Mosquitto bajo el topic `devices/{device_code}/readings`. El backend FastAPI consume estos mensajes en tiempo real mediante un hilo MQTT dedicado: valida el payload con Pydantic, identifica la parcela a través del `device_code` y dispara el almacenamiento. |

### Fase 2 — Ingesta y almacenamiento

| Documento | Qué cubre |
|---|---|
| [influxdb-ingestion.md](influxdb-ingestion.md) | Cada lectura validada se persiste en dos sistemas: las series temporales de sensores (`soil_humidity`, `air_temp`, `soil_temp`, `relative_humidity`) se escriben en InfluxDB usando el `hash_plot` como identificador anónimo; los metadatos operativos del dispositivo (`last_seen_at`, `battery_mv`) se actualizan en PostgreSQL. |

### Pipeline de análisis nocturno (Fases 3-10)

El pipeline se lanza cada noche a las `CLUSTERING_SCHEDULE_HOUR` UTC y procesa todas las parcelas activas de forma secuencial.

| Documento | Qué cubre |
|---|---|
| [aggregation.md](aggregation.md) | **Fase 3** — Comprime el histórico de cada parcela en un conjunto de variables representativas: medias de sensores (InfluxDB), frecuencia de riego, volumen total y eficiencia hídrica (PostgreSQL). Estas variables son la entrada del algoritmo. |
| [clustering-kmeans.md](clustering-kmeans.md) | **Fase 4** — K-Means agrupa las parcelas por similitud agronómica en clusters. Cada cluster tiene una media de referencia (benchmark) que se usa en las fases siguientes para detectar desviaciones. |
| [anomaly-detection-lof.md](anomaly-detection-lof.md) | **Fase 5** — LOF (Local Outlier Factor) detecta parcelas estadísticamente inusuales dentro de su cluster e identifica qué variables concretas son las responsables de la anomalía. |
| [causal-analysis.md](causal-analysis.md) | **Fase 6** — Para cada variable anómala, calcula la correlación de Pearson entre su serie temporal semanal y las variables candidatas (volumen de riego, otros sensores) para identificar la causa probable. |
| [analogue-search.md](analogue-search.md) | **Fase 7** — Calcula la distancia euclidiana entre todas las parcelas en el espacio de features normalizado y guarda las N más cercanas a cada una. Sirve como referencia de buenas prácticas. |
| [ml-prediction.md](ml-prediction.md) | **Fase 8** — Entrena un Random Forest global por variable objetivo (`yield_kg_ha` y `water_efficiency`) y predice el valor esperado para cada parcela. La brecha con el valor real alimenta las recomendaciones. |
| [recommendations.md](recommendations.md) | **Fase 9** — Sintetiza las salidas de todas las fases anteriores en recomendaciones accionables para cada parcela. Tres categorías: `anomaly` (causas identificadas), `prediction` (brecha con el potencial ML) y `benchmark` (diferencia con la media del cluster). |
| [performance-history.md](performance-history.md) | **Fase 10** — Al cierre del pipeline guarda en `plot_performance_history` una instantánea completa del estado de cada parcela: variables agregadas, cluster, anomalía, predicción ML y recuento de recomendaciones. |

### API REST — Resultados para el frontend

Los resultados del pipeline se exponen a través de endpoints autenticados bajo `/plots/{plot_id}/`:

| Endpoint | Devuelve |
|---|---|
| `GET /plots/{plot_id}/recommendations` | Recomendaciones agronómicas del último pipeline (o de un `run_date` concreto) |
| `GET /plots/{plot_id}/anomalies` | Historial de detección LOF con las features anómalas identificadas |
| `GET /plots/{plot_id}/analogues` | Parcelas más similares ordenadas por distancia |
| `GET /plots/{plot_id}/ml-predictions` | Predicciones Random Forest de rendimiento y eficiencia |
| `GET /plots/{plot_id}/performance-history` | Historial de instantáneas del pipeline (hasta 365 registros) |

Todos los endpoints verifican que la parcela pertenece al usuario autenticado. La documentación interactiva completa está disponible en `/docs`.

### Guías adicionales

| Documento | Qué cubre |
|---|---|
| [simulation-walkthrough.md](simulation-walkthrough.md) | Simulación paso a paso de 10 parcelas durante 4 horas: qué ocurre en cada capa del sistema desde el envío MQTT hasta las recomendaciones finales. |
| [requirements.md](requirements.md) | Requisitos funcionales y no funcionales del sistema. |
| [wokwi-deployment.md](wokwi-deployment.md) | Configuración y despliegue del firmware de sensores en Wokwi. |

---

## Flujo resumido

```
Sensor IoT (ESP32)
   │  JSON → topic: devices/{device_code}/readings
   ▼
Mosquitto broker  [Fase 1 — mqtt-flow.md]
   │
   ▼
FastAPI MQTT consumer (hilo dedicado)
   │  valida · busca parcela · persiste
   ▼
InfluxDB (series temporales)    PostgreSQL (riegos, cosechas, dispositivos)
           [Fase 2 — influxdb-ingestion.md]
   │                                  │
   └──────────────┬───────────────────┘
                  ▼  clustering_worker.py  (02:00 UTC)
    [F3]  Variables agregadas por parcela
    [F4]  Clustering K-Means  →  grupos + benchmarks
    [F5]  Detección de anomalías (LOF)
    [F6]  Análisis causal (correlación de Pearson)
    [F7]  Búsqueda de parcelas análogas
    [F8]  Predicción ML (Random Forest)
    [F9]  Generación de recomendaciones
    [F10] Historial de rendimiento
                  ▼
         PostgreSQL  →  API REST  →  Frontend
                         /plots/{id}/recommendations
                         /plots/{id}/anomalies
                         /plots/{id}/analogues
                         /plots/{id}/ml-predictions
                         /plots/{id}/performance-history
```
