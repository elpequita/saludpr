"""MuniDesignation — federal health designations at the municipio level.

Currently tracks HRSA MUA/P (Medically Underserved Area/Population) designations.
Schema is extensible to future HPSA (Health Professional Shortage Area) data
without migration changes.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
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


class MuniDesignation(Base):
    """A federal health designation attached to a municipio.

    One muni can have multiple simultaneous designations (e.g. both an MUA
    and a separate MUP for low-income population). Each row represents one
    designation, uniquely identified by (external_id, source_id).
    """

    __tablename__ = "muni_designations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # External natural key — HRSA's MUA/P ID (e.g. "03920")
    external_id: Mapped[str] = mapped_column(Text, nullable=False)

    muni_id: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("municipalities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Designation metadata
    designation_code: Mapped[str] = mapped_column(String(16), nullable=False)
    designation_name: Mapped[str] = mapped_column(Text, nullable=False)
    population_type_code: Mapped[str | None] = mapped_column(String(16))
    population_type: Mapped[str | None] = mapped_column(Text)

    # Severity / status
    imu_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status_code: Mapped[str | None] = mapped_column(String(2))
    status_description: Mapped[str | None] = mapped_column(Text)

    # Timeline
    designation_date: Mapped[date | None] = mapped_column(Date)
    update_date: Mapped[date | None] = mapped_column(Date)
    withdrawal_date: Mapped[date | None] = mapped_column(Date)
    break_in_designation: Mapped[bool | None] = mapped_column(Boolean)

    # Context
    rural_status_code: Mapped[str | None] = mapped_column(String(2))
    rural_status: Mapped[str | None] = mapped_column(Text)
    designated_population: Mapped[int | None] = mapped_column(Integer)
    service_area_name: Mapped[str | None] = mapped_column(Text)

    # Provenance
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
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    muni: Mapped["Municipality"] = relationship()
    source: Mapped["DataSource"] = relationship()
    etl_run: Mapped["EtlRun | None"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "external_id", "source_id", name="uq_muni_designations_external"
        ),
        CheckConstraint(
            "imu_score IS NULL OR (imu_score >= 0 AND imu_score <= 100)",
            name="ck_muni_designations_imu_range",
        ),
        Index("ix_muni_designations_muni", "muni_id"),
        Index("ix_muni_designations_code", "designation_code", "status_code"),
    )

    @property
    def is_active(self) -> bool:
        """True if this designation is currently in force."""
        return self.status_code == "D" and self.withdrawal_date is None

    def __repr__(self) -> str:
        return (
            f"<MuniDesignation {self.designation_code} "
            f"muni={self.muni_id} imu={self.imu_score}>"
        )
