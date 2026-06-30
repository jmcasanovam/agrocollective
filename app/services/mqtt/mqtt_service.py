import logging
import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)

TOPIC_READINGS = "devices/+/readings"


def build_client(client_id: str, on_connect, on_message) -> mqtt.Client:
    """Construye y configura un cliente MQTT Paho."""
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.MQTT_HOST, settings.MQTT_PORT, keepalive=60)
    return client
