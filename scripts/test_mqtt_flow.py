"""
Script interactivo de prueba end-to-end del flujo MQTT (Fases 1 + 2).

Uso:
    python scripts/test_mqtt_flow.py

Opciones del menú:
    1. Crear usuario + setup completo (finca/parcela/dispositivo) + publicar
    2. Login y publicar lectura (crea lo que falte automáticamente)
    3. Login y leer últimos datos registrados del dispositivo
    4. Salir

Requisitos:
    - docker-compose up en marcha (backend, postgres, influxdb, mosquitto)
    - httpx y paho-mqtt instalados (están en requirements.txt)
"""

import json
import os
import time
from datetime import datetime, timezone

import httpx
import paho.mqtt.publish as publish

# =============================================================================
# VARIABLES DE CONFIGURACIÓN: modifica aquí antes de ejecutar
# =============================================================================

# Dentro del contenedor Docker el broker se llama "mosquitto".
# Fuera del contenedor (local) usar "localhost".
# La variable de entorno MQTT_HOST ya está configurada en docker-compose.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MQTT_HOST    = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT    = int(os.getenv("MQTT_PORT", "1883"))

# Usuario
USER_EMAIL    = "agricultor@prueba.com"
USER_PASSWORD = "Test1234!"

# Finca
FARM_NAME      = "Finca Los Olivos"
FARM_LATITUDE  = 37.9922
FARM_LONGITUDE = -1.1307
FARM_AREA_HA   = 12.5

# Parcela
PLOT_NAME    = "Parcela Norte"
PLOT_AREA_HA = 4.2

# Dispositivo
DEVICE_CODE = "D001"

# Lectura MQTT de prueba
MQTT_BATTERY_MV = 4150
MQTT_MEASURES = {
    "soil_humidity": 45.0,
    "air_temp":      22.5,
    "soil_temp":     20.8,
    "air_humidity":  55.0,
}

# =============================================================================
# UI helpers
# =============================================================================

W = 62


def header(title: str) -> None:
    print(f"\n{'═' * W}")
    print(f"  {title}")
    print(f"{'═' * W}")


def step(msg: str) -> None:
    print(f"\n  {'─' * (W - 4)}")
    print(f"  {msg}")
    print(f"  {'─' * (W - 4)}")


def ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def info(msg: str) -> None:
    print(f"  ·  {msg}")


def warn(msg: str) -> None:
    print(f"  !  {msg}")


def bail(msg: str, response: httpx.Response | None = None) -> None:
    print(f"  ✗  {msg}")
    if response is not None:
        print(f"     Status : {response.status_code}")
        print(f"     Detalle: {response.text[:300]}")
    raise SystemExit(1)


# =============================================================================
# HTTP helpers
# =============================================================================

def api_get(client: httpx.Client, path: str) -> list | dict:
    r = client.get(f"{API_BASE_URL}{path}")
    if r.status_code not in (200, 201):
        bail(f"GET {path} falló", r)
    return r.json()


def api_post(client: httpx.Client, path: str, body: dict) -> dict:
    r = client.post(f"{API_BASE_URL}{path}", json=body)
    if r.status_code not in (200, 201):
        bail(f"POST {path} falló", r)
    return r.json()


# =============================================================================
# Acciones
# =============================================================================

def do_register(client: httpx.Client) -> None:
    step("Registrar usuario")
    r = client.post(f"{API_BASE_URL}/auth/register", json={
        "email":    USER_EMAIL,
        "password": USER_PASSWORD,
    })
    if r.status_code in (200, 201):
        ok(f"Usuario creado: {USER_EMAIL}")
    elif r.status_code == 400:
        warn(f"El usuario ya existía: {USER_EMAIL}")
    else:
        bail("Registro fallido", r)


def do_login(client: httpx.Client) -> str:
    step("Login")
    data = api_post(client, "/auth/login", {"email": USER_EMAIL, "password": USER_PASSWORD})
    token = data["access_token"]
    ok(f"Autenticado como {USER_EMAIL}")
    info(f"Token: {token[:28]}...")
    return token


def _get_or_create_catalog(client: httpx.Client) -> tuple[str, str, str | None]:
    """Devuelve (crop_id, soil_id, region_id). Falla si el catálogo está vacío."""
    crops = api_get(client, "/crops")
    if not crops:
        bail("Sin cultivos en el catálogo. Ejecuta: python scripts/seed_data.py")
    soils = api_get(client, "/soils")
    if not soils:
        bail("Sin tipos de suelo. Ejecuta: python scripts/seed_data.py")
    regions = api_get(client, "/regions")
    return crops[0]["id"], soils[0]["id"], (regions[0]["id"] if regions else None)


def _find_device(client: httpx.Client) -> tuple[dict, dict] | tuple[None, None]:
    """Busca DEVICE_CODE entre las fincas del usuario. Devuelve (device, plot) o (None, None)."""
    farms = api_get(client, "/farms")
    for farm in farms:
        plots = api_get(client, f"/farms/{farm['id']}/plots")
        for plot in plots:
            r = client.get(f"{API_BASE_URL}/plots/{plot['id']}/devices")
            if r.status_code == 200:
                device = r.json()
                if device.get("code") == DEVICE_CODE:
                    return device, plot
    return None, None


def ensure_setup(client: httpx.Client) -> None:
    """
    Garantiza que existen finca, parcela y dispositivo para el usuario actual.
    Crea solo lo que falta.
    """
    step("Verificar / crear recursos (finca, parcela, dispositivo)")

    device, _ = _find_device(client)
    if device:
        ok(f"Dispositivo '{DEVICE_CODE}' ya existe. No es necesario crear nada.")
        return

    info("Dispositivo no encontrado. Creando recursos necesarios...")

    crop_id, soil_id, region_id = _get_or_create_catalog(client)
    ok(f"Catálogo OK: cultivo={crop_id[:8]}... suelo={soil_id[:8]}...")

    # Finca: reutilizar la primera si ya existe
    farms = api_get(client, "/farms")
    if farms:
        farm_id = farms[0]["id"]
        warn(f"Reutilizando finca existente: {farms[0]['name']} ({farm_id})")
    else:
        farm = api_post(client, "/farms", {
            "name":      FARM_NAME,
            "latitude":  FARM_LATITUDE,
            "longitude": FARM_LONGITUDE,
            "area_ha":   FARM_AREA_HA,
            "region_id": region_id,
        })
        farm_id = farm["id"]
        ok(f"Finca creada: {FARM_NAME} ({farm_id})")

    # Parcela: reutilizar la primera de esa finca si ya existe
    plots = api_get(client, f"/farms/{farm_id}/plots")
    if plots:
        plot_id = plots[0]["id"]
        warn(f"Reutilizando parcela existente: {plots[0]['name']} ({plot_id})")
    else:
        plot = api_post(client, f"/farms/{farm_id}/plots", {
            "name":    PLOT_NAME,
            "crop_id": crop_id,
            "soil_id": soil_id,
            "area_ha": PLOT_AREA_HA,
        })
        plot_id = plot["id"]
        ok(f"Parcela creada: {PLOT_NAME} (hash={plot.get('hash_plot', 'N/D')[:12]}...)")

    # Dispositivo
    device = api_post(client, f"/plots/{plot_id}/devices", {"code": DEVICE_CODE})
    ok(f"Dispositivo creado: code={DEVICE_CODE} ({device['id']})")


def do_publish() -> None:
    step(f"Publicar lectura MQTT  [{MQTT_HOST}:{MQTT_PORT}]")
    topic = f"devices/{DEVICE_CODE}/readings"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "device_id":  DEVICE_CODE,
        "timestamp":  timestamp,
        "battery_mv": MQTT_BATTERY_MV,
        "measures":   MQTT_MEASURES,
    }
    msg = json.dumps(payload)
    try:
        publish.single(topic, msg, hostname=MQTT_HOST, port=MQTT_PORT, qos=1)
    except Exception as exc:
        bail(f"No se pudo conectar al broker MQTT ({MQTT_HOST}:{MQTT_PORT}): {exc}")
    ok(f"Tópico   : {topic}")
    ok(f"Timestamp: {timestamp}")
    info(f"Payload  : {msg}")
    time.sleep(1)
    ok("Mensaje entregado al broker.")


def do_read(client: httpx.Client) -> None:
    step(f"Últimos datos registrados: dispositivo '{DEVICE_CODE}'")

    device, plot = _find_device(client)

    if not device:
        warn(f"Dispositivo '{DEVICE_CODE}' no encontrado.")
        warn("Ejecuta la opción 1 o 2 primero para crear los recursos.")
        return

    print()
    print(f"  {'Campo':<22} Valor")
    print(f"  {'─'*22} {'─'*33}")
    print(f"  {'Dispositivo':<22} {device['code']}  (id: {device['id'][:8]}...)")
    print(f"  {'Activo':<22} {'Sí' if device['is_active'] else 'No'}")
    print(f"  {'Parcela':<22} {plot['name']}  (id: {plot['id'][:8]}...)")

    hash_plot = plot.get("hash_plot") or "N/D"
    print(f"  {'hash_plot (InfluxDB)':<22} {hash_plot[:20]}...")
    print(f"  {'Última lectura':<22} {device.get('last_seen_at') or '(sin datos aún)'}")
    print(f"  {'Batería':<22} {device.get('battery_mv') or 'N/D'} mV")

    print()
    info("Query Flux para ver los puntos en InfluxDB Data Explorer:")
    info('  from(bucket: "agrocollective")')
    info('    |> range(start: -1h)')
    info('    |> filter(fn: (r) => r._measurement == "measurements")')
    if hash_plot != "N/D":
        info(f'    |> filter(fn: (r) => r.hash_plot == "{hash_plot}")')


# =============================================================================
# Menú principal
# =============================================================================

MENU = """
  ┌─────────────────────────────────────────────────┐
  │  1 │ Crear usuario + setup completo + publicar  │
  │  2 │ Login y publicar (crea lo que falte)       │
  │  3 │ Login y leer últimos datos del dispositivo │
  │  4 │ Salir                                      │
  └─────────────────────────────────────────────────┘"""


def main() -> None:
    header("AgroCollective - Test MQTT interactivo (Fases 1 + 2)")
    info(f"API : {API_BASE_URL}")
    info(f"MQTT: {MQTT_HOST}:{MQTT_PORT}")

    while True:
        print(MENU)
        opcion = input("\n  Elige una opción: ").strip()

        if opcion == "1":
            header("Opción 1: Setup completo + publicar")
            with httpx.Client(timeout=10.0) as client:
                do_register(client)
                token = do_login(client)
                client.headers["Authorization"] = f"Bearer {token}"
                ensure_setup(client)
            do_publish()

        elif opcion == "2":
            header("Opción 2: Login y publicar")
            with httpx.Client(timeout=10.0) as client:
                token = do_login(client)
                client.headers["Authorization"] = f"Bearer {token}"
                ensure_setup(client)
            do_publish()

        elif opcion == "3":
            header("Opción 3: Login y leer datos")
            with httpx.Client(timeout=10.0) as client:
                token = do_login(client)
                client.headers["Authorization"] = f"Bearer {token}"
                do_read(client)

        elif opcion == "4":
            print("\n  Hasta luego.\n")
            break

        else:
            warn("Opción no válida. Elige 1, 2, 3 o 4.")


if __name__ == "__main__":
    main()
