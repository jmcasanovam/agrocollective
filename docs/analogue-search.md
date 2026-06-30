# Fase 7 — Búsqueda de Parcelas Análogas

## Objetivo

Para cada parcela activa, identificar las **N parcelas más similares** del sistema en función de sus variables agronómicas agregadas. Esto permite:

- Mostrar al agricultor referencias reales de parcelas con condiciones parecidas.
- Alimentar las recomendaciones de la Fase 9 con ejemplos de buenas prácticas.
- Detectar si parcelas anómalas (Fase 5) tienen comparables sanos con mejores resultados.

---

## Algoritmo

### 1. Reconstrucción del espacio normalizado

Se usa el mismo conjunto de 9 features de la Fase 4, con la misma estrategia de imputación (`None → 0`) y normalización (`StandardScaler`):

```
avg_soil_humidity, avg_air_temp, avg_soil_temp, avg_air_humidity,
irrigation_frequency, avg_irrigation_mm, total_water_mm,
yield_kg_ha, water_efficiency
```

### 2. Matriz de distancias

Se calcula la distancia euclidiana entre todos los pares de parcelas en el espacio normalizado:

```
d(i, j) = √Σ (x_i_k − x_j_k)²    para k en las 9 features
```

Esto produce una matriz **N×N** calculada de forma vectorizada con NumPy.

### 3. Ranking por parcela

Para cada parcela `i`, se ordenan las demás por distancia ascendente (excluyendo la propia) y se toman las `top-N = min(ANALOGUE_TOP_N, N-1)` más cercanas.

### 4. Etiqueta `same_cluster`

Se marca si la análoga pertenece al mismo cluster K-Means (Fase 4). Una análoga en el mismo cluster sugiere similitud estructural; fuera del cluster puede indicar similitud parcial o valores extremos compartidos.

---

## Persistencia

Los resultados se guardan en `plot_analogues` (idempotente: DELETE por `run_date` + INSERT).

### Esquema de la tabla

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK auto-generado |
| `plot_id` | UUID | Parcela evaluada (FK → `plots.id`) |
| `analogue_plot_id` | UUID | Parcela análoga (FK → `plots.id`) |
| `run_date` | Date | Fecha de ejecución del pipeline |
| `rank` | Integer | Posición (1 = más cercana) |
| `distance` | Float | Distancia euclidiana en espacio normalizado |
| `same_cluster` | Boolean | True si comparten cluster K-Means |

---

## Configuración (`.env`)

```dotenv
# Número de parcelas análogas a guardar por parcela
ANALOGUE_TOP_N=5
```

---

## Estructura de archivos

```
app/
  services/
    clustering/
      analogue_service.py       ← AnalogueService + AnalogueResult dataclass
  repositories/
    analogue_repository.py      ← save_results(), get_analogues_for_plot()
  models/
    plot_analogue.py            ← ORM PlotAnalogue
  workers/
    clustering_worker.py        ← llama a analogue_service.run() en Fase 7

alembic/versions/
  i6d7e8f9a0b1_add_plot_analogues_table.py
```

---

## Limitaciones (MVP)

- La búsqueda es global (no se restringe al mismo cluster ni región). Con muchas parcelas podría filtrarse por cluster para mejorar la relevancia.
- La distancia en el espacio normalizado es sensible a la imputación de `None → 0`. Parcelas sin datos de cosecha o riego tienden a agruparse entre sí.
- Con menos de 2 parcelas en el sistema no se generan análogas.

---

## Salida del pipeline (ejemplo)

```
INFO [Fase 7] Buscando parcelas análogas...
INFO [Fase 7] 5 registros de análogas generados para 1 parcelas (top-5).
INFO [Fase 7] 5 registros de análogas guardados.
```

Con 3 parcelas y `ANALOGUE_TOP_N=5` se guardan `3 × 2 = 6` registros (top-2 por limitación de N-1).
