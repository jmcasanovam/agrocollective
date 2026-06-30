"""
Script de simulación de sensores IoT para AgroCollective.

Genera lecturas artificiales con coherencia agronómica y las envía
al broker MQTT, imitando el comportamiento de dispositivos ESP32 reales.

Uso:
    python scripts/simulate_sensors.py                    # usa valores por defecto
    python scripts/simulate_sensors.py --realtime         # espera el intervalo real entre envíos
    python scripts/simulate_sensors.py --dry-run          # solo imprime, no envía

Requisitos:
    pip install paho-mqtt
    El broker Mosquitto debe estar accesible (ajusta MQTT_HOST/MQTT_PORT abajo).
"""

import argparse
import json
import math
import random
import time
from datetime import datetime, timedelta, timezone

import paho.mqtt.publish as mqtt_publish

# =============================================================================
# VARIABLES DE CONFIGURACIÓN — edita aquí
# =============================================================================

MQTT_HOST = "localhost"          # host del broker (fuera de Docker usa localhost)
MQTT_PORT = 1883

# Número de parcelas a simular
N_PLOTS = 10

# Ventana temporal de simulación
START_TIME = datetime(2026, 6, 30, 8, 0, 0, tzinfo=timezone.utc)   # inicio
END_TIME   = datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc)  # fin (excluido)

# Intervalo entre mediciones de cada dispositivo (minutos)
INTERVAL_MINUTES = 15

# Prefijo del código de dispositivo. Se generarán AGRO-P01-001 ... AGRO-P10-001
DEVICE_PREFIX = "AGRO-P"

# Pausa en segundos entre mensajes cuando NO se usa --realtime
# (0 = tan rápido como sea posible)
SEND_DELAY_SECONDS = 0.05

# =============================================================================
# RANGOS DE VARIABLES POR PERFIL DE PARCELA
# Cada parcela se asigna aleatoriamente a uno de estos perfiles al inicio.
# Dentro del rango, el valor oscila con ruido gaussiano entre mediciones.
# =============================================================================

PROFILES = {
    "seco_eficiente": {
        # Poco riego, buena eficiencia
        "soil_humidity":  (30.0, 45.0),
        "air_temp":       (16.0, 22.0),
        "soil_temp":      (14.0, 20.0),
        "air_humidity":   (65.0, 78.0),
        "battery_mv":     (3600, 3900),
    },
    "moderado": {
        "soil_humidity":  (42.0, 58.0),
        "air_temp":       (18.0, 25.0),
        "soil_temp":      (16.0, 23.0),
        "air_humidity":   (60.0, 75.0),
        "battery_mv":     (3500, 3850),
    },
    "humedo_intensivo": {
        # Mucho riego, baja eficiencia → tendencia anómala
        "soil_humidity":  (60.0, 85.0),
        "air_temp":       (19.0, 27.0),
        "soil_temp":      (17.0, 25.0),
        "air_humidity":   (55.0, 70.0),
        "battery_mv":     (3400, 3800),
    },
}

# Distribución de perfiles (reproducible con seed)
PROFILE_DISTRIBUTION = [
    "seco_eficiente",   # P01
    "moderado",         # P02
    "moderado",         # P03
    "seco_eficiente",   # P04
    "humedo_intensivo", # P05
    "moderado",         # P06
    "seco_eficiente",   # P07
    "humedo_intensivo", # P08
    "moderado",         # P09
    "humedo_intensivo", # P10 ← anómala más probable
]

# Amplitud del ruido gaussiano como fracción del rango de cada variable
NOISE_FRACTION = 0.04

# Probabilidad de que una medición tenga un "pico" (evento de riego, rafaga de calor…)
SPIKE_PROBABILITY = 0.03

# =============================================================================
# LÓGICA DE GENERACIÓN
# =============================================================================


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _noisy(lo: float, hi: float, prev: float | None, noise_frac: float) -> float:
    """Valor dentro de [lo, hi] con ruido gaussiano alrededor del previo."""
    center = prev if prev is not None else (lo + hi) / 2
    sigma = (hi - lo) * noise_frac
    new_val = random.gauss(center, sigma)
    return round(_clamp(new_val, lo, hi), 2)


def _diurnal_offset(timestamp: datetime, variable: str) -> float:
    """Variación sinusoidal diurna (temperatura sube al mediodía, humedad baja)."""
    hour = timestamp.hour + timestamp.minute / 60
    # Temperatura: mínimo a las 6h, máximo a las 14h
    if "temp" in variable:
        return 2.0 * math.sin(math.pi * (hour - 6) / 8)
    # Humedad: inverso
    if "humidity" in variable:
        return -3.0 * math.sin(math.pi * (hour - 6) / 8)
    return 0.0


class SensorSimulator:

    def __init__(self, plot_index: int, seed: int | None = None):
        self.plot_index = plot_index
        self.device_code = f"{DEVICE_PREFIX}{plot_index:02d}-001"
        profile_name = PROFILE_DISTRIBUTION[plot_index % len(PROFILE_DISTRIBUTION)]
        self.profile = PROFILES[profile_name]
        self.profile_name = profile_name
        self.prev: dict[str, float | None] = {k: None for k in self.profile}

    def next_reading(self, timestamp: datetime) -> dict:
        measures = {}
        for field in ("soil_humidity", "air_temp", "soil_temp", "air_humidity"):
            lo, hi = self.profile[field]
            offset = _diurnal_offset(timestamp, field)
            lo_adj = _clamp(lo + offset, lo - 2, hi)
            hi_adj = _clamp(hi + offset, lo, hi + 2)
            val = _noisy(lo_adj, hi_adj, self.prev.get(field), NOISE_FRACTION)

            # Spike aleatorio (riego súbito, ráfaga de viento…)
            if random.random() < SPIKE_PROBABILITY and field == "soil_humidity":
                val = round(_clamp(val + random.uniform(10, 20), lo, hi + 15), 2)

            self.prev[field] = val
            measures[field] = val

        battery_lo, battery_hi = self.profile["battery_mv"]
        battery = int(random.uniform(battery_lo, battery_hi))

        return {
            "device_id": self.device_code,
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "battery_mv": battery,
            "measures": {
                "soil_humidity": measures["soil_humidity"],
                "air_temp":      measures["air_temp"],
                "soil_temp":     measures["soil_temp"],
                "air_humidity":  measures["air_humidity"],
            },
        }


# =============================================================================
# ENVÍO MQTT
# =============================================================================


def send_message(payload: dict, dry_run: bool) -> None:
    topic = f"devices/{payload['device_id']}/readings"
    body = json.dumps(payload)
    if dry_run:
        print(f"  [DRY-RUN] {topic} -> {body}")
        return
    try:
        mqtt_publish.single(topic, body, hostname=MQTT_HOST, port=MQTT_PORT)
    except Exception as exc:
        print(f"  [ERROR] {topic}: {exc}")


# =============================================================================
# MAIN
# =============================================================================


def build_timestamps() -> list[datetime]:
    ts = START_TIME
    result = []
    while ts < END_TIME:
        result.append(ts)
        ts += timedelta(minutes=INTERVAL_MINUTES)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de sensores AgroCollective")
    parser.add_argument("--realtime", action="store_true",
                        help="Espera INTERVAL_MINUTES reales entre ciclos")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo imprime los mensajes, no los envía")
    parser.add_argument("--seed", type=int, default=42,
                        help="Semilla aleatoria para reproducibilidad (default: 42)")
    args = parser.parse_args()

    random.seed(args.seed)

    simulators = [SensorSimulator(i) for i in range(N_PLOTS)]
    timestamps = build_timestamps()

    total_messages = len(simulators) * len(timestamps)
    print(f"\n=== AgroCollective — Simulador de sensores ===")
    print(f"  Parcelas:    {N_PLOTS}")
    print(f"  Inicio:      {START_TIME.isoformat()}")
    print(f"  Fin:         {END_TIME.isoformat()}")
    print(f"  Intervalo:   {INTERVAL_MINUTES} min  ->  {len(timestamps)} ciclos")
    print(f"  Total msgs:  {total_messages}")
    print(f"  Modo:        {'REALTIME' if args.realtime else 'FAST'} | {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"  MQTT:        {MQTT_HOST}:{MQTT_PORT}")
    print()

    sent = 0
    for ts in timestamps:
        print(f"[{ts.strftime('%H:%M')}] Ciclo {ts.strftime('%Y-%m-%d %H:%M')} UTC — enviando {N_PLOTS} mensajes...")
        for sim in simulators:
            payload = sim.next_reading(ts)
            m = payload["measures"]
            print(
                f"  {sim.device_code} [{sim.profile_name:18s}] "
                f"hum={m['soil_humidity']:5.1f}% "
                f"air={m['air_temp']:4.1f}°C "
                f"bat={payload['battery_mv']}mV"
            )
            send_message(payload, args.dry_run)
            sent += 1
            if not args.realtime:
                time.sleep(SEND_DELAY_SECONDS)

        if args.realtime:
            print(f"  → Esperando {INTERVAL_MINUTES} min hasta el próximo ciclo...")
            time.sleep(INTERVAL_MINUTES * 60)

    print(f"\n=== Simulación completada: {sent}/{total_messages} mensajes enviados ===")
    for sim in simulators:
        print(
            f"  {sim.device_code} [{sim.profile_name}] "
            f"última lectura: hum={sim.prev.get('soil_humidity', '—')}% "
            f"air={sim.prev.get('air_temp', '—')}°C"
        )


if __name__ == "__main__":
    main()
