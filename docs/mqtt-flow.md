# Fase 1: Flujo MQTT — Dispositivo a Backend

## Descripción general

Los dispositivos IoT (ESP32) publican lecturas de sensores al broker Mosquitto. El backend FastAPI consume estos mensajes en tiempo real mediante un hilo dedicado.

---

## Broker: Eclipse Mosquitto 2

| Parámetro | Valor |
|---|---|
| Puerto | 1883 |
| Protocolo | MQTT 3.1.1 |
| Autenticación | Anónima (MVP) |
| Persistencia | 24 horas |
| Imagen Docker | `eclipse-mosquitto:2` |

---

## Tópico de publicación

```
devices/{device_code}/readings
```

**Ejemplo:**
```
devices/D001/readings
```

El `device_code` debe coincidir con el campo `code` del dispositivo registrado en PostgreSQL.

---

## Payload del dispositivo

El ESP32 serializa la lectura a JSON y la publica en el tópico correspondiente.

```json
{
    "device_id": "D001",
    "timestamp": "2026-05-19T14:32:15Z",
    "battery_mv": 4150,
    "measures": {
        "soil_humidity": 45,
        "air_temp": 22.5,
        "soil_temp": 20.8,
        "air_humidity": 55
    }
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `device_id` | string | Código único del dispositivo (coincide con `devices.code`) |
| `timestamp` | ISO 8601 UTC | Momento de la captura del sensor |
| `battery_mv` | int | Tensión de batería en milivoltios |
| `measures.soil_humidity` | float | Humedad del suelo (%) |
| `measures.air_temp` | float | Temperatura del aire (°C) |
| `measures.soil_temp` | float | Temperatura del suelo (°C) |
| `measures.air_humidity` | float | Humedad relativa del aire (%) |

Todos los campos de `measures` son opcionales: un dispositivo puede tener solo los sensores que tenga físicamente asignados.

---

## Procesamiento en el backend

```
ESP32
  │
  │  MQTT publish → devices/D001/readings
  ▼
Mosquitto (broker)
  │
  │  Distribución a suscriptores
  ▼
mqtt_consumer (hilo FastAPI)
  │
  ├─ 1. Extraer device_code del tópico
  ├─ 2. Validar payload (Pydantic)
  ├─ 3. Comprobar que device_id == device_code del tópico
  ├─ 4. Buscar dispositivo en PostgreSQL por code
  │      → Si no existe o está inactivo: descartar + log warning
  │
  └─ 5. [Fase 2] Persistir en InfluxDB con hash_plot como tag
```

### Reglas de validación (Fase 1)

| Comprobación | Acción si falla |
|---|---|
| JSON malformado | Log error, descartar |
| Campos obligatorios ausentes | Log error, descartar |
| `device_id` ≠ code del tópico | Log warning, descartar |
| Dispositivo no existe en BD | Log warning, descartar |
| Dispositivo inactivo | Log warning, descartar |
| `battery_mv` negativo | Log error, descartar |

---

## Ciclo de vida

El consumer arranca automáticamente al iniciar FastAPI (evento `lifespan`) y se detiene limpiamente al apagar la aplicación. Corre en un hilo daemon (`mqtt-consumer`) para no bloquear el event loop de uvicorn.

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_consumer.start()   # al arrancar
    yield
    mqtt_consumer.stop()    # al apagar
```

---

## Prueba manual

Con los servicios Docker levantados, publica un mensaje de prueba:

En Windows, también se puede probar desde `cmd` instalando Mosquitto desde la [web oficial](https://mosquitto.org/download/) y usando estas utilidades:

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -p 1883 -t devices/D001/readings
```

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -p 1883 -t devices/D001/readings -m "{ \"device_id\": \"D001\", \"timestamp\": \"2026-05-19T14:32:15Z\", \"battery_mv\": 4150, \"measures\": { \"soil_humidity\": 45, \"air_temp\": 22.5, \"soil_temp\": 20.8, \"air_humidity\": 55 } }"
```

```bash
# Instalar cliente mosquitto en local (si no lo tienes)
# apt install mosquitto-clients  /  brew install mosquitto

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

El log del backend debe mostrar:
```
INFO  Lectura válida de 'D001' | plot_id=<uuid> | batería=4150 mV | medidas={...}
```
