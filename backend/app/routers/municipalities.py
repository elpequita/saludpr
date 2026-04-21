"""Municipalities router — serves the 78 PR municipios as GeoJSON."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class MunicipalitySummary(BaseModel):
    """Compact summary of a municipality (no geometry)."""

    id: str
    name: str
    area_sq_km: float | None
    population_latest: int | None


@router.get("/municipalities")
def list_municipalities_geojson(db: DbSession) -> dict[str, Any]:
    """Return all 78 municipalities as a GeoJSON FeatureCollection.

    Uses PostGIS's ST_AsGeoJSON to let the database do the heavy lifting.
    Simplified geometry (tolerance=0.0005°) for fast browser rendering —
    full-precision geometries are ~5x larger.
    """
    rows = db.execute(
        text(
            """
            SELECT
                id,
                name,
                area_sq_km,
                population_latest,
                ST_AsGeoJSON(
                    ST_Simplify(geometry, 0.0005),
                    6
                ) AS geom_json
            FROM municipalities
            ORDER BY name
            """
        )
    ).all()

    features = [
        {
            "type": "Feature",
            "geometry": json.loads(row.geom_json),
            "properties": {
                "id": row.id,
                "name": row.name,
                "area_sq_km": float(row.area_sq_km) if row.area_sq_km else None,
                "population_latest": row.population_latest,
            },
        }
        for row in rows
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/municipalities/summary", response_model=list[MunicipalitySummary])
def list_municipalities_summary(db: DbSession) -> list[MunicipalitySummary]:
    """Return all 78 municipalities as a compact list (no geometry).

    Faster than the GeoJSON endpoint — use this for dropdowns, autocomplete, etc.
    """
    rows = db.execute(
        text(
            """
            SELECT id, name, area_sq_km, population_latest
            FROM municipalities
            ORDER BY name
            """
        )
    ).all()
    return [
        MunicipalitySummary(
            id=row.id,
            name=row.name,
            area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
            population_latest=row.population_latest,
        )
        for row in rows
    ]


@router.get("/municipalities/{muni_id}", response_model=MunicipalitySummary)
def get_municipality(muni_id: str, db: DbSession) -> MunicipalitySummary:
    """Return one municipality by its 5-digit FIPS code (e.g. '72127' for San Juan)."""
    row = db.execute(
        text(
            """
            SELECT id, name, area_sq_km, population_latest
            FROM municipalities
            WHERE id = :muni_id
            """
        ),
        {"muni_id": muni_id},
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Municipality '{muni_id}' not found")

    return MunicipalitySummary(
        id=row.id,
        name=row.name,
        area_sq_km=float(row.area_sq_km) if row.area_sq_km else None,
        population_latest=row.population_latest,
    )
