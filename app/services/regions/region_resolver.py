"""
Resolucion de la region SiAR de referencia para una finca.

Usado por el endpoint /plots/{id}/weather y por el publicador de
telemetria en vivo (scripts/live_sensor_publisher.py). El formulario
de alta de finca permite elegir region, pero es opcional: si la finca
no tiene una asignada, se usa la region con estacion SiAR mas cercana
por latitud/longitud.
"""

from app.models.farm import Farm
from app.models.region import Region


def nearest_region(farm: Farm, regions: list[Region]) -> Region | None:
    """Region mas cercana a la finca por distancia euclidiana lat/lon. Pura, sin acceso a BD."""
    candidates = [r for r in regions if r.latitude is not None and r.longitude is not None]
    if not candidates:
        return regions[0] if regions else None

    if farm.latitude is None or farm.longitude is None:
        return candidates[0]

    return min(
        candidates,
        key=lambda r: (r.latitude - farm.latitude) ** 2 + (r.longitude - farm.longitude) ** 2,
    )


def resolve_region_for_farm(db, farm: Farm) -> Region | None:
    """Variante con acceso a BD para resolver una sola finca (usa la region asignada si existe)."""
    if farm.region_id:
        region = db.query(Region).filter(Region.id == farm.region_id).first()
        if region:
            return region

    return nearest_region(farm, db.query(Region).all())
