# Fase 3: Obtención de históricos y generación de variables agregadas

## Descripción

El sistema calcula periódicamente un conjunto de variables representativas por parcela, combinando datos de sensores (InfluxDB) y datos agronómicos (PostgreSQL). Estas variables son la entrada del algoritmo de clustering (Fase 4).

El proceso se ejecuta sobre todas las parcelas activas (con `hash_plot` generado) y puede lanzarse manualmente o de forma programada cada noche.

---

## Variables agregadas por parcela (`PlotAggregates`)

| Variable | Fuente | Cálculo | Unidad |
|---|---|---|---|
| `avg_soil_humidity` | InfluxDB `measurements` | Media ventana `AGGREGATION_WINDOW_DAYS` | % |
| `avg_air_temp` | InfluxDB `measurements` | Media ventana | °C |
| `avg_soil_temp` | InfluxDB `measurements` | Media ventana | °C |
| `avg_air_humidity` | InfluxDB `measurements` | Media ventana | % |
| `irrigation_frequency` | PostgreSQL `irrigation_records` | Nº de registros en la ventana | - |
| `avg_irrigation_mm` | PostgreSQL `irrigation_records` | Media de mm/riego | mm |
| `total_water_mm` | PostgreSQL `irrigation_records` | Suma total en la ventana | mm |
| `yield_kg_ha` | PostgreSQL `harvests` | Última cosecha disponible | kg/ha |
| `water_efficiency` | Calculado | `yield_kg_ha / (total_water_mm × 10)` | kg/m³ |

> `water_efficiency` es `None` si no hay cosecha o riego registrado.  
> 1 mm/ha = 10 m³/ha, de ahí el factor ×10.

---

## Ventana temporal configurable

La ventana de días se controla con la variable de entorno:

```env
AGGREGATION_WINDOW_DAYS=30
```

Se puede sobrescribir en tiempo de ejecución pasando el número de días como argumento.

---

## Flujo de ejecución

```
clustering_worker.run_pipeline()
  │
  ├─ Consulta todas las parcelas con hash_plot (PostgreSQL)
  │
  └─ Por cada parcela → aggregation_service.compute(plot)
        │
        ├─ InfluxDB: mean() de soil_humidity, air_temp, soil_temp, relative_humidity
        │    en la ventana [now - AGGREGATION_WINDOW_DAYS, now]
        │    → falla con warning si InfluxDB no está disponible (no bloquea)
        │
        ├─ PostgreSQL: irrigation_records con week_start >= since_date
        │    → irrigation_frequency, avg_irrigation_mm, total_water_mm
        │
        ├─ PostgreSQL: última harvest ordenada por harvest_date DESC
        │    → yield_kg_ha
        │
        └─ Calcula water_efficiency si hay yield y riego
```

---

## Ficheros

| Fichero | Responsabilidad |
|---|---|
| `app/services/measurements/aggregation_service.py` | Lógica de cálculo por parcela |
| `app/workers/clustering_worker.py` | Orquestación del pipeline (Fases 3-10) |

---

## Ejecución manual

```bash
docker exec -it agro_backend bash

# Usando la ventana configurada en .env (por defecto 30 días)
python -m app.workers.clustering_worker

# Forzando una ventana distinta (ej: últimos 7 días)
python -m app.workers.clustering_worker 7
```

### Salida esperada

```
INFO - === Inicio pipeline clustering | 2026-06-29T18:56:22Z ===
INFO - Parcelas a procesar: 3
INFO - [1/3] Parcela 2e8d557a... | hum=45.2 air=22.1 riego=4 total_mm=180.0 yield=4200.0 eff=2.3333
INFO - [2/3] Parcela a1b2c3d4... | hum=38.7 air=21.8 riego=3 total_mm=120.0 yield=None eff=None
INFO - [3/3] Parcela ff1122ab... | hum=51.0 air=23.4 riego=5 total_mm=240.0 yield=3800.0 eff=1.5833
INFO - === Fase 3 completada | 3/3 parcelas | 0.8s ===
```

---

## Requisitos y configuración

### InfluxDB token (obligatorio para datos de sensores)

Si InfluxDB devuelve `401 Unauthorized`, el token no está configurado:

1. Accede a `http://localhost:8086`
2. Ve a **Data → API Tokens → Generate All Access Token**
3. Copia el token y añádelo al `.env`:

```env
INFLUXDB_TOKEN=tu_token_aqui
```

4. Reinicia el backend: `docker-compose restart backend`

> El worker continúa funcionando aunque InfluxDB falle: los campos de sensor quedan a `None` pero los datos de PostgreSQL (riego, cosechas) se calculan igualmente.

### Datos mínimos para ver variables completas

| Dato | Cómo añadirlo |
|---|---|
| Lecturas de sensores | Opción 2 del script `test_mqtt_flow.py` (repetir varias veces) |
| Registros de riego | API `POST /plots/{plot_id}/irrigation` (Fase futura) o inserción directa en BD |
| Cosechas | API `POST /plots/{plot_id}/harvests` (Fase futura) o inserción directa en BD |

---

## Integración con Fases siguientes

`run_pipeline()` devuelve `list[PlotAggregates]`. Las fases sucesivas se encadenan en el mismo worker:

```python
# clustering_worker.py (estructura prevista)
results = [aggregation_service.compute(db, plot) for plot in plots]  # Fase 3
clusters = kmeans_service.run(results)                                # Fase 4
anomalies = lof_service.run(results, clusters)                        # Fase 5
# ...
```
