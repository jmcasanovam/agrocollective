# Fase 8: Predicción ML (Random Forest)

## Objetivo

Predecir para cada parcela los valores futuros esperados de:

- **`yield_kg_ha`**: rendimiento de cosecha (kg/ha)
- **`water_efficiency`**: eficiencia hídrica (kg/mm×ha)

Las predicciones permiten detectar brechas entre lo esperado y lo observado (alimenta la Fase 9), y ofrecer al agricultor una referencia de rendimiento potencial.

---

## Algoritmo

### 1. Modelo global por target

Se entrena **un Random Forest por variable objetivo**, usando como muestras de entrenamiento únicamente las parcelas que tienen ese target con valor no nulo.

Esto evita el *data leakage* de usar el propio target como predictor y permite aprovechar el conocimiento colectivo de todas las parcelas del sistema.

### 2. Features de entrada

| Target | Features de entrada |
|---|---|
| `yield_kg_ha` | `avg_soil_humidity`, `avg_air_temp`, `avg_soil_temp`, `avg_air_humidity`, `irrigation_frequency`, `avg_irrigation_mm`, `total_water_mm` |
| `water_efficiency` | todas las anteriores + `yield_kg_ha` |

Los valores `None` se imputan a `0` (mismo criterio que Fase 4).

### 3. Normalización

Las features se normalizan con `StandardScaler` antes de entrenar y predecir, para evitar que features con escalas muy diferentes dominen el modelo.

### 4. Umbral de entrenamiento mínimo

Si hay menos de `ML_MIN_SAMPLES` parcelas con el target disponible, no se entrena el modelo y todas las predicciones de ese target quedan a `None`.

### 5. Evaluación del modelo

| Condición | Método de evaluación |
|---|---|
| `n_train ≥ 2 × ML_MIN_SAMPLES` | OOB score (Out-Of-Bag, sin partición adicional) |
| `n_train < 2 × ML_MIN_SAMPLES` | Leave-One-Out cross-validation |

El R² resultante se almacena en `model_r2` para trazabilidad.

### 6. Predicción universal

Una vez entrenado, el modelo predice para **todas** las parcelas del pipeline, incluyendo las que no tenían el target (por no tener cosecha/riego registrado aún). Esto se aprovecha en la Fase 9 para generar recomendaciones incluso en parcelas nuevas.

---

## Persistencia

Los resultados se guardan en `plot_ml_predictions` (idempotente: DELETE por `run_date` + INSERT).

### Esquema de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK auto-generado |
| `plot_id` | UUID | FK → `plots.id` |
| `run_date` | Date | Fecha de ejecución del pipeline |
| `cluster_id` | Integer | Cluster K-Means de la parcela |
| `target` | String(40) | `"yield_kg_ha"` o `"water_efficiency"` |
| `predicted_value` | Float | Valor predicho (NULL si no se pudo entrenar) |
| `model_r2` | Float | R² del modelo en la ejecución |
| `n_training_samples` | Integer | Parcelas usadas en el entrenamiento |

---

## Configuración (`.env`)

```dotenv
# Mínimo de parcelas con target no nulo para entrenar el modelo
ML_MIN_SAMPLES=10
# Número de árboles del Random Forest
ML_N_ESTIMATORS=100
```

---

## Estructura de archivos

```
app/
  services/
    ml/
      __init__.py
      prediction_service.py     ← PredictionService + MlPredictionResult dataclass
  repositories/
    ml_prediction_repository.py ← save_results(), get_by_plot_and_date()
  models/
    plot_ml_prediction.py       ← ORM PlotMlPrediction
  workers/
    clustering_worker.py        ← llama a prediction_service.run() en Fase 8

alembic/versions/
  j7e8f9a0b1c2_add_plot_ml_predictions_table.py
```

---

## Limitaciones (MVP)

- El modelo no tiene memoria entre ejecuciones: se reentrena cada noche desde cero. Esto garantiza que los datos más recientes siempre estén incluidos, a costa de no aprovechar modelos incrementales.
- Con menos de `ML_MIN_SAMPLES` parcelas en producción, la predicción queda desactivada. Es el escenario esperable en MVP; se activará conforme el sistema crezca.
- Random Forest no extrapola bien fuera del rango de entrenamiento. Si una parcela tiene valores de sensores muy atípicos respecto a las demás, la predicción puede ser poco fiable.

---

## Salida del pipeline (ejemplo)

```
INFO [Fase 8] Iniciando predicción ML (Random Forest)...
INFO [Fase 8] Target 'yield_kg_ha': solo 1 muestras con valor (mínimo 10): predicción omitida.
INFO [Fase 8] Target 'water_efficiency': solo 1 muestras con valor (mínimo 10): predicción omitida.
INFO [Fase 8] 0 predicciones con valor de 2 totales.
```

*(Con más parcelas en producción)*:

```
INFO [Fase 8] Target 'yield_kg_ha' | n_train=15 | R²=0.742 | method=OOB
INFO [Fase 8] Target 'water_efficiency' | n_train=12 | R²=0.681 | method=LOO
INFO [Fase 8] 30 predicciones con valor de 30 totales.
```
