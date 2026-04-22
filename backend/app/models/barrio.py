"""Barrio model — sub-municipio geographic units (Census county subdivisions)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from geoalchemy2 import Geography, Geometry
from sqlalchemy import ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.barrio_health_metric import BarrioHealthMetric
    from app.models.municipality import Municipality


class Barrio(Base):
    """A Puerto Rico barrio (Census county subdivision).

    IDs are 10-digit Census GEOIDs: state(2) + county(3) + cousub(5).
    Example: "7212735560" is a barrio within San Juan municipio (72127).
    """

    __tablename__ = "barrios"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    muni_id: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("municipalities.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)

    geometry: Mapped[bytes] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )
    centroid: Mapped[bytes | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
    )

    area_sq_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    population_latest: Mapped[int | None] = mapped_column(Integer)
    population_year: Mapped[int | None] = mapped_column(SmallInteger)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    municipality: Mapped["Municipality"] = relationship(
        back_populates="barrios",
    )
    health_metrics: Mapped[list["BarrioHealthMetric"]] = relationship(
        back_populates="barrio",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_barrios_geometry", "geometry", postgresql_using="gist"),
        Index("ix_barrios_centroid", "centroid", postgresql_using="gist"),
        Index("ix_barrios_name_normalized", "name_normalized"),
        Index("ix_barrios_muni", "muni_id"),
    )

    def __repr__(self) -> str:
        return f"<Barrio {self.id} {self.name}>"
