"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-21 10:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # --- data_sources ---
    op.create_table(
        "data_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("organization", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("license", sa.Text(), nullable=False),
        sa.Column("update_frequency", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_es", sa.Text(), nullable=True),
        sa.Column("known_limitations", sa.Text(), nullable=True),
        sa.Column("last_pulled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # --- municipalities ---
    op.create_table(
        "municipalities",
        sa.Column("id", sa.String(length=5), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalized", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "centroid",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("area_sq_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("population_latest", sa.Integer(), nullable=True),
        sa.Column("population_year", sa.SmallInteger(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_municipalities_geometry",
        "municipalities",
        ["geometry"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_municipalities_centroid",
        "municipalities",
        ["centroid"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_municipalities_name_normalized",
        "municipalities",
        ["name_normalized"],
    )

    # --- etl_runs ---
    op.create_table(
        "etl_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("rows_read", sa.Integer(), nullable=True),
        sa.Column("rows_upserted", sa.Integer(), nullable=True),
        sa.Column("rows_skipped", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"], ["data_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_etl_runs_source_started",
        "etl_runs",
        ["source_id", "started_at"],
    )

    # --- health_metrics ---
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("muni_id", sa.String(length=5), nullable=False),
        sa.Column("indicator_code", sa.Text(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("value_type", sa.Text(), nullable=False),
        sa.Column("numerator", sa.Integer(), nullable=True),
        sa.Column("denominator", sa.Integer(), nullable=True),
        sa.Column("ci_lower", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("ci_upper", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("is_suppressed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_estimated", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(["muni_id"], ["municipalities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "muni_id", "indicator_code", "year", "source_id",
            name="uq_health_metrics_muni_indicator_year_source",
        ),
        sa.CheckConstraint("value IS NULL OR value >= 0", name="ck_health_metrics_value_nonneg"),
        sa.CheckConstraint(
            "ci_lower IS NULL OR ci_upper IS NULL OR ci_lower <= ci_upper",
            name="ck_health_metrics_ci_valid",
        ),
    )
    op.create_index(
        "ix_health_metrics_indicator_year",
        "health_metrics",
        ["indicator_code", "year"],
    )
    op.create_index(
        "ix_health_metrics_muni_indicator",
        "health_metrics",
        ["muni_id", "indicator_code"],
    )

    # --- hospitals ---
    op.create_table(
        "hospitals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("muni_id", sa.String(length=5), nullable=False),
        sa.Column("facility_type", sa.Text(), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("total_beds", sa.Integer(), nullable=True),
        sa.Column("staffed_beds", sa.Integer(), nullable=True),
        sa.Column("has_emergency_dept", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(["muni_id"], ["municipalities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", "source_id", name="uq_hospitals_external_source"),
        sa.CheckConstraint("total_beds IS NULL OR total_beds >= 0", name="ck_hospitals_beds_nonneg"),
    )
    op.create_index("ix_hospitals_location", "hospitals", ["location"], postgresql_using="gist")
    op.create_index("ix_hospitals_muni", "hospitals", ["muni_id"])

    # --- vulnerability ---
    op.create_table(
        "vulnerability",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("muni_id", sa.String(length=5), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("index_score", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("low_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("medium_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("high_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("disaster_risk_score", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("etl_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["muni_id"], ["municipalities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["etl_run_id"], ["etl_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("muni_id", "year", "source_id", name="uq_vulnerability_muni_year_source"),
        sa.CheckConstraint(
            "(low_pct IS NULL OR medium_pct IS NULL OR high_pct IS NULL) "
            "OR (low_pct + medium_pct + high_pct BETWEEN 99.0 AND 101.0)",
            name="ck_vulnerability_pct_sum",
        ),
    )

    # --- Convenience views ---
    op.execute(
        """
        CREATE OR REPLACE VIEW v_latest_metrics AS
        SELECT DISTINCT ON (muni_id, indicator_code, source_id)
            muni_id,
            indicator_code,
            year,
            value,
            value_type,
            ci_lower,
            ci_upper,
            is_suppressed,
            source_id
        FROM health_metrics
        ORDER BY muni_id, indicator_code, source_id, year DESC;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW v_source_freshness AS
        SELECT
            ds.id,
            ds.slug,
            ds.name,
            ds.last_pulled_at,
            (SELECT MAX(year) FROM health_metrics hm WHERE hm.source_id = ds.id)
                AS latest_data_year,
            (SELECT MAX(started_at) FROM etl_runs er
                WHERE er.source_id = ds.id AND er.status = 'success')
                AS latest_successful_run
        FROM data_sources ds;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_source_freshness;")
    op.execute("DROP VIEW IF EXISTS v_latest_metrics;")
    op.drop_table("vulnerability")
    op.drop_index("ix_hospitals_muni", table_name="hospitals")
    op.drop_index("ix_hospitals_location", table_name="hospitals")
    op.drop_table("hospitals")
    op.drop_index("ix_health_metrics_muni_indicator", table_name="health_metrics")
    op.drop_index("ix_health_metrics_indicator_year", table_name="health_metrics")
    op.drop_table("health_metrics")
    op.drop_index("ix_etl_runs_source_started", table_name="etl_runs")
    op.drop_table("etl_runs")
    op.drop_index("ix_municipalities_name_normalized", table_name="municipalities")
    op.drop_index("ix_municipalities_centroid", table_name="municipalities")
    op.drop_index("ix_municipalities_geometry", table_name="municipalities")
    op.drop_table("municipalities")
    op.drop_table("data_sources")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    op.execute("DROP EXTENSION IF EXISTS unaccent;")
    # Note: we do NOT drop postgis — it may be used by other DBs on the server
