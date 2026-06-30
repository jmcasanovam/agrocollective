# Simulación paso a paso — 10 parcelas, 4 horas, medición cada 15 min

Este documento sigue el recorrido completo de los datos desde el primer mensaje MQTT hasta las recomendaciones finales, usando un escenario concreto como ejemplo.

---

## Escenario

| Parámetro | Valor |
|---|---|
| Parcelas | 10 (IDs P1–P10, pertenecientes a 3 agricultores distintos) |
| Período de lectura | 08:00 – 12:00 UTC |
| Intervalo | 15 minutos |
| Total de mensajes MQTT | 10 parcelas × 17 intervalos = **170 mensajes** |
| Pipeline nocturno | 02:00 UTC del día siguiente |

---

## Parte 1 — Captura de datos en tiempo real (Fases 1 y 2)

### 08:00:00 — Primer mensaje

El sensor de la parcela P1 publica en Mosquitto:

```
Topic: devices/AGRO-P1-001/readings

{
  "device_id": "AGRO-P1-001",
  "timestamp": "2026-06-30T08:00:00Z",
  "battery_mv": 3820,
  "measures": {
    "soil_humidity": 42.3,
    "air_temp": 18.1,
    "soil_temp": 16.4,
    "air_humidity": 71.2
  }
}
```

**Lo que hace el backend en ese instante:**

1. El hilo `mqtt-consumer` recibe el mensaje en `_on_message()`.
2. Valida el JSON con Pydantic (`DeviceReadingPayload`). Si falla → log de error, descarta.
3. Busca el dispositivo `AGRO-P1-001` en PostgreSQL → encuentra la parcela P1 (`hash_plot = sha256(plot.id)`).
4. **Actualiza PostgreSQL** → `devices.last_seen_at = 08:00:00`, `devices.battery_mv = 3820`.
5. **Escribe en InfluxDB** → measurement `sensor_readings`, tag `hash_plot = abc123...`, fields: `soil_humidity=42.3`, `air_temp=18.1`, `soil_temp=16.4`, `relative_humidity=71.2`.

### 08:15:00 — Segundo intervalo (10 mensajes en ~1 s)

Los 10 sensores publican casi simultáneamente. El broker los encola; el consumer los procesa uno a uno en el hilo MQTT.

| Parcela | soil_humidity | air_temp | soil_temp | air_humidity |
|---|---|---|---|---|
| P1 | 41.8 | 18.4 | 16.5 | 70.9 |
| P2 | 55.1 | 19.2 | 17.1 | 68.4 |
| P3 | 38.2 | 17.8 | 15.9 | 74.1 |
| P4 | 61.4 | 20.1 | 18.3 | 65.2 |
| P5 | 44.7 | 18.9 | 16.8 | 72.0 |
| P6 | 39.5 | 17.5 | 15.7 | 75.3 |
| P7 | 52.3 | 19.8 | 17.6 | 66.8 |
| P8 | 47.1 | 18.6 | 16.9 | 71.5 |
| P9 | 85.2 ⚠ | 19.0 | 17.2 | 69.1 |  ← P9 acaba de recibir riego
| P10 | 43.6 | 18.2 | 16.3 | 72.8 |

La parcela P9 tiene `soil_humidity = 85.2`, muy por encima del resto. En este momento el sistema **no detecta nada inusual** — simplemente almacena el dato. La detección ocurrirá en el pipeline nocturno.

### 12:00:00 — Última lectura

Tras 4 horas y 17 ciclos, InfluxDB acumula **170 puntos** (17 × 10 parcelas).

**Estado de InfluxDB al cierre:**
- Serie temporal continua por `hash_plot` con granularidad de 15 min
- ~17 valores por campo por parcela

**Estado de PostgreSQL al cierre:**
- Tabla `devices`: `last_seen_at` y `battery_mv` actualizados para los 10 dispositivos

---

## Parte 2 — Pipeline nocturno (02:00 UTC del día siguiente)

El scheduler lanza `clustering_worker.run_pipeline()`.

---

### Fase 3 — Variables agregadas (ventana = 30 días)

Para cada parcela se calculan medias sobre la ventana completa. En este ejemplo, solo hay 4 horas de datos, pero el sistema funciona igual:

| Parcela | avg_soil_hum | avg_air_temp | irrig_freq | total_mm | yield_kg_ha | water_eff |
|---|---|---|---|---|---|---|
| P1 | 41.9 | 18.3 | 2 | 60.0 | 4 200 | 0.70 |
| P2 | 54.8 | 19.1 | 3 | 90.0 | 3 800 | 0.42 |
| P3 | 38.5 | 17.9 | 1 | 30.0 | 3 500 | 1.17 |
| P4 | 61.2 | 20.0 | 4 | 120.0 | 4 100 | 0.34 |
| P5 | 44.9 | 18.8 | 2 | 60.0 | 4 300 | 0.72 |
| P6 | 39.8 | 17.6 | 1 | 30.0 | 3 600 | 1.20 |
| P7 | 52.1 | 19.7 | 3 | 90.0 | 3 900 | 0.43 |
| P8 | 47.3 | 18.5 | 2 | 60.0 | 4 150 | 0.69 |
| P9 | 72.4 ⚠ | 19.1 | 5 | 150.0 | 3 200 | 0.21 |  ← mucho riego, baja eficiencia
| P10 | 43.4 | 18.1 | 2 | 60.0 | 4 250 | 0.71 |

P9 destaca claramente: máxima humedad, máxima frecuencia de riego, mínima eficiencia hídrica.

---

### Fase 4 — Clustering K-Means (k=3)

El algoritmo normaliza las 9 features y agrupa las parcelas por similitud:

| Cluster | Parcelas | Perfil |
|---|---|---|
| **0** | P1, P5, P8, P10 | Riego moderado, eficiencia media-alta (~0.70) |
| **1** | P3, P6 | Riego escaso, alta eficiencia (>1.15), temperatura baja |
| **2** | P2, P4, P7, P9 | Riego intensivo, eficiencia baja (<0.45) |

Cada parcela queda asociada a su cluster con una distancia al centroide. P9 pertenece al cluster 2 pero está **lejos del centroide** de su grupo: incluso dentro del grupo de riego intensivo, ella riega más.

---

### Fase 5 — Detección de anomalías LOF

LOF se ejecuta dentro de cada cluster.

**Cluster 2 (P2, P4, P7, P9):**

| Parcela | LOF score | ¿Anómala? | Features anómalas |
|---|---|---|---|
| P2 | 1.12 | No | — |
| P4 | 1.08 | No | — |
| P7 | 1.19 | No | — |
| P9 | **2.34** | **Sí** | `avg_soil_humidity`, `total_water_mm` |

P9 es la única anómala del sistema esta noche.

---

### Fase 6 — Análisis causal

Para P9, feature anómala: `avg_soil_humidity`.

Se consulta la serie semanal de `soil_humidity` en InfluxDB y la serie de `irrigation_mm` en PostgreSQL, y se calcula la correlación de Pearson:

```
r(soil_humidity, irrigation_mm) = +0.91  ✓  (≥ CAUSAL_MIN_CORR = 0.6)
r(soil_humidity, air_temp)       = -0.12
r(soil_humidity, air_humidity)   = +0.34
```

**Causa identificada:** `irrigation_mm` con r = +0.91

**Explicación generada:**
> "La correlación histórica entre 'avg_soil_humidity' e 'irrigation_mm' es +0.91. Causa probable: exceso de volumen de riego."

---

### Fase 7 — Parcelas análogas

Para cada parcela se buscan las 5 más cercanas en el espacio normalizado. Para P9 (anómala):

| Rank | Parcela análoga | Distancia | Mismo cluster |
|---|---|---|---|
| 1 | P4 | 0.48 | Sí |
| 2 | P2 | 0.61 | Sí |
| 3 | P7 | 0.72 | Sí |
| 4 | P1 | 1.85 | No |
| 5 | P8 | 1.92 | No |

P1 y P8 son análogas fuera del cluster: son parcelas con valores similares en temperatura y humedad del aire, pero con riego mucho más eficiente. Son buenas referencias prácticas para P9.

---

### Fase 8 — Predicción ML (Random Forest)

Con 10 parcelas y cosechas registradas para todas, hay suficientes muestras para entrenar:

```
Target: yield_kg_ha
  n_train = 10  →  se usa Leave-One-Out (LOO)
  R² = 0.74
  Predicción P9 → 4 100 kg/ha  (observado: 3 200 kg/ha, brecha: 22%)

Target: water_efficiency
  n_train = 10
  R² = 0.81
  Predicción P9 → 0.58  (observado: 0.21, brecha: 64%)
```

El modelo ha aprendido de P3 y P6 (cluster 1) que con sus condiciones climáticas es posible conseguir alta eficiencia. Le aplica esa "esperanza" a P9.

---

### Fase 9 — Recomendaciones para P9

Se generan 3 recomendaciones:

**[anomaly / high]**
> *"Anomalía en humedad del suelo: posible volumen de riego inadecuado/a"*
> Tu parcela presenta un valor anómalo de humedad del suelo (LOF score: 2.34). La correlación histórica entre 'avg_soil_humidity' e 'irrigation_mm' es +0.91. Causa probable: exceso de volumen de riego. Revisa los registros de volumen de riego de las últimas semanas.

**[prediction / high]**
> *"Tu eficiencia hídrica está un 64% por debajo del potencial estimado"*
> El modelo estima que parcelas con tus condiciones alcanzan una eficiencia hídrica de 0.58, pero tu valor actual es 0.21. Compara tus prácticas con las parcelas análogas de tu grupo.

**[prediction / medium]**
> *"Tu rendimiento (kg/ha) está un 22% por debajo del potencial estimado"*
> El modelo estima 4 100 kg/ha; tu valor actual es 3 200 kg/ha.

---

### Fase 10 — Historial de rendimiento

Se guarda en `plot_performance_history` un registro para cada una de las 10 parcelas con `run_date = 2026-07-01`:

```
P9 → cluster_id=2, avg_soil_humidity=72.4, is_anomaly=TRUE,
     lof_score=2.34, predicted_yield=4100, predicted_efficiency=0.58,
     n_recommendations=3, n_high_priority=2
```

Este registro alimentará el entrenamiento de la próxima ejecución del modelo ML.

---

## Resumen visual

```
08:00 ──────────────── 12:00        02:00 (día siguiente)
│ 170 mensajes MQTT                  │ Pipeline nocturno
│ → InfluxDB (170 puntos)            │
│ → PostgreSQL (last_seen, battery)  ├─ F3: variables agregadas
│                                    ├─ F4: K-Means → 3 clusters
│                                    ├─ F5: LOF → P9 anómala
│                                    ├─ F6: causa → sobrerriego (r=0.91)
│                                    ├─ F7: análogas → P4, P2, P7, P1, P8
│                                    ├─ F8: ML → pred_yield=4100
│                                    ├─ F9: 3 recomendaciones para P9
│                                    └─ F10: snapshot guardado
```
