"""
MQTT Consumer — Fase 1
Suscribe al broker Mosquitto y procesa lecturas de dispositivos IoT.
Tópico: devices/{device_code}/readings

Payload esperado:
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
"""

import json
import logging
import threading

import paho.mqtt.client as mqtt
from pydantic import BaseModel, ValidationError, field_validator
from datetime import datetime

from app.services.mqtt.mqtt_service import build_client, TOPIC_READINGS
from app.database.postgres import SessionLocal
from app.repositories.device_repository import device_repository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema de validación del payload entrante
# ---------------------------------------------------------------------------

class MeasuresPayload(BaseModel):
    soil_humidity: float | None = None
    air_temp: float | None = None
    soil_temp: float | None = None
    air_humidity: float | None = None


class DeviceReadingPayload(BaseModel):
    device_id: str
    timestamp: datetime
    battery_mv: int
    measures: MeasuresPayload

    @field_validator("battery_mv")
    @classmethod
    def battery_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("battery_mv debe ser positivo")
        return v


# ---------------------------------------------------------------------------
# Callbacks MQTT
# ---------------------------------------------------------------------------

def _on_connect(client: mqtt.Client, userdata, flags, rc: int) -> None:
    if rc == 0:
        logger.info("MQTT conectado al broker. Suscribiendo a '%s'", TOPIC_READINGS)
        client.subscribe(TOPIC_READINGS, qos=1)
    else:
        logger.error("Error al conectar con el broker MQTT. Código: %d", rc)


def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
    topic = msg.topic
    logger.debug("Mensaje recibido en tópico: %s", topic)

    # 1. Extraer device_code del tópico: devices/{device_code}/readings
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "devices" or parts[2] != "readings":
        logger.warning("Tópico inesperado ignorado: %s", topic)
        return

    device_code = parts[1]

    # 2. Parsear y validar el payload JSON
    try:
        raw = json.loads(msg.payload.decode("utf-8"))
        payload = DeviceReadingPayload(**raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error(
            "Payload inválido desde dispositivo '%s': %s | Raw: %s",
            device_code, exc, msg.payload
        )
        return

    # 3. Verificar que el device_id del payload coincide con el del tópico
    if payload.device_id != device_code:
        logger.warning(
            "device_id del payload ('%s') no coincide con el tópico ('%s'). Ignorado.",
            payload.device_id, device_code
        )
        return

    # 4. Buscar el dispositivo en PostgreSQL
    db = SessionLocal()
    try:
        device = device_repository.get_by_code(db, device_code)
        if device is None:
            logger.warning("Dispositivo no encontrado en BD: '%s'. Mensaje descartado.", device_code)
            return
        if not device.is_active:
            logger.warning("Dispositivo inactivo: '%s'. Mensaje descartado.", device_code)
            return

        logger.info(
            "Lectura válida de '%s' | plot_id=%s | batería=%d mV | medidas=%s",
            device_code, device.plot_id, payload.battery_mv, payload.measures.model_dump()
        )

        # Fase 2: aquí se llamará a measurement_service para persistir en InfluxDB

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Ciclo de vida del consumer (hilo de fondo)
# ---------------------------------------------------------------------------

_client: mqtt.Client | None = None
_thread: threading.Thread | None = None


def start() -> None:
    """Arranca el consumer MQTT en un hilo de fondo."""
    global _client, _thread

    _client = build_client(
        client_id="agrocollective-backend",
        on_connect=_on_connect,
        on_message=_on_message,
    )

    _thread = threading.Thread(target=_client.loop_forever, daemon=True, name="mqtt-consumer")
    _thread.start()
    logger.info("MQTT consumer arrancado en hilo '%s'", _thread.name)


def stop() -> None:
    """Detiene el consumer MQTT limpiamente."""
    global _client
    if _client:
        _client.disconnect()
        logger.info("MQTT consumer desconectado.")
