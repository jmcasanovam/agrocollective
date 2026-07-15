import os
import json
from datetime import datetime, timezone
import paho.mqtt.publish as publish
from app.database.postgres import SessionLocal
from app.models.device import Device

def main():
    db = SessionLocal()
    try:
        devices = db.query(Device).all()
        print(f"Encontrados {len(devices)} dispositivos en PostgreSQL.")
        
        mqtt_host = os.environ.get("MQTT_HOST", "mosquitto")
        mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
        
        for dev in devices:
            if not dev.is_active:
                continue
            
            topic = f"devices/{dev.code}/readings"
            payload = {
                "device_id": dev.code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "battery_mv": 4180,
                "measures": {
                    "soil_humidity": 24.5,
                    "air_temp": 21.8,
                    "soil_temp": 17.5,
                    "air_humidity": 58.0
                }
            }
            
            publish.single(
                topic,
                payload=json.dumps(payload),
                hostname=mqtt_host,
                port=mqtt_port
            )
            print(f"Enviada telemetría inicial para {dev.code} en tópico: {topic}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
