"""Hospital model — licensed healthcare facilities across PR."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.etl_run import EtlRun
    from app.models.municipality import Municipality


class Hospital(Base):
    """A licensed healthcare facility with geolocation and capacity."""

    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(Text)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    muni_id: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("municipalities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    facility_type: Mapped[str] = mapped_column(Text, nullable=False)

    location: Mapped[bytes] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    address: Mapped[str | None] = mapped_column(Text)

    total_beds: Mapped[int | None] = mapped_column(Integer)
    staffed_beds: Mapped[int | None] = mapped_column(Integer)
    has_emergency_dept: Mapped[bool | None] = mapped_column(Boolean)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    etl_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("etl_runs.id", ondelete="SET NULL"),
    )

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
    municipality: Mapped["Municipality"] = relationship(back_populates="hospitals")
    source: Mapped["DataSource"] = relationship(back_populates="hospitals")
    etl_run: Mapped["EtlRun | None"] = relationship()

    __table_args__ = (
        UniqueConstraint("external_id", "source_id", name="uq_hospitals_external_source"),
        CheckConstraint("total_beds IS NULL OR total_beds >= 0", name="ck_hospitals_beds_nonneg"),
        Index("ix_hospitals_location", "location", postgresql_using="gist"),
        Index("ix_hospitals_muni", "muni_id"),
    )

    def __repr__(self) -> str:
        return f"<Hospital {self.id} {self.name}>"
