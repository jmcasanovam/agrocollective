# Fase 6: Análisis Causal Inteligente

## Objetivo

Para cada parcela detectada como anómala en la Fase 5, identificar **por qué** se produce la anomalía. El servicio calcula la correlación de Pearson entre la serie temporal de la variable anómala y las variables candidatas a ser su causa (volumen de riego, otras lecturas de sensores), y genera una explicación legible por el usuario.

---

## Cuándo se ejecuta

La Fase 6 forma parte del pipeline nocturno (`clustering_worker.py`) y se ejecuta justo después de la Fase 5 (LOF). Solo actúa sobre parcelas marcadas como anómalas **con features identificadas**.

---

## Algoritmo

### 1. Selección de parcelas anómalas

Se filtran los `AnomalyResult` de la Fase 5 donde `is_anomaly=True` y `anomalous_features` no está vacío.

### 2. Serie temporal de la feature anómala

Para cada feature anómala, se consulta InfluxDB con una agregación semanal (`aggregateWindow(every: 1w, fn: mean)`):

```flux
from(bucket: "agrocollective")
  |> range(start: <since>)
  |> filter(fn: (r) => r._measurement == "sensor_readings")
  |> filter(fn: (r) => r.hash_plot == "<hash>")
  |> filter(fn: (r) => r._field == "<feature>")
  |> aggregateWindow(every: 1w, fn: mean, createEmpty: false)
```

Resultado: `dict[date, float]` indexado por semana.

### 3. Variables candidatas

Se construyen series semanales para cada candidato:

| Candidato | Fuente |
|---|---|
| `irrigation_mm` | PostgreSQL → `irrigation_records.irrigation_mm` filtrado por `week_start ≥ since` |
| `soil_humidity` | InfluxDB |
| `air_temp` | InfluxDB |
| `soil_temp` | InfluxDB |
| `relative_humidity` | InfluxDB |

Se excluye de los candidatos la propia feature anómala.

### 4. Correlación de Pearson

Para cada candidato se calculan las semanas comunes con la serie objetivo y se aplica:

```python
r = np.corrcoef(x_candidate, y_target)[0, 1]
```

**Condiciones para calcular:**
- Al menos `CAUSAL_MIN_PERIODS` semanas comunes (default: 4)
- Desviación estándar > 0 en ambas series

Se selecciona el candidato con mayor `|r|`.

### 5. Umbral de causalidad

Si `|r| ≥ CAUSAL_MIN_CORR` (default: 0.6), se registra la relación causal. Si no, el campo `causal_feature` queda a `None`.

### 6. Explicación textual

Se genera automáticamente según la dirección de la correlación:

| Feature anómala | Causa | r > 0 | r < 0 |
|---|---|---|---|
| `soil_humidity` | `irrigation_mm` | exceso de volumen de riego | déficit de riego |
| `soil_humidity` | `air_humidity` | alta humedad ambiental | baja humedad ambiental |
| `soil_humidity` | `air_temp` | bajas temperaturas (menor evaporación) | altas temperaturas (mayor evaporación) |
| `water_efficiency` | `irrigation_mm` | exceso de agua reduce la eficiencia | déficit de agua limita la producción |

Para combinaciones no contempladas, la explicación es genérica: *"correlación positiva/negativa con `{causal}`"*.

---

## Persistencia

Los resultados se guardan en la tabla `plot_causal_results` (idempotente: DELETE por `run_date` + INSERT).

### Esquema de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK auto-generado |
| `plot_id` | UUID | FK a `plots.id` |
| `run_date` | Date | Fecha de ejecución del pipeline |
| `cluster_id` | Integer | Cluster al que pertenece la parcela |
| `anomalous_feature` | String(60) | Variable que presenta la anomalía |
| `causal_feature` | String(60) | Variable causa (NULL si no se identifica) |
| `correlation` | Float | Pearson r entre ambas series |
| `explanation` | Text | Explicación textual generada |

---

## Configuración (`.env`)

```dotenv
# Mínimo de semanas con datos para calcular correlación causal
CAUSAL_MIN_PERIODS=4
# Correlación de Pearson mínima (valor absoluto) para considerar relación causal
CAUSAL_MIN_CORR=0.6
```

---

## Estructura de archivos

```
app/
  services/
    recommendations/
      causal_analysis.py      ← CausalAnalysisService + CausalResult dataclass
  repositories/
    causal_repository.py      ← save_results(), get_by_date()
  models/
    plot_causal_result.py     ← ORM PlotCausalResult
  workers/
    clustering_worker.py      ← llama a causal_analysis_service.run() en Fase 6

alembic/versions/
  h5c6d7e8f9a0_add_plot_causal_results_table.py
```

---

## Limitaciones (MVP)

- La correlación no implica causalidad; es un indicador estadístico.
- Con pocos datos (< `CAUSAL_MIN_PERIODS` semanas) no se puede determinar la causa y se deja `None`.
- El análisis se basa en la ventana `AGGREGATION_WINDOW_DAYS`, que debe ser suficientemente larga para capturar variabilidad semanal.

---

## Salida del pipeline (ejemplo)

```
INFO [Fase 6] Iniciando análisis causal...
INFO [Fase 6] Parcela a1b2c3d4... | feature=soil_humidity → causa=irrigation_mm (r=+0.87) | La correlación histórica entre 'soil_humidity' e 'irrigation_mm' es +0.87. Causa probable: exceso de volumen de riego.
INFO [Fase 6] Parcela e5f6g7h8... | feature=air_temp → causa=None (r=0.00) | sin correlación suficiente
INFO [Fase 6] 1 causas identificadas de 2 features anómalas.
```
