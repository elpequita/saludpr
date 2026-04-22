"""add territory_health_metrics for PR-wide indicators

Revision ID: 0003_territory
Revises: 0002_barrios
Create Date: 2026-04-22 16:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_territory"
down_revision: Union[str, None] = "0002_barrios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # territory_health_metrics — PR-wide values from CDC BRFSS and similar sources.
    # Distinct from health_metrics (muni-level) and barrio_health_metrics (barrio-level)
    # because the granularity is explicitly the whole territory of Puerto Rico.
    op.create_table(
        "territory_health_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "territory_id",
            sa.String(length=2),
            nullable=False,
            server_default="PR",
        ),
        sa.Column("indicator_code", sa.Text(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("value_type", sa.Text(), nullable=False),
        sa.Column("ci_lower", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ci_upper", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column(
            "is_suppressed", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "is_estimated", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("etl_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "territory_id",
            "indicator_code",
            "year",
            "source_id",
            name="uq_thm_territory_indicator_year_source",
        ),
        sa.CheckConstraint(
            "value IS NULL OR value >= 0", name="ck_thm_value_nonneg"
        ),
        sa.CheckConstraint(
            "ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper",
            name="ck_thm_ci_valid",
        ),
    )
    op.create_index(
        "ix_thm_indicator_year", "territory_health_metrics", ["indicator_code", "year"]
    )
    op.create_index(
        "ix_thm_territory_indicator",
        "territory_health_metrics",
        ["territory_id", "indicator_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_thm_territory_indicator", table_name="territory_health_metrics"
    )
    op.drop_index("ix_thm_indicator_year", table_name="territory_health_metrics")
    op.drop_table("territory_health_metrics")
