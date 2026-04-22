"""BarrioHealthMetric model — indicator values at the barrio level."""

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
    from app.models.barrio import Barrio
    from app.models.data_source import DataSource
    from app.models.etl_run import EtlRun


class BarrioHealthMetric(Base):
    """A single health/SDOH indicator value for a barrio in a given year."""

    __tablename__ = "barrio_health_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    barrio_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("barrios.id", ondelete="CASCADE"),
        nullable=False,
    )
    indicator_code: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    value_type: Mapped[str] = mapped_column(Text, nullable=False)

    numerator: Mapped[int | None] = mapped_column(Integer)
    denominator: Mapped[int | None] = mapped_column(Integer)
    ci_lower: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ci_upper: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

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
    barrio: Mapped["Barrio"] = relationship(back_populates="health_metrics")
    source: Mapped["DataSource"] = relationship()
    etl_run: Mapped["EtlRun | None"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "barrio_id",
            "indicator_code",
            "year",
            "source_id",
            name="uq_bhm_barrio_indicator_year_source",
        ),
        CheckConstraint("value IS NULL OR value >= 0", name="ck_bhm_value_nonneg"),
        CheckConstraint(
            "ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper",
            name="ck_bhm_ci_valid",
        ),
        Index("ix_bhm_indicator_year", "indicator_code", "year"),
        Index("ix_bhm_barrio_indicator", "barrio_id", "indicator_code"),
    )

    def __repr__(self) -> str:
        return (
            f"<BarrioHealthMetric {self.indicator_code} "
            f"{self.barrio_id} {self.year}={self.value}>"
        )
