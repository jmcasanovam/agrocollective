# Fase 2: Ingesta y almacenamiento en InfluxDB

## Descripción

Tras recibir y validar el mensaje MQTT (Fase 1), el backend persiste la lectura en InfluxDB usando el `hash_plot` como identificador anónimo, y actualiza los metadatos operativos del dispositivo en PostgreSQL.

---

## Flujo completo (Fases 1 + 2)

```
ESP32
  │  MQTT publish → devices/D001/readings
  ▼
Mosquitto (broker, caché 24h)
  │
  ▼
mqtt_consumer (hilo FastAPI)
  ├─ Validar JSON con Pydantic
  ├─ Comprobar device_id == code del tópico
  ├─ Buscar device en PostgreSQL → obtener plot_id
  │
  └─▶ measurement_service.store_reading()
        ├─ Cargar plot → farm → region (joinedload)
        ├─ Obtener hash_plot (SHA256 del plot.id, ya generado)
        ├─ Obtener region_code
        │
        ├─ Escribir punto en InfluxDB
        │    measurement: "measurements"
        │    tags:   hash_plot, region_code
        │    fields: soil_humidity, air_temp, soil_temp, relative_humidity, battery
        │    time:   timestamp del payload (UTC)
        │
        └─ Actualizar device en PostgreSQL
             last_seen_at = timestamp
             battery_mv   = battery_mv
```

---

## Anonimización

El `hash_plot` es un SHA-256 del UUID interno de la parcela, generado en el momento de creación de la parcela y almacenado en `plots.hash_plot`. **Nunca se almacena en InfluxDB ningún identificador directo** de finca, parcela o usuario.

```
plot.id (UUID privado) → SHA-256 → hash_plot (tag InfluxDB)
```

---

## Punto en InfluxDB

```
measurement: measurements
tags:
  hash_plot   = "a1b2c3d4..."   (SHA-256 del plot.id)
  region_code = "MU01"

fields:
  battery          = 4150       (mV, siempre presente)
  soil_humidity    = 45.0       (%)
  air_temp         = 22.5       (°C)
  soil_temp        = 20.8       (°C)
  relative_humidity= 55.0       (%)

time: 2026-05-19T14:32:15Z
```

Los campos de sensor son opcionales: solo se escriben los que el dispositivo haya enviado (según los sensores asignados).

---

## Cambios en PostgreSQL (Fase 2)

Se añadieron dos columnas a la tabla `devices`:

| Columna | Tipo | Descripción |
|---|---|---|
| `last_seen_at` | `TIMESTAMPTZ` | Timestamp de la última lectura recibida |
| `battery_mv` | `INTEGER` | Tensión de batería de la última lectura |

Migración: `e2f3a4b5c6d7_add_device_telemetry_fields`

---

## Prueba manual

1. Registrar un usuario, crear finca, parcela y dispositivo con `code = "D001"` vía API.
2. Publicar mensaje MQTT:

```bash
mosquitto_pub \
  -h localhost -p 1883 \
  -t "devices/D001/readings" \
  -m '{
    "device_id": "D001",
    "timestamp": "2026-05-19T14:32:15Z",
    "battery_mv": 4150,
    "measures": {
      "soil_humidity": 45,
      "air_temp": 22.5,
      "soil_temp": 20.8,
      "air_humidity": 55
    }
  }'
```

3. Verificar en InfluxDB (Data Explorer):

```flux
from(bucket: "agrocollective")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "measurements")
```

4. Verificar en PostgreSQL que `last_seen_at` y `battery_mv` se han actualizado:

```sql
SELECT code, last_seen_at, battery_mv FROM devices WHERE code = 'D001';
```
