# Fase 9 — Generación de Recomendaciones Inteligentes

## Objetivo

Sintetizar los resultados de las fases anteriores para producir **recomendaciones agronómicas accionables** para cada parcela, ordenadas por prioridad y clasificadas por categoría.

---

## Fuentes de conocimiento

| Fase | Qué aporta |
|---|---|
| Fase 4 — K-Means | Estadísticas medias del cluster (benchmark de referencia) |
| Fase 5 — LOF | Detección de anomalías y features afectadas |
| Fase 6 — Causal | Causa probable de cada anomalía (correlación de Pearson) |
| Fase 7 — Análogas | Parcelas similares con mejores resultados (referencia práctica) |
| Fase 8 — ML | Predicción de rendimiento y eficiencia hídrica esperados |

---

## Categorías de recomendación

### `anomaly` — Anomalía detectada

Se genera una recomendación por cada **feature anómala** identificada en la Fase 5.

| Condición | Prioridad | Mensaje |
|---|---|---|
| Causa identificada (Fase 6, \|r\| ≥ CAUSAL_MIN_CORR) | **high** | Incluye la causa, la correlación y el consejo específico |
| Sin causa identificada | **medium** | Alerta genérica + revisión manual recomendada |

**Ejemplo (high):**
> *Anomalía en humedad del suelo: posible volumen de riego inadecuado/a*
> Tu parcela presenta un valor anómalo de humedad del suelo (LOF score: 2.14). La correlación histórica entre 'soil_humidity' e 'irrigation_mm' es +0.87. Causa probable: exceso de volumen de riego. Correlación estadística: +0.87. Revisa los registros de volumen de riego de las últimas semanas.

---

### `prediction` — Brecha respecto al potencial ML

Se genera cuando el valor **observado** de `yield_kg_ha` o `water_efficiency` está por debajo de la **predicción del modelo** en un margen relevante.

| Brecha | Prioridad |
|---|---|
| > 30 % | **high** |
| 10–30 % | **medium** |
| < 10 % | Se omite |

**Ejemplo (medium):**
> *Tu rendimiento (kg/ha) está un 18.3% por debajo del potencial estimado*
> El modelo estima que parcelas con tus condiciones alcanzan un rendimiento de 4 200 kg/ha, pero tu valor actual es 3 430 kg/ha. Compara tus prácticas con las parcelas análogas de tu grupo.

---

### `benchmark` — Comparación con la media del cluster

Se compara la parcela contra la **media del cluster K-Means** en tres dimensiones clave: eficiencia hídrica, humedad del suelo y volumen de riego. Solo se genera si la brecha supera el 10 %.

| Variable | Dirección del gap | Consejo |
|---|---|---|
| Eficiencia hídrica | parcela < media | Optimizar calendario y volumen de riego |
| Humedad del suelo | parcela < media | Revisar programación de riegos |
| Volumen de riego | parcela > media (gap invertido) | Considerar reducirlo |

---

## Persistencia

Los resultados se guardan en `plot_recommendations` (idempotente: DELETE por `run_date` + INSERT).

### Esquema de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK auto-generado |
| `plot_id` | UUID | FK → `plots.id` |
| `run_date` | Date | Fecha de ejecución del pipeline |
| `category` | String(20) | `anomaly` \| `prediction` \| `benchmark` |
| `priority` | String(10) | `high` \| `medium` \| `low` |
| `title` | String(120) | Título breve de la recomendación |
| `body` | Text | Explicación completa y consejo |

---

## Estructura de archivos

```
app/
  services/
    recommendations/
      recommendation_service.py   ← RecommendationService + RecommendationResult
  repositories/
    recommendation_repository.py  ← save_results(), get_latest_by_plot()
  models/
    plot_recommendation.py        ← ORM PlotRecommendation
  workers/
    clustering_worker.py          ← llama a recommendation_service.run() en Fase 9

alembic/versions/
  k8f9a0b1c2d3_add_plot_recommendations_table.py
```

---

## Configuración

No requiere nuevas variables de entorno. Usa los umbrales de las fases anteriores:

| Variable | Fase | Rol en Fase 9 |
|---|---|---|
| `LOF_THRESHOLD` | 5 | Determina qué parcelas son anómalas |
| `CAUSAL_MIN_CORR` | 6 | Umbral para considerar una causa válida |
| `ML_MIN_SAMPLES` | 8 | Si no hay modelo entrenado, no hay recomendación de predicción |

Los umbrales internos de brecha (`GAP_HIGH=30%`, `GAP_MEDIUM=10%`) están definidos en el servicio y son ajustables en código.

---

## Salida del pipeline (ejemplo)

```
INFO [Fase 9] Generando recomendaciones...
INFO [Fase 9] 3 recomendaciones generadas (1 alta prioridad).
  → [anomaly/high]   "Anomalía en humedad del suelo: posible volumen de riego inadecuado/a"
  → [benchmark/medium] "Tu eficiencia hídrica está un 22.4% por debajo de la media de tu grupo"
  → [prediction/medium] "Tu rendimiento (kg/ha) está un 15.1% por debajo del potencial estimado"
```
