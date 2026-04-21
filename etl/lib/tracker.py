"""Track ETL pipeline executions in the `etl_runs` provenance table.

Usage:
    with EtlRunTracker(source_slug="prdoh_municipalities") as run:
        # ... do work ...
        run.rows_read = 78
        run.rows_upserted = 78
    # On exit: status + finished_at + counts are written automatically.
"""

from __future__ import annotations

import subprocess
import traceback
from datetime import datetime, timezone
from types import TracebackType

from sqlalchemy import text

from lib.db import session_scope
from lib.logging import get_logger

log = get_logger(__name__)


def _git_sha() -> str | None:
    """Return current git SHA (short), or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return result.stdout.strip()[:40]
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


class EtlRunTracker:
    """Context manager that records an etl_runs row.

    Automatically sets status to 'success' or 'failed' based on whether an
    exception propagated through the context.
    """

    def __init__(self, source_slug: str) -> None:
        self.source_slug = source_slug
        self.run_id: int | None = None
        self.source_id: int | None = None
        self.rows_read: int = 0
        self.rows_upserted: int = 0
        self.rows_skipped: int = 0

    def __enter__(self) -> "EtlRunTracker":
        with session_scope() as s:
            row = s.execute(
                text("SELECT id FROM data_sources WHERE slug = :slug"),
                {"slug": self.source_slug},
            ).first()
            if row is None:
                raise RuntimeError(
                    f"data_sources row not found for slug='{self.source_slug}'. "
                    f"Run: uv run python scripts/seed_data_sources.py"
                )
            self.source_id = int(row[0])

            result = s.execute(
                text(
                    """
                    INSERT INTO etl_runs (source_id, started_at, status, git_sha)
                    VALUES (:source_id, :started_at, 'running', :git_sha)
                    RETURNING id
                    """
                ),
                {
                    "source_id": self.source_id,
                    "started_at": datetime.now(timezone.utc),
                    "git_sha": _git_sha(),
                },
            )
            self.run_id = int(result.scalar_one())
        log.info(
            "Started ETL run id=%s source=%s",
            self.run_id,
            self.source_slug,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        status = "success" if exc_type is None else "failed"
        error_message = None
        if exc_val is not None:
            error_message = "".join(
                traceback.format_exception(exc_type, exc_val, exc_tb)
            )[:4000]

        with session_scope() as s:
            s.execute(
                text(
                    """
                    UPDATE etl_runs
                    SET finished_at = :finished_at,
                        status = :status,
                        rows_read = :rows_read,
                        rows_upserted = :rows_upserted,
                        rows_skipped = :rows_skipped,
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {
                    "id": self.run_id,
                    "finished_at": datetime.now(timezone.utc),
                    "status": status,
                    "rows_read": self.rows_read,
                    "rows_upserted": self.rows_upserted,
                    "rows_skipped": self.rows_skipped,
                    "error_message": error_message,
                },
            )
            # Touch last_pulled_at on the source row (only on success)
            if status == "success":
                s.execute(
                    text(
                        "UPDATE data_sources SET last_pulled_at = :now WHERE id = :id"
                    ),
                    {"now": datetime.now(timezone.utc), "id": self.source_id},
                )
        log.info(
            "Finished ETL run id=%s status=%s read=%d upserted=%d skipped=%d",
            self.run_id,
            status,
            self.rows_read,
            self.rows_upserted,
            self.rows_skipped,
        )
