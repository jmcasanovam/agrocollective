# Guía de prueba end-to-end del pipeline inteligente

Pasos seguidos para verificar el sistema completo: desde la simulación IoT hasta el consumo de la API REST.

---

## Requisitos previos

- Docker en ejecución (`agro_backend`, `agro_postgres`, `agro_influxdb`, `agro_mosquitto`)
- Python con `httpx` y `paho-mqtt` instalados en el entorno local
- Backend accesible en `http://localhost:8000`

---

## Paso 1: Crear el entorno de simulación

El script `setup_simulation.py` crea via API un usuario, una finca con 10 parcelas y sus dispositivos, y luego inserta directamente en PostgreSQL 8 semanas de registros de riego y 1 cosecha por parcela.

```bash
python scripts/setup_simulation.py
```

**Resultado esperado:**

```
[OK]  Usuario creado: simulacion@agrocollective.com
[OK]  Finca creada: Finca Simulacion
[OK]  Parcela Sim-P00 creada  ...  Sim-P09 creada
[OK]  80 registros insertados (10 x 8 semanas riego + 1 cosecha)
```

**Verificar en PostgreSQL:**

```sql
SELECT count(*) FROM plots;          -- 11 (10 sim + Parcela Norte si existe)
SELECT count(*) FROM devices;        -- >= 10
SELECT count(*) FROM irrigation_records;  -- >= 80
SELECT count(*) FROM harvests;       -- >= 10
```

---

## Paso 2: Simular lecturas de sensores (MQTT → InfluxDB + PostgreSQL)

El script `simulate_sensors.py` publica mensajes MQTT con datos de 3 perfiles agronómicos:

| Perfil | Parcelas | Humedad suelo | Riego |
|--------|----------|---------------|-------|
| `seco_eficiente` | P00, P03, P06 | ~35-40% | bajo |
| `moderado` | P01, P02, P05, P08 | ~48-56% | medio |
| `humedo_intensivo` | P04, P07, P09 | ~67-70% | alto |

```bash
# Simulación estándar (4 horas de datos, intervalos de 15 min)
python scripts/simulate_sensors.py

# Opciones adicionales
python scripts/simulate_sensors.py --dry-run   # sin enviar, solo muestra mensajes
python scripts/simulate_sensors.py --seed 999  # reproducible con semilla distinta
python scripts/simulate_sensors.py --realtime  # publicación en tiempo real
```

**Verificar en PostgreSQL** (los dispositivos deben tener `last_seen_at` actualizado):

```sql
SELECT code, last_seen_at, battery_mv FROM devices ORDER BY code;
```

**Verificar en InfluxDB** (http://localhost:8086):

- Bucket: `agrocollective` (o el nombre configurado en `INFLUXDB_BUCKET`)
- Measurement: `sensor_readings`
- Filtrar por `_field = "soil_humidity"` o cualquier otro sensor

> Los `ROLLBACK` que aparecen en los logs del backend son normales: SQLAlchemy cierra la transacción de PostgreSQL tras cada commit del `UPDATE devices`, lo que genera ese mensaje incluso cuando todo va bien.

---

## Paso 3: Ejecutar el pipeline manualmente

El pipeline nocturno (Fases 3-10) se ejecuta automáticamente a las `CLUSTERING_SCHEDULE_HOUR` UTC, pero se puede lanzar a mano:

```bash
docker exec agro_backend python -m app.workers.clustering_worker
```

**Resultado esperado en los logs:**

```
INFO - Pipeline completado | Fases 3-10 | 11 parcelas | k=5 | 0 anomalías | 0 causas | 22 predicciones | 1 recomendaciones | 2.5s
```

**Interpretación de los valores:**

| Campo | Valor | Explicación |
|-------|-------|-------------|
| `11 parcelas` | ✓ | 10 simuladas + Parcela Norte (si existe) |
| `k=5` | ✓ | K-Means encontró 5 clusters óptimos |
| `0 anomalías` | Normal | LOF necesita clusters de ≥6 plots para ser sensible; con clusters de 2-4 todos los scores son ~1.0 |
| `22 predicciones` | ✓ | 11 parcelas × 2 targets (yield + efficiency) |
| `1 recomendaciones` | ✓ | Sim-P09 (perfil más extremo) detectada con eficiencia subóptima |

**Verificar clusters en PostgreSQL:**

```sql
SELECT p.name, pc.cluster_id, ph.avg_soil_humidity, ph.is_anomaly, ph.n_recommendations
FROM plot_performance_history ph
JOIN plots p ON p.id = ph.plot_id
JOIN plot_clusters pc ON pc.plot_id = ph.plot_id AND pc.run_date = ph.run_date
WHERE ph.run_date = CURRENT_DATE
ORDER BY pc.cluster_id, p.name;
```

---

## Paso 4: Consumir la API REST (frontend)

### 4.1: Autenticación

```powershell
$r = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" `
     -Method POST -ContentType "application/json" `
     -Body '{"email":"simulacion@agrocollective.com","password":"Simul2026!"}'
$token = $r.access_token
$headers = @{ Authorization = "Bearer $token" }
```

### 4.2: Obtener IDs de finca y parcelas

```powershell
$farms  = Invoke-RestMethod -Uri "http://localhost:8000/farms" -Headers $headers
$farm_id = $farms[0].id

$plots  = Invoke-RestMethod -Uri "http://localhost:8000/farms/$farm_id/plots" -Headers $headers
$p09    = $plots | Where-Object { $_.name -eq "Sim-P09" }
$plot_id = $p09.id
```

### 4.3: Endpoints de inteligencia

Todos requieren autenticación JWT y verifican que la parcela pertenece al usuario.

**Recomendaciones agronómicas:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/plots/$plot_id/recommendations" `
    -Headers $headers | ConvertTo-Json -Depth 5
```

Devuelve lista de recomendaciones ordenadas por prioridad (`high → medium → low`). Categorías posibles: `anomaly`, `prediction`, `benchmark`.

**Anomalías LOF:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/plots/$plot_id/anomalies" `
    -Headers $headers | ConvertTo-Json -Depth 5
```

Devuelve historial de detección LOF. `anomalous_features` es una lista de las variables que disparan la anomalía.

**Parcelas análogas (más similares):**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/plots/$plot_id/analogues" `
    -Headers $headers | ConvertTo-Json -Depth 5
```

Devuelve las 5 parcelas más cercanas en el espacio de features normalizado (`rank=1` = más parecida). `same_cluster=true` indica que pertenecen al mismo grupo.

**Predicciones ML (Random Forest):**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/plots/$plot_id/ml-predictions" `
    -Headers $headers | ConvertTo-Json -Depth 5
```

Devuelve 2 registros: `yield_kg_ha` y `water_efficiency`. `model_r2=null` indica que LOO cross-validation no produjo un R² fiable (normal con pocos datos).

**Historial de rendimiento:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/plots/$plot_id/performance-history" `
    -Headers $headers | ConvertTo-Json -Depth 5
```

Instantánea completa del pipeline por fecha. Soporta `?limit=90` (default) hasta `?limit=365`.


## Cómo generar resultados más ricos

Para ver **anomalías reales** el pipeline necesita clusters con más puntos. Ejecuta el simulador varias veces con semillas distintas para acumular varianza:

```bash
python scripts/simulate_sensors.py --seed 111
python scripts/simulate_sensors.py --seed 222
python scripts/simulate_sensors.py --seed 333
docker exec agro_backend python -m app.workers.clustering_worker
```

Con más ejecuciones diarias del pipeline (`run_date` distinto cada día) el historial de rendimiento también crece y `/performance-history` devuelve una serie temporal más completa.

---

## Referencia rápida de endpoints

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/auth/register` | POST | No | Crear usuario |
| `/auth/login` | POST | No | Obtener JWT |
| `/farms` | GET | Sí | Listar fincas del usuario |
| `/farms/{id}/plots` | GET | Sí | Listar parcelas de una finca |
| `/plots/{id}/recommendations` | GET | Sí | Recomendaciones del pipeline |
| `/plots/{id}/anomalies` | GET | Sí | Historial LOF |
| `/plots/{id}/analogues` | GET | Sí | Parcelas más similares |
| `/plots/{id}/ml-predictions` | GET | Sí | Predicciones Random Forest |
| `/plots/{id}/performance-history` | GET | Sí | Historial de instantáneas |

Todos los endpoints de inteligencia aceptan `?run_date=YYYY-MM-DD` para filtrar por fecha de ejecución del pipeline.
