"""
Script de setup para la simulación completa de AgroCollective (Sprint 2).

Cambios respecto a Sprint 1:
  - 2 fincas con región: Finca Valencia (VALENCIA/V17) y Finca Baza (BAZA/GR01)
  - management_profile por parcela (seco_eficiente / moderado / humedo_intensivo)
  - Cosechas dentro de la ventana 2025-07-01 → 2026-06-30 según cultivo
  - Riego histórico para el año móvil completo (~52 semanas)

Uso:
    python scripts/setup_simulation.py

Idempotente: re-ejecutar no duplica datos.
"""

import httpx
import random
import subprocess
from datetime import date, timedelta

# =============================================================================
# CONFIG
# =============================================================================

API_BASE_URL  = "http://localhost:8000"
USER_EMAIL    = "simulacion@agrocollective.com"
USER_PASSWORD = "Simul2026!"
N_PLOTS       = 10
DEVICE_PREFIX = "AGRO-P"
RANDOM_SEED   = 42

# 2 fincas: P00-P04 → Valencia, P05-P09 → Baza
FARMS_DEF = [
    {
        "name":         "Finca Valencia",
        "region_code":  "VALENCIA",
        "latitude":     39.36,
        "longitude":    -0.44,
        "area_ha":      25.0,
        "plot_indices": list(range(0, 5)),
    },
    {
        "name":         "Finca Baza",
        "region_code":  "BAZA",
        "latitude":     37.49,
        "longitude":    -2.77,
        "area_ha":      25.0,
        "plot_indices": list(range(5, 10)),
    },
]

# IDs de catálogo (seed_data.py los crea con upsert; si cambian, actualizar aquí)
CROP_IDS = [
    "28bfc727-2a0b-45e5-a615-0b4681f3a03f",  # olivo    (i%3 == 0)
    "ed5c9802-be51-43bf-84be-ce4fd3a075b1",  # almendro (i%3 == 1)
    "c4da7803-9d30-4d31-b48c-aaa175e756d6",  # vina     (i%3 == 2)
]
SOIL_IDS = [
    "17f9f0f0-fd61-4f51-af1d-68576593833e",  # arenoso
    "b6b80434-67cc-4d50-9082-5b6b6923737c",  # franco
    "711336e4-e3fa-405f-82d6-c53c0bac06a9",  # arcilloso
    "2246bf5f-30a4-442a-862e-9a244ed7b179",  # franco-arenoso
    "dce6379b-542a-42f0-b6dc-b10e11ff3dfb",  # franco-arcilloso
]

# Management profile por parcela (espejo de simulate_sensors.py PROFILE_DISTRIBUTION)
MANAGEMENT_PROFILES = [
    "seco_eficiente",   # P00 Valencia
    "moderado",         # P01 Valencia
    "moderado",         # P02 Valencia
    "seco_eficiente",   # P03 Valencia
    "humedo_intensivo", # P04 Valencia
    "moderado",         # P05 Baza
    "seco_eficiente",   # P06 Baza
    "humedo_intensivo", # P07 Baza
    "moderado",         # P08 Baza
    "humedo_intensivo", # P09 Baza
]

# Riego por profile (freq veces/semana, mm/riego)
IRRIGATION_BY_PROFILE = {
    "seco_eficiente":   {"freq": 2, "mm_por_riego": 30.0, "yield_kg_ha": 4200.0},
    "moderado":         {"freq": 3, "mm_por_riego": 45.0, "yield_kg_ha": 3800.0},
    "humedo_intensivo": {"freq": 5, "mm_por_riego": 58.0, "yield_kg_ha": 3100.0},
}

# Fechas de cosecha dentro del año móvil 2025-07-01→2026-06-30 por cultivo
# crop_idx = plot_index % 3  →  0=olivo, 1=almendro, 2=vina
HARVEST_DATE_BY_CROP_IDX = {
    0: date(2025, 11, 15),  # olivo:    cosecha nov-dic
    1: date(2025, 8, 25),   # almendro: cosecha ago
    2: date(2025, 9, 25),   # vina:     cosecha sep
}

SIM_START = date(2025, 7, 1)
SIM_END   = date(2026, 6, 30)

# =============================================================================
# Helpers de consola
# =============================================================================

W = 62
def header(t): print(f"\n{'='*W}\n  {t}\n{'='*W}")
def step(t):   print(f"\n  --- {t}")
def ok(t):     print(f"  [OK]  {t}")
def info(t):   print(f"  [ ]   {t}")
def warn(t):   print(f"  [!]   {t}")

def bail(msg, r=None):
    print(f"  [ERR] {msg}")
    if r is not None:
        print(f"        Status: {r.status_code}  Body: {r.text[:400]}")
    raise SystemExit(1)

def api_post(client, path, body):
    return client.post(f"{API_BASE_URL}{path}", json=body)

def api_get(client, path):
    return client.get(f"{API_BASE_URL}{path}")

def _psql(sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "agro_postgres",
         "psql", "-U", "agro_user", "-d", "agrocollective",
         "-t", "-A", "-F", "\t", "-c", sql],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""

def _psql_rows(sql: str) -> list[list[str]]:
    out = _psql(sql)
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if parts and parts[0]:
            rows.append(parts)
    return rows

# =============================================================================
# PASO 0 — Resolver region_ids
# =============================================================================

def get_region_ids() -> dict[str, str]:
    """Returns {region_code: region_uuid}. Fails if seed_data.py no corrió."""
    rows = _psql_rows(
        "SELECT code, id::text FROM regions WHERE code IN ('VALENCIA','BAZA');"
    )
    mapping = {r[0]: r[1] for r in rows if len(r) == 2}
    if len(mapping) < 2:
        bail(
            f"Regiones VALENCIA/BAZA no encontradas en BD. "
            f"Ejecuta primero: python scripts/seed_data.py. "
            f"Encontradas: {list(mapping.keys())}"
        )
    return mapping

# =============================================================================
# PASO 1 — Usuario
# =============================================================================

def setup_user(client) -> str:
    step("Creando / verificando usuario de simulacion")
    r = api_post(client, "/auth/register", {"email": USER_EMAIL, "password": USER_PASSWORD})
    if r.status_code in (200, 201):
        ok(f"Usuario creado: {USER_EMAIL}")
    elif r.status_code in (400, 409, 422):
        info("Usuario ya existe, haciendo login...")
    else:
        bail("Error al registrar usuario", r)

    r = api_post(client, "/auth/login", {"email": USER_EMAIL, "password": USER_PASSWORD})
    if r.status_code != 200:
        bail("Login fallido", r)
    token = r.json()["access_token"]
    ok("Login correcto")
    client.headers["Authorization"] = f"Bearer {token}"
    return token

# =============================================================================
# PASO 2 — 2 Fincas con región
# =============================================================================

def setup_farms(client, region_ids: dict[str, str]) -> dict[str, str]:
    """Returns {farm_name: farm_id}."""
    step("Creando / verificando 2 fincas con región asignada")
    r = api_get(client, "/farms")
    existing = {f["name"]: f for f in (r.json() if r.status_code == 200 else [])}

    farm_ids = {}
    for farm_def in FARMS_DEF:
        name  = farm_def["name"]
        rcode = farm_def["region_code"]
        rid   = region_ids[rcode]

        if name in existing:
            fid = existing[name]["id"]
            ok(f"Finca existente: {name} / {rcode}  ({fid[:8]}...)")
        else:
            r = api_post(client, "/farms", {
                "name":      name,
                "region_id": rid,
                "latitude":  farm_def["latitude"],
                "longitude": farm_def["longitude"],
                "area_ha":   farm_def["area_ha"],
            })
            if r.status_code not in (200, 201):
                bail(f"Error al crear finca {name}", r)
            fid = r.json()["id"]
            ok(f"Finca creada: {name} / {rcode}  ({fid[:8]}...)")

        farm_ids[name] = fid
    return farm_ids

# =============================================================================
# PASO 3 — Parcelas y dispositivos
# =============================================================================

def setup_plots(
    client,
    farm_ids: dict[str, str],
    crop_ids: list[str],
    soil_ids: list[str],
) -> list[str]:
    """Returns plot_ids[0..9] indexed by plot index (None si falló)."""
    step(f"Creando {N_PLOTS} parcelas (5 por finca) con management_profile y dispositivos")
    random.seed(RANDOM_SEED)

    plot_ids: list[str | None] = [None] * N_PLOTS

    for farm_def in FARMS_DEF:
        farm_id = farm_ids[farm_def["name"]]
        r = api_get(client, f"/farms/{farm_id}/plots")
        existing = {p["name"]: p for p in (r.json() if r.status_code == 200 else [])}

        for i in farm_def["plot_indices"]:
            name        = f"Sim-P{i:02d}"
            device_code = f"{DEVICE_PREFIX}{i:02d}-001"
            profile     = MANAGEMENT_PROFILES[i]

            if name in existing:
                pid = existing[name]["id"]
                info(f"Parcela {name} ya existe ({pid[:8]}...)")
                plot_ids[i] = pid
                continue

            crop_id = crop_ids[i % len(crop_ids)]
            soil_id = soil_ids[i % len(soil_ids)]
            r = api_post(client, f"/farms/{farm_id}/plots", {
                "name":               name,
                "crop_id":            crop_id,
                "soil_id":            soil_id,
                "area_ha":            round(random.uniform(2.0, 8.0), 1),
                "management_profile": profile,
            })
            if r.status_code not in (200, 201):
                bail(f"Error creando parcela {name}", r)
            pid = r.json()["id"]
            plot_ids[i] = pid
            ok(
                f"Parcela {name}  finca={farm_def['name'][:14]}  "
                f"perfil={profile}  ({pid[:8]}...)"
            )

            r = api_post(client, f"/plots/{pid}/devices", {
                "code":      device_code,
                "is_active": True,
            })
            if r.status_code not in (200, 201):
                warn(f"  Dispositivo {device_code} ya existe o error: {r.status_code}")
            else:
                ok(f"  Dispositivo {device_code} creado")

    return plot_ids

# =============================================================================
# PASO 4 — Datos históricos: riego año móvil + cosechas por cultivo
# =============================================================================

def setup_historical_data(plot_ids: list[str | None]) -> None:
    step("Insertando riego (año móvil 2025-07-01→2026-06-30) y cosechas por cultivo")

    # Semanas dentro de la ventana
    weeks: list[date] = []
    w = SIM_START
    while w <= SIM_END:
        weeks.append(w)
        w += timedelta(weeks=1)

    sqls = []
    for i, plot_id in enumerate(plot_ids):
        if plot_id is None:
            continue

        profile   = MANAGEMENT_PROFILES[i]
        irr       = IRRIGATION_BY_PROFILE[profile]
        freq      = irr["freq"]
        mm        = irr["mm_por_riego"]
        yld       = irr["yield_kg_ha"]
        crop_idx  = i % 3

        for week_start in weeks:
            total_mm = round(mm * freq, 1)
            sqls.append(
                f"INSERT INTO irrigation_records "
                f"(id, plot_id, week_start, irrigation_mm, created_at, updated_at) "
                f"VALUES (gen_random_uuid(), '{plot_id}', '{week_start}', "
                f"{total_mm}, now(), now()) ON CONFLICT DO NOTHING;"
            )

        harvest_date   = HARVEST_DATE_BY_CROP_IDX[crop_idx]
        water_consumed = round(mm * freq * len(weeks) / 10000, 4)
        sqls.append(
            f"INSERT INTO harvests "
            f"(id, plot_id, harvest_date, yield_kg_ha, water_consumed_m3_ha, "
            f"created_at, updated_at) "
            f"VALUES (gen_random_uuid(), '{plot_id}', '{harvest_date}', "
            f"{yld}, {water_consumed}, now(), now()) ON CONFLICT DO NOTHING;"
        )

    sql_block = "\n".join(sqls)
    result = subprocess.run(
        ["docker", "exec", "agro_postgres",
         "psql", "-U", "agro_user", "-d", "agrocollective", "-c", sql_block],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        warn(f"Algunos inserts fallaron (puede ser normal si ya existen): {result.stderr[:300]}")
    else:
        active = sum(1 for p in plot_ids if p is not None)
        ok(
            f"{len(sqls)} registros  "
            f"({active} parcelas × {len(weeks)} semanas riego + 1 cosecha/parcela)"
        )

# =============================================================================
# PASO 5 — Verificar
# =============================================================================

def verify() -> None:
    step("Verificacion final")
    result = subprocess.run(
        ["docker", "exec", "agro_postgres",
         "psql", "-U", "agro_user", "-d", "agrocollective", "-c",
         "SELECT "
         "(SELECT count(*) FROM farms f "
         "  JOIN regions r ON f.region_id=r.id) AS fincas_con_region, "
         "(SELECT count(*) FROM plots "
         "  WHERE management_profile IS NOT NULL) AS parcelas_con_perfil, "
         "(SELECT count(*) FROM devices WHERE is_active=true) AS dispositivos, "
         "(SELECT count(*) FROM irrigation_records) AS registros_riego, "
         "(SELECT count(*) FROM harvests) AS cosechas, "
         "(SELECT string_agg(DISTINCT r.code, '/' ORDER BY r.code) "
         "  FROM farms f JOIN regions r ON f.region_id=r.id) AS regiones;"],
        capture_output=True, text=True,
    )
    print(result.stdout)

# =============================================================================
# MAIN
# =============================================================================

def main():
    header("AgroCollective — Setup de simulacion (Sprint 2)")
    info(f"API: {API_BASE_URL}")
    info(f"Parcelas: {N_PLOTS}  (P00-P04 → Valencia, P05-P09 → Baza)")

    region_ids = get_region_ids()
    info(f"Regiones resueltas: { {k: v[:8]+'...' for k, v in region_ids.items()} }")

    with httpx.Client(timeout=15) as client:
        setup_user(client)
        farm_ids = setup_farms(client, region_ids)
        plot_ids = setup_plots(client, farm_ids, CROP_IDS, SOIL_IDS)

    setup_historical_data(plot_ids)
    verify()

    header("Setup completado")
    info("Siguientes pasos:")
    info("  python scripts/download_siar.py   # SiAR → InfluxDB (si no está ya)")
    info("  python scripts/simulate_sensors.py")
    print()


if __name__ == "__main__":
    main()
