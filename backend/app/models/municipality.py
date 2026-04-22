"""Municipality model — the 78 official Puerto Rico municipios."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.barrio import Barrio
    from app.models.health_metric import HealthMetric
    from app.models.hospital import Hospital
    from app.models.vulnerability import Vulnerability


class Municipality(Base):
    """A Puerto Rico municipality (municipio)."""

    __tablename__ = "municipalities"

    # PR municipality FIPS-style code, e.g. "72127" for San Juan.
    id: Mapped[str] = mapped_column(String(5), primary_key=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(Text)

    # WGS84 boundary polygon
    geometry: Mapped[bytes] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )
    # Computed centroid — used for map labels & nearest-hospital queries
    centroid: Mapped[bytes | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
    )

    area_sq_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    population_latest: Mapped[int | None] = mapped_column(Integer)
    population_year: Mapped[int | None] = mapped_column(SmallInteger)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    health_metrics: Mapped[list["HealthMetric"]] = relationship(
        back_populates="municipality",
        cascade="all, delete-orphan",
    )
    hospitals: Mapped[list["Hospital"]] = relationship(
        back_populates="municipality",
        cascade="all, delete-orphan",
    )
    vulnerability_records: Mapped[list["Vulnerability"]] = relationship(
        back_populates="municipality",
        cascade="all, delete-orphan",
    )
    barrios: Mapped[list["Barrio"]] = relationship(
        back_populates="municipality",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_municipalities_geometry", "geometry", postgresql_using="gist"),
        Index("ix_municipalities_centroid", "centroid", postgresql_using="gist"),
        Index("ix_municipalities_name_normalized", "name_normalized"),
    )

    def __repr__(self) -> str:
        return f"<Municipality {self.id} {self.name}>"
