"""Designations router — federal health designations (HRSA MUA/P).

The product question this answers is: "For a given municipio, what federal
designations apply, and how severe are they?"
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.database import DbSession

router = APIRouter()


class DesignationPublic(BaseModel):
    """One federal designation on a municipio."""

    external_id: str
    designation_code: str
    designation_name: str
    population_type: str | None
    imu_score: float | None
    status_code: str | None
    status_description: str | None
    designation_date: date | None
    rural_status: str | None
    designated_population: int | None
    is_active: bool


class MuniDesignations(BaseModel):
    """All designations for one muni."""

    muni_id: str
    muni_name: str
    designations: list[DesignationPublic]


class DesignationSummary(BaseModel):
    """Island-wide designation rollup for the homepage stat card."""

    total_munis: int
    designated_munis: int
    percentage_designated: float
    min_imu_score: float | None
    max_imu_score: float | None
    mean_imu_score: float | None
    earliest_designation: date | None
    counts_by_type: dict[str, int]
    counts_by_rural_status: dict[str, int]
    source_slug: str
    last_updated: datetime | None


@router.get("/designations/summary", response_model=DesignationSummary)
def get_summary(db: DbSession) -> DesignationSummary:
    """High-level rollup of designations across all of PR.

    Powers the stat card on the homepage ("72 de 78 municipios...").
    """
    totals = db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM municipalities) AS total_munis,
                (SELECT COUNT(DISTINCT md.muni_id)
                   FROM muni_designations md
                  WHERE md.status_code = 'D'
                    AND md.withdrawal_date IS NULL) AS designated_munis,
                MIN(md.imu_score) AS min_imu,
                MAX(md.imu_score) AS max_imu,
                AVG(md.imu_score) AS mean_imu,
                MIN(md.designation_date) AS earliest,
                MAX(md.updated_at) AS last_updated
            FROM muni_designations md
            WHERE md.status_code = 'D' AND md.withdrawal_date IS NULL
            """
        )
    ).one()

    by_type_rows = db.execute(
        text(
            """
            SELECT designation_code, COUNT(*) AS n
            FROM muni_designations
            WHERE status_code = 'D' AND withdrawal_date IS NULL
            GROUP BY designation_code
            """
        )
    ).all()

    by_rural_rows = db.execute(
        text(
            """
            SELECT COALESCE(rural_status, 'Desconocido') AS rural, COUNT(*) AS n
            FROM muni_designations
            WHERE status_code = 'D' AND withdrawal_date IS NULL
            GROUP BY rural_status
            """
        )
    ).all()

    source_slug_row = db.execute(
        text(
            """
            SELECT ds.slug
            FROM data_sources ds
            JOIN muni_designations md ON md.source_id = ds.id
            GROUP BY ds.slug
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """
        )
    ).first()

    total = int(totals.total_munis or 0)
    designated = int(totals.designated_munis or 0)
    pct = (designated / total * 100) if total else 0.0

    def _to_f(v: Decimal | None) -> float | None:
        return float(v) if v is not None else None

    return DesignationSummary(
        total_munis=total,
        designated_munis=designated,
        percentage_designated=round(pct, 1),
        min_imu_score=_to_f(totals.min_imu),
        max_imu_score=_to_f(totals.max_imu),
        mean_imu_score=_to_f(totals.mean_imu),
        earliest_designation=totals.earliest,
        counts_by_type={r.designation_code: int(r.n) for r in by_type_rows},
        counts_by_rural_status={r.rural: int(r.n) for r in by_rural_rows},
        source_slug=source_slug_row.slug if source_slug_row else "hrsa_mua",
        last_updated=totals.last_updated,
    )


@router.get(
    "/designations/by-muni/{muni_id}", response_model=MuniDesignations
)
def get_by_muni(muni_id: str, db: DbSession) -> MuniDesignations:
    """All designations for a single muni. Multiple designations are possible."""
    muni = db.execute(
        text("SELECT id, name FROM municipalities WHERE id = :id"),
        {"id": muni_id},
    ).first()
    if not muni:
        raise HTTPException(status_code=404, detail=f"Muni '{muni_id}' not found")

    rows = db.execute(
        text(
            """
            SELECT
                external_id, designation_code, designation_name,
                population_type, imu_score, status_code, status_description,
                designation_date, rural_status, designated_population,
                withdrawal_date
            FROM muni_designations
            WHERE muni_id = :muni
            ORDER BY designation_date DESC NULLS LAST, external_id
            """
        ),
        {"muni": muni_id},
    ).all()

    designations = [
        DesignationPublic(
            external_id=r.external_id,
            designation_code=r.designation_code,
            designation_name=r.designation_name,
            population_type=r.population_type,
            imu_score=float(r.imu_score) if r.imu_score is not None else None,
            status_code=r.status_code,
            status_description=r.status_description,
            designation_date=r.designation_date,
            rural_status=r.rural_status,
            designated_population=r.designated_population,
            is_active=(r.status_code == "D" and r.withdrawal_date is None),
        )
        for r in rows
    ]

    return MuniDesignations(
        muni_id=muni.id, muni_name=muni.name, designations=designations
    )
