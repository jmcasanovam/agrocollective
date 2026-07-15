"""
Seed de datos de catálogo para PostgreSQL.

Regiones (estaciones SiAR confirmadas, API v2.2 mayo 2025):
  VALENCIA -> V17  (Picassent, activa desde 2001)
  BAZA     -> GR01 (Baza, activa desde 2000)

Cultivos: solo leñosos mediterráneos presentes en ambas regiones.
  Excluidos: naranjo (heladas en Baza), tomate (herbáceo anual, no comparable).

Uso:
  docker compose exec backend python scripts/seed_data.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.postgres import SessionLocal
from app.models.region import Region
from app.models.crop import Crop
from app.models.soil import Soil


REGIONS = [
    {
        "code": "VALENCIA",
        "name": "Valencia",
        "siar_station_code": "V17",
        "latitude": 39.36,
        "longitude": -0.46,
    },
    {
        "code": "BAZA",
        "name": "Baza",
        "siar_station_code": "GR01",
        "latitude": 37.49,
        "longitude": -2.77,
    },
]

CROPS = [
    {"name": "olivo",   "description": "Olea europaea"},
    {"name": "almendro","description": "Prunus dulcis"},
    {"name": "vina",    "description": "Vitis vinifera"},
]

SOILS = [
    {"name": "arenoso",          "description": "Textura gruesa, alta permeabilidad"},
    {"name": "franco",           "description": "Textura equilibrada"},
    {"name": "arcilloso",        "description": "Textura fina, alta retención"},
    {"name": "franco-arenoso",   "description": "Mezcla con predominio arenoso"},
    {"name": "franco-arcilloso", "description": "Mezcla con predominio arcilloso"},
]


def _upsert(db, model, unique_field, rows):
    inserted = 0
    for row in rows:
        exists = db.query(model).filter(getattr(model, unique_field) == row[unique_field]).first()
        if not exists:
            db.add(model(**row))
            inserted += 1
    db.commit()
    return inserted


def _remove_crops(db, names):
    removed = 0
    for name in names:
        obj = db.query(Crop).filter(Crop.name == name).first()
        if obj:
            db.delete(obj)
            removed += 1
    db.commit()
    return removed


def main():
    db = SessionLocal()
    try:
        print(f"Regions:  {_upsert(db, Region, 'code', REGIONS)} nuevas")
        print(f"Crops:    {_upsert(db, Crop, 'name', CROPS)} nuevas")
        removed = _remove_crops(db, ["naranjo", "tomate"])
        if removed:
            print(f"Crops:    {removed} eliminadas (naranjo, tomate, fuera del MVP)")
        print(f"Soils:    {_upsert(db, Soil, 'name', SOILS)} nuevas")
        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
