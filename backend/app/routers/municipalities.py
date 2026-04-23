"""Municipalities router — serves the 78 PR municipios as GeoJSON.

Supports optional indicator overlay: when ?indicator=X is passed, each feature
gets a `value` property injected from the health_metrics table for the most
recent year (or the specified ?year=YYYY).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
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
def list_municipalities_geojson(
    db: DbSession,
    indicator: str | None = Query(
        None, description="Optional indicator_code to inject into each feature"
    ),
    year: int | None = Query(
        None, description="Year for the indicator (defaults to latest available)"
    ),
) -> dict[str, Any]:
    """Return all 78 municipalities as a GeoJSON FeatureCollection.

    When `indicator` is passed, each feature's properties include a `value`,
    `value_type`, `year`, `is_suppressed`, and `is_estimated` from
    health_metrics. Otherwise just geometry + name + area.
    """
    resolved_year: int | None = year

    # Special-case: imu_score is a designation attribute, not a health_metric.
    # Short-circuit the year lookup and use a dedicated query branch.
    is_imu = indicator == "imu_score"

    if indicator is not None and not is_imu and resolved_year is None:
        row = db.execute(
            text("SELECT MAX(year) FROM health_metrics WHERE indicator_code = :code"),
            {"code": indicator},
        ).first()
        if row is None or row[0] is None:
            raise HTTPException(
                status_code=404, detail=f"No data for indicator '{indicator}'"
            )
        resolved_year = int(row[0])

    if indicator is None:
        query = """
            SELECT
                m.id,
                m.name,
                m.area_sq_km,
                m.population_latest,
                ST_AsGeoJSON(ST_Simplify(m.geometry, 0.0005), 6) AS geom_json,
                NULL::numeric AS value,
                NULL::text AS value_type,
                NULL::int AS year,
                NULL::boolean AS is_suppressed,
                NULL::boolean AS is_estimated,
                d.designation_code,
                d.imu_score,
                d.designation_date
            FROM municipalities m
            LEFT JOIN v_muni_active_designations d ON d.muni_id = m.id
            ORDER BY m.name
        """
        params: dict[str, Any] = {}
    else:
        if is_imu:
            query = """
                SELECT
                    m.id,
                    m.name,
                    m.area_sq_km,
                    m.population_latest,
                    ST_AsGeoJSON(ST_Simplify(m.geometry, 0.0005), 6) AS geom_json,
                    d.imu_score AS value,
                    'imu_score'::text AS value_type,
                    EXTRACT(YEAR FROM d.designation_date)::int AS year,
                    false::boolean AS is_suppressed,
                    false::boolean AS is_estimated,
                    d.designation_code,
                    d.imu_score,
                    d.designation_date
                FROM municipalities m
                LEFT JOIN v_muni_active_designations d ON d.muni_id = m.id
                ORDER BY m.name
            """
            params = {}
        else:
            query = """
                SELECT
                    m.id,
                    m.name,
                    m.area_sq_km,
                    m.population_latest,
                    ST_AsGeoJSON(ST_Simplify(m.geometry, 0.0005), 6) AS geom_json,
                    hm.value,
                    hm.value_type,
                    hm.year,
                    hm.is_suppressed,
                    hm.is_estimated,
                    d.designation_code,
                    d.imu_score,
                    d.designation_date
                FROM municipalities m
                LEFT JOIN health_metrics hm
                    ON hm.muni_id = m.id
                    AND hm.indicator_code = :indicator
                    AND hm.year = :year
                LEFT JOIN v_muni_active_designations d ON d.muni_id = m.id
                ORDER BY m.name
            """
            params = {"indicator": indicator, "year": resolved_year}

    rows = db.execute(text(query), params).all()

    features = [
        {
            "type": "Feature",
            "id": row.id,  # surfaced at feature level so Mapbox feature-state works cleanly
            "geometry": json.loads(row.geom_json),
            "properties": {
                "id": row.id,
                "name": row.name,
                "area_sq_km": float(row.area_sq_km) if row.area_sq_km else None,
                "population_latest": row.population_latest,
                "value": float(row.value) if row.value is not None else None,
                "value_type": row.value_type,
                "year": row.year,
                "is_suppressed": row.is_suppressed,
                "is_estimated": row.is_estimated,
                "designation_code": row.designation_code,
                "imu_score": float(row.imu_score) if row.imu_score is not None else None,
                "designation_year": row.designation_date.year if row.designation_date else None,
            },
        }
        for row in rows
    ]

    return {
        "type": "FeatureCollection",
        "metadata": {
            "indicator": indicator,
            "year": resolved_year,
            "count": len(features),
        },
        "features": features,
    }


@router.get("/municipalities/summary", response_model=list[MunicipalitySummary])
def list_municipalities_summary(db: DbSession) -> list[MunicipalitySummary]:
    """Return all 78 municipalities as a compact list (no geometry)."""
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


# ---------- Slug resolver ----------


class MuniSlugMapping(BaseModel):
    """Bidirectional mapping: id (FIPS) <-> slug."""

    id: str
    slug: str
    name: str


@router.get("/municipalities-slugs", response_model=list[MuniSlugMapping])
def list_muni_slugs(db: DbSession) -> list[MuniSlugMapping]:
    """Return all 78 munis with their slugified names.

    The slug is computed in Python (not stored) so we can evolve the
    slugification rule without a migration. Used by the frontend to resolve
    /municipio/san-juan -> FIPS 72127.
    """
    rows = db.execute(
        text("SELECT id, name FROM municipalities ORDER BY name")
    ).all()
    return [
        MuniSlugMapping(id=r.id, slug=_slugify(r.name), name=r.name) for r in rows
    ]


def _slugify(name: str) -> str:
    """Convert a muni name to a URL-safe slug.

    Examples:
        'San Juan'  -> 'san-juan'
        'Loíza'     -> 'loiza'
        'Peñuelas'  -> 'penuelas'
        "Las Marías" -> 'las-marias'
    """
    import unicodedata

    # Decompose accented characters, drop the combining marks
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in normalized if not unicodedata.combining(c))
    # Lowercase, keep only alnum + space + hyphen, then collapse whitespace to hyphen
    cleaned = "".join(
        c.lower() if c.isalnum() or c in (" ", "-") else "" for c in ascii_name
    )
    return "-".join(cleaned.split())


# ---------- Detail endpoint (powers /municipio/{slug} pages) ----------


class IndicatorYearValue(BaseModel):
    year: int
    value: float | None


class MuniIndicatorSeries(BaseModel):
    """One indicator's 5-year series for this muni, with context."""

    code: str
    value_type: str | None
    values: list[IndicatorYearValue]
    latest_year: int | None
    latest_value: float | None
    source_slug: str | None


class MuniDesignationSummary(BaseModel):
    """Active federal designation on this muni, if any."""

    designation_code: str
    designation_name: str
    imu_score: float | None
    designation_year: int | None
    rural_status: str | None


class BarrioRankEntry(BaseModel):
    """One barrio in a top/bottom ranking."""

    id: str
    name: str
    value: float | None
    population_latest: int | None


class BarrioRanking(BaseModel):
    """Top and bottom 3 barrios for the default indicator."""

    indicator_code: str
    direction: str  # 'worst_first' or 'best_first' — depends on high_is_bad/good
    year: int | None
    top: list[BarrioRankEntry]
    bottom: list[BarrioRankEntry]


class SimilarMuni(BaseModel):
    id: str
    name: str
    population_latest: int | None
    population_diff_pct: float


class MuniDetail(BaseModel):
    """Everything the /municipio/{slug} page needs in one round-trip."""

    id: str
    name: str
    area_sq_km: float | None
    population_latest: int | None
    designation: MuniDesignationSummary | None
    indicators: list[MuniIndicatorSeries]
    barrio_ranking: BarrioRanking | None
    similar_munis: list[SimilarMuni]


# Indicators we'll return with 5-year series. Order matters — it's the display order.
_DETAIL_INDICATORS = [
    "pct_below_poverty",
    "pct_uninsured",
    "pct_bachelors_or_higher",
    "pct_no_high_school",
    "pct_overcrowded_housing",
    "median_household_income",
    "pct_age_65_plus",
    "pct_under_18",
    "median_age",
    "total_population",
]

# Indicators where HIGHER values are worse (for ranking direction)
_HIGH_IS_BAD = {
    "pct_below_poverty",
    "pct_uninsured",
    "pct_no_high_school",
    "pct_overcrowded_housing",
}


@router.get("/municipalities/{muni_id}/detail", response_model=MuniDetail)
def get_municipality_detail(muni_id: str, db: DbSession) -> MuniDetail:
    """Return all data needed for the /municipio/{slug} page in one round-trip.

    Includes base municipality info, active HRSA designation (if any),
    10 SDOH indicators with 5-year trends, top/bottom barrios for the default
    indicator, and 4 similar munis by population.
    """
    # 1. Base muni
    base = db.execute(
        text(
            """
            SELECT id, name, area_sq_km, population_latest
            FROM municipalities
            WHERE id = :muni_id
            """
        ),
        {"muni_id": muni_id},
    ).first()
    if base is None:
        raise HTTPException(
            status_code=404, detail=f"Municipality '{muni_id}' not found"
        )

    # 2. Active designation (if any)
    desig_row = db.execute(
        text(
            """
            SELECT designation_code, designation_name, imu_score,
                   designation_date, rural_status
            FROM v_muni_active_designations
            WHERE muni_id = :muni_id
            LIMIT 1
            """
        ),
        {"muni_id": muni_id},
    ).first()
    designation = (
        MuniDesignationSummary(
            designation_code=desig_row.designation_code,
            designation_name=desig_row.designation_name,
            imu_score=float(desig_row.imu_score)
            if desig_row.imu_score is not None
            else None,
            designation_year=desig_row.designation_date.year
            if desig_row.designation_date
            else None,
            rural_status=desig_row.rural_status,
        )
        if desig_row
        else None
    )

    # 3. Indicator series (all 5 years for all 10 indicators, one query)
    series_rows = db.execute(
        text(
            """
            SELECT
                hm.indicator_code,
                hm.year,
                hm.value,
                hm.value_type,
                ds.slug AS source_slug
            FROM health_metrics hm
            JOIN data_sources ds ON ds.id = hm.source_id
            WHERE hm.muni_id = :muni_id
              AND hm.indicator_code = ANY(:codes)
            ORDER BY hm.indicator_code, hm.year
            """
        ),
        {"muni_id": muni_id, "codes": _DETAIL_INDICATORS},
    ).all()

    # Group by indicator_code
    from collections import defaultdict

    by_code: dict[str, list] = defaultdict(list)
    value_type_by_code: dict[str, str | None] = {}
    source_by_code: dict[str, str | None] = {}
    for r in series_rows:
        by_code[r.indicator_code].append((int(r.year), r.value))
        value_type_by_code[r.indicator_code] = r.value_type
        source_by_code[r.indicator_code] = r.source_slug

    indicators: list[MuniIndicatorSeries] = []
    for code in _DETAIL_INDICATORS:
        points = by_code.get(code, [])
        values = [
            IndicatorYearValue(
                year=yr, value=float(v) if v is not None else None
            )
            for yr, v in points
        ]
        # Latest value = most recent year where value is not null
        latest_year: int | None = None
        latest_value: float | None = None
        for yr, v in reversed(points):
            if v is not None:
                latest_year = yr
                latest_value = float(v)
                break

        indicators.append(
            MuniIndicatorSeries(
                code=code,
                value_type=value_type_by_code.get(code),
                values=values,
                latest_year=latest_year,
                latest_value=latest_value,
                source_slug=source_by_code.get(code),
            )
        )

    # 4. Barrio ranking for pct_below_poverty (default ranking indicator)
    #    Top = worst, Bottom = best (since poverty is high_is_bad)
    ranking_indicator = "pct_below_poverty"
    direction = "worst_first" if ranking_indicator in _HIGH_IS_BAD else "best_first"

    barrio_year_row = db.execute(
        text(
            """
            SELECT MAX(year) AS y FROM barrio_health_metrics bhm
            JOIN barrios b ON b.id = bhm.barrio_id
            WHERE b.muni_id = :muni_id AND bhm.indicator_code = :code
            """
        ),
        {"muni_id": muni_id, "code": ranking_indicator},
    ).first()
    ranking_year = int(barrio_year_row.y) if barrio_year_row and barrio_year_row.y else None

    barrio_ranking: BarrioRanking | None = None
    if ranking_year:
        # Only include barrios with population >= 1000 for statistical reliability
        barrio_rows = db.execute(
            text(
                """
                SELECT b.id, b.name, bhm.value, b.population_latest
                FROM barrios b
                JOIN barrio_health_metrics bhm ON bhm.barrio_id = b.id
                WHERE b.muni_id = :muni_id
                  AND bhm.indicator_code = :code
                  AND bhm.year = :year
                  AND bhm.value IS NOT NULL
                  AND (b.population_latest IS NULL OR b.population_latest >= 1000)
                ORDER BY bhm.value
                """
            ),
            {
                "muni_id": muni_id,
                "code": ranking_indicator,
                "year": ranking_year,
            },
        ).all()

        def _mk(r) -> BarrioRankEntry:
            return BarrioRankEntry(
                id=r.id,
                name=r.name,
                value=float(r.value) if r.value is not None else None,
                population_latest=r.population_latest,
            )

        # Ordered ascending by value; for worst_first (poverty), top=end (highest), bottom=start (lowest)
        if direction == "worst_first":
            top = [_mk(r) for r in list(reversed(barrio_rows))[:3]]
            bottom = [_mk(r) for r in barrio_rows[:3]]
        else:
            top = [_mk(r) for r in list(reversed(barrio_rows))[:3]]
            bottom = [_mk(r) for r in barrio_rows[:3]]

        barrio_ranking = BarrioRanking(
            indicator_code=ranking_indicator,
            direction=direction,
            year=ranking_year,
            top=top,
            bottom=bottom,
        )

    # 5. Similar munis by population (±30% band, closest 4)
    similar: list[SimilarMuni] = []
    if base.population_latest:
        sim_rows = db.execute(
            text(
                """
                SELECT id, name, population_latest,
                       ABS(population_latest - :pop)::float AS pop_diff,
                       ABS(population_latest - :pop)::float / NULLIF(:pop, 0) AS pop_diff_frac
                FROM municipalities
                WHERE id != :muni_id
                  AND population_latest IS NOT NULL
                ORDER BY pop_diff
                LIMIT 4
                """
            ),
            {"muni_id": muni_id, "pop": base.population_latest},
        ).all()
        for r in sim_rows:
            similar.append(
                SimilarMuni(
                    id=r.id,
                    name=r.name,
                    population_latest=r.population_latest,
                    population_diff_pct=round((r.pop_diff_frac or 0) * 100, 1),
                )
            )

    return MuniDetail(
        id=base.id,
        name=base.name,
        area_sq_km=float(base.area_sq_km) if base.area_sq_km else None,
        population_latest=base.population_latest,
        designation=designation,
        indicators=indicators,
        barrio_ranking=barrio_ranking,
        similar_munis=similar,
    )
