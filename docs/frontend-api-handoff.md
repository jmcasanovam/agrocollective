# Frontend API Handoff — AgroCollective

**Base URL:** `http://localhost:8000`  
**Documentación interactiva:** `http://localhost:8000/docs` (Swagger)  
**Fecha:** 30 de junio de 2026

---

## Punto de partida — modelo de datos

Un usuario tiene una o varias **fincas**. Cada finca contiene **parcelas**. Cada parcela tiene al menos un **dispositivo IoT** que envía lecturas de sensores en tiempo real vía MQTT. Con esos datos, el backend ejecuta cada noche un pipeline de análisis agronómico y guarda los resultados, que el front consume bajo demanda.

```
User → Farm (1:N) → Plot (1:N) → Device (1:N)
                              → IrrigationRecord (1:N)
                              → Harvest (1:N)
```

| Entidad | Campos relevantes para la UI |
|---------|------------------------------|
| `Farm` | `name`, `latitude`, `longitude`, `area_ha` |
| `Plot` | `name`, `area_ha`, `crop_id` → cultivo, `soil_id` → tipo de suelo |
| `Device` | `code` (e.g. `AGRO-P00-001`), `last_seen_at`, `battery_mv`, `is_active` |
| `IrrigationRecord` | `week_start`, `irrigation_mm` |
| `Harvest` | `harvest_date`, `yield_kg_ha`, `water_consumed_m3_ha` |

---

## Autenticación

Todo endpoint (salvo registro y login) requiere un JWT en el header `Authorization: Bearer <token>`. Sin token → 401.

```
POST /auth/register   { email, password }   → crea cuenta
POST /auth/login      { email, password }   → { access_token, token_type }
```

Guardar el `access_token` y enviarlo en todas las peticiones autenticadas.

---

## Flujo 1 — Mis fincas

Pantalla principal tras el login. Muestra las fincas del usuario autenticado.

```
GET    /farms                              → lista de fincas del usuario
POST   /farms       { name, latitude, longitude, area_ha }
GET    /farms/{farm_id}                    → detalle
PUT    /farms/{farm_id}                    → editar
DELETE /farms/{farm_id}                    → eliminar
```

---

## Flujo 2 — Parcelas de una finca

Al seleccionar una finca → listado de sus parcelas. Para los selectores de cultivo y suelo al crear/editar, usar el catálogo.

```
GET    /farms/{farm_id}/plots              → lista de parcelas
POST   /farms/{farm_id}/plots   { name, crop_id, soil_id, area_ha }
GET    /plots/{plot_id}                    → detalle
PUT    /plots/{plot_id}                    → editar
DELETE /plots/{plot_id}                    → eliminar

GET    /catalog/crops                      → tipos de cultivo disponibles
GET    /catalog/soils                      → tipos de suelo disponibles
```

---

## Flujo 3 — Dispositivos IoT de una parcela

Cada parcela tiene al menos un dispositivo. La UI debería mostrar si está activo (tiempo desde `last_seen_at`) y el nivel de batería.

```
GET    /plots/{plot_id}/devices            → dispositivos de la parcela
POST   /plots/{plot_id}/devices   { code, is_active }
DELETE /plots/{plot_id}/devices/{device_id}
```

**Campos clave para la UI:**

| Campo | Descripción |
|-------|-------------|
| `last_seen_at` | Última lectura recibida — usar para indicar activo / offline |
| `battery_mv` | Batería en milivoltios (típico: 3300 mv ≈ 100%) |
| `is_active` | Si el dispositivo está habilitado por el usuario |

---

## Flujo 4 — Lecturas de sensores

Para mostrar el estado actual del suelo/ambiente o una gráfica histórica.  
Sensores disponibles: `soil_humidity`, `air_temp`, `soil_temp`, `air_humidity`.

```
GET /plots/{plot_id}/sensors/latest          → última lectura de cada sensor
GET /plots/{plot_id}/sensors/history?hours=24  → histórico reciente (default 24h)
```

---

## Flujo 5 — Riego e historial de cosechas

Datos que el usuario introduce manualmente y que alimentan el modelo ML. Cuantos más registros históricos, mejores predicciones.

```
GET  /plots/{plot_id}/irrigation             → registros de riego (semana a semana)
POST /plots/{plot_id}/irrigation   { week_start, irrigation_mm }

GET  /plots/{plot_id}/harvests               → historial de cosechas
POST /plots/{plot_id}/harvests     { harvest_date, yield_kg_ha, water_consumed_m3_ha }
```

---

## Flujo 6 — Resultados del algoritmo de inteligencia

El backend ejecuta un pipeline de análisis agronómico **una vez al día, ~02:00 UTC**. El front **no dispara** el pipeline — solo lee los resultados. No hace falta polling; con cargar al abrir la pantalla de parcela es suficiente.

**Parámetros comunes a todos los endpoints de inteligencia:**

- Sin parámetros → devuelve los resultados del **último pipeline ejecutado**.
- `?run_date=YYYY-MM-DD` → filtra por una fecha de ejecución concreta.

---

### 6.1 — Recomendaciones agronómicas

```
GET /plots/{plot_id}/recommendations
```

**El endpoint más importante para el usuario.** Lista de acciones concretas ordenadas por prioridad (`high → medium → low`). Tres categorías:

| Categoría | Cuándo aparece |
|-----------|----------------|
| `anomaly` | Sensor con valor estadísticamente inusual respecto al grupo de parcelas similares |
| `prediction` | Rendimiento o eficiencia hídrica real por debajo del potencial que estima el modelo ML |
| `benchmark` | Alguna variable por debajo de la media del grupo K-Means de la parcela |

Campos de cada recomendación: `category`, `priority`, `title`, `body`, `run_date`.

---

### 6.2 — Detección de anomalías (LOF)

```
GET /plots/{plot_id}/anomalies
```

Historial de detección de anomalías. Sin `run_date` devuelve todos los registros del más reciente al más antiguo.

| Campo | Descripción |
|-------|-------------|
| `is_anomaly` | `true` si la parcela fue marcada como anómala |
| `lof_score` | Puntuación LOF (>1.5 indica anomalía relevante, 1.0 = normal) |
| `anomalous_features` | Array de variables que provocan la anomalía, e.g. `["soil_humidity", "irrigation_mm"]` |
| `cluster_id` | Grupo K-Means al que pertenece la parcela en esa ejecución |

---

### 6.3 — Parcelas análogas (más similares)

```
GET /plots/{plot_id}/analogues
```

Las 5 parcelas más parecidas agronómicamente, ordenadas de más a menos similar (`rank 1` = más parecida). Útil para mostrar al usuario con quién compararse y qué buenas prácticas adoptar.

| Campo | Descripción |
|-------|-------------|
| `analogue_plot_id` | ID de la parcela análoga — hacer `GET /plots/{id}` para obtener su nombre |
| `distance` | Distancia euclidiana normalizada — menor = más parecida |
| `same_cluster` | `true` si pertenecen al mismo grupo K-Means |
| `rank` | Posición 1–5 por similitud |

---

### 6.4 — Predicciones ML (Random Forest)

```
GET /plots/{plot_id}/ml-predictions
```

Predicciones de un modelo Random Forest entrenado con todas las parcelas. Devuelve **2 registros** (uno por target):

| Campo | Descripción |
|-------|-------------|
| `target` | `"yield_kg_ha"` (rendimiento) o `"water_efficiency"` (eficiencia hídrica) |
| `predicted_value` | Valor esperado según el modelo para las condiciones de esta parcela |
| `model_r2` | Calidad del modelo (0–1). `null` si no hay suficientes datos de entrenamiento |
| `n_training_samples` | Número de parcelas usadas para entrenar el modelo |

---

### 6.5 — Historial de rendimiento

```
GET /plots/{plot_id}/performance-history?limit=90
```

Una instantánea completa por ejecución diaria del pipeline. Ideal para **gráficas de evolución temporal**. Máximo 365 registros (default 90 ≈ 3 meses).

Cada registro incluye: cluster asignado, medias de sensores (humedad suelo, temperatura aire/suelo, humedad aire), frecuencia y volumen de riego, yield, eficiencia hídrica, LOF score, predicciones ML y recuento de recomendaciones.

---

## Cadencia de actualización

| Tipo de dato | Frecuencia | Estrategia recomendada en el front |
|--------------|------------|------------------------------------|
| Lecturas de sensores | Cada ~15 min | Polling cada 60 s en la vista de parcela activa |
| `last_seen_at` del dispositivo | En cada lectura | Refrescar al cargar la vista de parcela |
| Recomendaciones, anomalías, ML, análogos | **1 vez al día (~02:00 UTC)** | Cargar al abrir la pantalla. Mostrar `run_date` como "última actualización" |
| Historial de rendimiento | 1 entrada/día | Cargar al abrir la vista de historial/gráficas |
| Riego y cosechas | Manual (usuario) | Refrescar tras cada POST exitoso |

---

## Resumen de endpoints

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/auth/register` | POST | No | Crear cuenta |
| `/auth/login` | POST | No | Obtener JWT |
| `/farms` | GET / POST | Sí | Listar / crear fincas |
| `/farms/{id}` | GET / PUT / DELETE | Sí | Detalle / editar / eliminar finca |
| `/farms/{id}/plots` | GET / POST | Sí | Listar / crear parcelas |
| `/plots/{id}` | GET / PUT / DELETE | Sí | Detalle / editar / eliminar parcela |
| `/plots/{id}/devices` | GET / POST | Sí | Dispositivos de la parcela |
| `/plots/{id}/sensors/latest` | GET | Sí | Última lectura de sensores |
| `/plots/{id}/sensors/history` | GET | Sí | Histórico de sensores |
| `/plots/{id}/irrigation` | GET / POST | Sí | Registros de riego |
| `/plots/{id}/harvests` | GET / POST | Sí | Historial de cosechas |
| `/plots/{id}/recommendations` | GET | Sí | Recomendaciones del pipeline |
| `/plots/{id}/anomalies` | GET | Sí | Historial LOF |
| `/plots/{id}/analogues` | GET | Sí | Parcelas más similares |
| `/plots/{id}/ml-predictions` | GET | Sí | Predicciones Random Forest |
| `/plots/{id}/performance-history` | GET | Sí | Historial de instantáneas del pipeline |
| `/catalog/crops` | GET | Sí | Tipos de cultivo |
| `/catalog/soils` | GET | Sí | Tipos de suelo |
