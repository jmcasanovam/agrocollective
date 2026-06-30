"""
Script de setup para la prueba de simulación completa de AgroCollective.

Crea via API todo lo necesario para ejecutar el simulador y el pipeline:
  - 1 usuario de prueba
  - 1 finca con N_PLOTS parcelas
  - 1 dispositivo por parcela (con los códigos que usa simulate_sensors.py)
  - Registros de riego e historial de cosechas artificiales (para el ML)

Uso:
    python scripts/setup_simulation.py

El script es idempotente: si el usuario ya existe hace login, si la finca
ya existe la reutiliza. Ejecutar varias veces no duplica datos.

Requisitos:
    pip install httpx
"""

import httpx
import json
import random
from datetime import date, timedelta

# =============================================================================
# CONFIGURACION
# =============================================================================

API_BASE_URL = "http://localhost:8000"

# Usuario de simulacion
USER_EMAIL    = "simulacion@agrocollective.com"
USER_PASSWORD = "Simul2026!"

# Finca
FARM_NAME      = "Finca Simulacion"
FARM_LATITUDE  = 37.9922
FARM_LONGITUDE = -1.1307
FARM_AREA_HA   = 50.0

# Numero de parcelas a crear (debe coincidir con N_PLOTS en simulate_sensors.py)
N_PLOTS = 10

# IDs del catalogo (ajusta si los tuyos son distintos — ejecuta el script
# y si falla en la creacion de parcelas, copia los IDs de tu BD aqui)
CROP_IDS = [
    "28bfc727-2a0b-45e5-a615-0b4681f3a03f",  # olivo
    "ed5c9802-be51-43bf-84be-ce4fd3a075b1",  # almendro
    "c4da7803-9d30-4d31-b48c-aaa175e756d6",  # vina
]
SOIL_IDS = [
    "17f9f0f0-fd61-4f51-af1d-68576593833e",  # arenoso
    "b6b80434-67cc-4d50-9082-5b6b6923737c",  # franco
    "711336e4-e3fa-405f-82d6-c53c0bac06a9",  # arcilloso
    "2246bf5f-30a4-442a-862e-9a244ed7b179",  # franco-arenoso
    "dce6379b-542a-42f0-b6dc-b10e11ff3dfb",  # franco-arcilloso
]

# Prefijo de dispositivo (debe coincidir con DEVICE_PREFIX en simulate_sensors.py)
DEVICE_PREFIX = "AGRO-P"

# Semilla para reproducibilidad
RANDOM_SEED = 42

# =============================================================================
# Datos agropecuarios artificiales para que el ML tenga con que entrenar
# (se insertan directamente en BD via psycopg2 / o via API si existe endpoint)
# Para MVP usamos insercion directa via psql en el container
# =============================================================================

# Perfiles de riego por parcela (coincide con simulate_sensors.py PROFILE_DISTRIBUTION)
IRRIGATION_PROFILES = [
    {"freq": 2, "mm_por_riego": 30.0, "yield_kg_ha": 4200.0},  # P00 seco_eficiente
    {"freq": 3, "mm_por_riego": 45.0, "yield_kg_ha": 3800.0},  # P01 moderado
    {"freq": 3, "mm_por_riego": 44.0, "yield_kg_ha": 3750.0},  # P02 moderado
    {"freq": 2, "mm_por_riego": 31.0, "yield_kg_ha": 4150.0},  # P03 seco_eficiente
    {"freq": 5, "mm_por_riego": 55.0, "yield_kg_ha": 3200.0},  # P04 humedo_intensivo
    {"freq": 3, "mm_por_riego": 43.0, "yield_kg_ha": 3900.0},  # P05 moderado
    {"freq": 2, "mm_por_riego": 29.0, "yield_kg_ha": 4300.0},  # P06 seco_eficiente
    {"freq": 5, "mm_por_riego": 58.0, "yield_kg_ha": 3100.0},  # P07 humedo_intensivo
    {"freq": 3, "mm_por_riego": 46.0, "yield_kg_ha": 3850.0},  # P08 moderado
    {"freq": 6, "mm_por_riego": 60.0, "yield_kg_ha": 2900.0},  # P09 humedo_intensivo (anomala)
]

# =============================================================================
# Helpers
# =============================================================================

W = 62

def header(t): print(f"\n{'=' * W}\n  {t}\n{'=' * W}")
def step(t):   print(f"\n  --- {t}")
def ok(t):     print(f"  [OK]  {t}")
def info(t):   print(f"  [ ]   {t}")
def warn(t):   print(f"  [!]   {t}")

def bail(msg, r=None):
    print(f"  [ERR] {msg}")
    if r is not None:
        print(f"        Status: {r.status_code}  Body: {r.text[:400]}")
    raise SystemExit(1)

def post(client, path, body):
    r = client.post(f"{API_BASE_URL}{path}", json=body)
    return r

def get(client, path):
    r = client.get(f"{API_BASE_URL}{path}")
    return r

# =============================================================================
# PASO 1 — Usuario
# =============================================================================

def setup_user(client):
    step("Creando / verificando usuario de simulacion")
    r = post(client, "/auth/register", {"email": USER_EMAIL, "password": USER_PASSWORD})
    if r.status_code in (200, 201):
        ok(f"Usuario creado: {USER_EMAIL}")
    elif r.status_code in (400, 409, 422):
        info("Usuario ya existe, haciendo login...")
    else:
        bail("Error al registrar usuario", r)

    r = post(client, "/auth/login", {"email": USER_EMAIL, "password": USER_PASSWORD})
    if r.status_code != 200:
        bail("Login fallido", r)
    token = r.json()["access_token"]
    ok("Login correcto")
    client.headers["Authorization"] = f"Bearer {token}"
    return token

# =============================================================================
# PASO 2 — Finca
# =============================================================================

def setup_farm(client):
    step("Creando / verificando finca")
    r = get(client, "/farms")
    farms = r.json() if r.status_code == 200 else []
    existing = next((f for f in farms if f["name"] == FARM_NAME), None)
    if existing:
        ok(f"Finca existente: {existing['name']} ({existing['id']})")
        return existing["id"]

    r = post(client, "/farms", {
        "name": FARM_NAME,
        "latitude": FARM_LATITUDE,
        "longitude": FARM_LONGITUDE,
        "area_ha": FARM_AREA_HA,
    })
    if r.status_code not in (200, 201):
        bail("Error al crear finca", r)
    farm = r.json()
    ok(f"Finca creada: {farm['name']} ({farm['id']})")
    return farm["id"]

# =============================================================================
# PASO 3 — Parcelas y dispositivos
# =============================================================================

def setup_plots(client, farm_id):
    step(f"Creando {N_PLOTS} parcelas con sus dispositivos")
    random.seed(RANDOM_SEED)

    r = get(client, f"/farms/{farm_id}/plots")
    existing_plots = r.json() if r.status_code == 200 else []
    existing_names = {p["name"]: p for p in existing_plots}

    plot_ids = []
    for i in range(N_PLOTS):
        name = f"Sim-P{i:02d}"
        device_code = f"{DEVICE_PREFIX}{i:02d}-001"

        if name in existing_names:
            pid = existing_names[name]["id"]
            info(f"Parcela {name} ya existe ({pid[:8]}...)")
            plot_ids.append(pid)
            continue

        crop_id = CROP_IDS[i % len(CROP_IDS)]
        soil_id = SOIL_IDS[i % len(SOIL_IDS)]
        r = post(client, f"/farms/{farm_id}/plots", {
            "name": name,
            "crop_id": crop_id,
            "soil_id": soil_id,
            "area_ha": round(random.uniform(2.0, 8.0), 1),
        })
        if r.status_code not in (200, 201):
            bail(f"Error creando parcela {name}", r)
        plot = r.json()
        pid = plot["id"]
        plot_ids.append(pid)
        ok(f"Parcela {name} ({pid[:8]}...)")

        # Crear dispositivo asociado
        r = post(client, f"/plots/{pid}/devices", {"code": device_code, "is_active": True})
        if r.status_code not in (200, 201):
            warn(f"  Dispositivo {device_code} ya existe o error: {r.status_code}")
        else:
            ok(f"  Dispositivo {device_code} creado")

    return plot_ids

# =============================================================================
# PASO 4 — Datos historicos (riego + cosechas) via SQL directo en container
# =============================================================================

def setup_historical_data(plot_ids):
    step("Insertando registros de riego y cosechas historicos")
    import subprocess

    today = date.today()
    sqls = []

    for i, plot_id in enumerate(plot_ids):
        profile = IRRIGATION_PROFILES[i % len(IRRIGATION_PROFILES)]
        freq = profile["freq"]
        mm   = profile["mm_por_riego"]
        yld  = profile["yield_kg_ha"]

        # 8 semanas de registros de riego (freq veces por semana)
        for week_offset in range(8):
            week_start = today - timedelta(weeks=8 - week_offset)
            total_mm = round(mm * freq, 1)
            sqls.append(
                f"INSERT INTO irrigation_records (id, plot_id, week_start, irrigation_mm, created_at, updated_at) "
                f"VALUES (gen_random_uuid(), '{plot_id}', '{week_start}', {total_mm}, now(), now()) "
                f"ON CONFLICT DO NOTHING;"
            )

        # 1 cosecha reciente
        harvest_date = today - timedelta(days=30)
        water_consumed = round(mm * freq * 8 / 10000, 4)  # m3/ha aprox
        sqls.append(
            f"INSERT INTO harvests (id, plot_id, harvest_date, yield_kg_ha, water_consumed_m3_ha, created_at, updated_at) "
            f"VALUES (gen_random_uuid(), '{plot_id}', '{harvest_date}', {yld}, {water_consumed}, now(), now()) "
            f"ON CONFLICT DO NOTHING;"
        )

    sql_block = "\n".join(sqls)
    cmd = [
        "docker", "exec", "agro_postgres",
        "psql", "-U", "agro_user", "-d", "agrocollective",
        "-c", sql_block,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        warn(f"Algunos inserts fallaron (puede ser normal si ya existen): {result.stderr[:300]}")
    else:
        ok(f"{len(sqls)} registros insertados ({len(plot_ids)} x 8 semanas riego + 1 cosecha)")

# =============================================================================
# PASO 5 — Verificar
# =============================================================================

def verify(client, farm_id, plot_ids):
    step("Verificacion final")
    import subprocess

    result = subprocess.run([
        "docker", "exec", "agro_postgres",
        "psql", "-U", "agro_user", "-d", "agrocollective", "-c",
        "SELECT "
        "(SELECT count(*) FROM plots WHERE hash_plot IS NOT NULL) AS parcelas_con_hash, "
        "(SELECT count(*) FROM devices) AS dispositivos, "
        "(SELECT count(*) FROM irrigation_records) AS registros_riego, "
        "(SELECT count(*) FROM harvests) AS cosechas;",
    ], capture_output=True, text=True)
    print(result.stdout)

# =============================================================================
# MAIN
# =============================================================================

def main():
    header("AgroCollective — Setup de simulacion")
    info(f"API: {API_BASE_URL}")
    info(f"Parcelas a crear: {N_PLOTS}")

    with httpx.Client(timeout=15) as client:
        setup_user(client)
        farm_id = setup_farm(client)
        plot_ids = setup_plots(client, farm_id)

    setup_historical_data(plot_ids)
    with httpx.Client(timeout=15) as client:
        setup_user(client)  # re-login para verificacion
        verify(client, farm_id, plot_ids)

    header("Setup completado")
    info("Siguiente paso:")
    info("  python scripts/simulate_sensors.py")
    info("(o con --dry-run para verificar sin enviar)")
    print()

if __name__ == "__main__":
    main()
