"""TerritoryHealthMetric model — PR-wide indicators (not muni or barrio scoped)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
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


class TerritoryHealthMetric(Base):
    """A health indicator measured at the territory (PR-wide) level.

    Used for BRFSS chronic disease rates that cannot be disaggregated to
    municipio. Kept in a separate table from muni/barrio metrics so the
    granularity semantics are self-documenting.
    """

    __tablename__ = "territory_health_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    territory_id: Mapped[str] = mapped_column(
        String(2), nullable=False, server_default="PR"
    )
    indicator_code: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    value_type: Mapped[str] = mapped_column(Text, nullable=False)

    ci_lower: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ci_upper: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sample_size: Mapped[int | None] = mapped_column(Integer)

    is_suppressed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
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
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    source: Mapped["DataSource"] = relationship()
    etl_run: Mapped["EtlRun | None"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "territory_id",
            "indicator_code",
            "year",
            "source_id",
            name="uq_thm_territory_indicator_year_source",
        ),
        CheckConstraint("value IS NULL OR value >= 0", name="ck_thm_value_nonneg"),
        CheckConstraint(
            "ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper",
            name="ck_thm_ci_valid",
        ),
        Index("ix_thm_indicator_year", "indicator_code", "year"),
        Index("ix_thm_territory_indicator", "territory_id", "indicator_code"),
    )

    def __repr__(self) -> str:
        return (
            f"<TerritoryHealthMetric {self.indicator_code} "
            f"{self.territory_id} {self.year}={self.value}>"
        )
