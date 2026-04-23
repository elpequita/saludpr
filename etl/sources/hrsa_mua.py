"""Load HRSA Medically Underserved Area/Population (MUA/P) designations for Puerto Rico.

HRSA publishes a complete MUA/P detail file updated daily at:
    https://data.hrsa.gov/DataDownload/DD_Files/MUA_DET.csv

The file covers the entire US; we filter to Puerto Rico (State Abbreviation = 'PR')
and upsert into muni_designations keyed on (external_id, source_id).

Each row represents one designation. The 5-digit FIPS in the file matches our
municipalities.id column, so joining is direct.

Run:
    cd etl && uv run python -m sources.hrsa_mua
"""

from __future__ import annotations

import csv
import tempfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from lib.db import session_scope
from lib.logging import get_logger
from lib.tracker import EtlRunTracker

log = get_logger(__name__)

SOURCE_SLUG = "hrsa_mua"
CSV_URL = "https://data.hrsa.gov/DataDownload/DD_Files/MUA_DET.csv"
PR_STATE_ABBR = "PR"

# Column names in the source CSV (these are verbose but stable).
# We reference by exact header string to stay resilient to column reordering.
COL_ID = "MUA/P ID"
COL_MUNI_FIPS = "State and County Federal Information Processing Standard Code"
COL_STATE_ABBR = "State Abbreviation"
COL_DESIG_CODE = "Designation Type Code"
COL_DESIG_NAME = "Designation Type"
COL_STATUS_CODE = "MUA/P Status Code"
COL_STATUS_DESC = "MUA/P Status Description"
COL_DESIG_DATE = "Designation Date"
COL_UPDATE_DATE = "MUA/P Update Date"
COL_WITHDRAWAL_DATE = "Medically Underserved Area/Population (MUA/P) Withdrawal Date"
COL_BREAK = "Break in Designation"
COL_IMU = "IMU Score"
COL_POP_TYPE_CODE = "MUA/P Population Type Code"
COL_POP_TYPE = "Population Type"
COL_RURAL_CODE = "Rural Status Code"
COL_RURAL = "Rural Status Description"
COL_DESIGNATED_POP = "Designation Population in a Medically Underserved Area/Population (MUA/P)"
COL_SERVICE_AREA = "MUA/P Service Area Name"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _download_csv(dest: Path) -> int:
    """Download the HRSA MUA detail CSV. Returns file size in bytes."""
    log.info("Downloading HRSA MUA/P detail CSV...")
    r = requests.get(CSV_URL, timeout=120, stream=True)
    r.raise_for_status()
    total = 0
    with dest.open("wb") as fh:
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if chunk:
                fh.write(chunk)
                total += len(chunk)
    log.info("Downloaded %d bytes to %s", total, dest)
    return total


def _parse_date(raw: str | None) -> date | None:
    """HRSA dates come as MM/DD/YYYY. Empty strings mean 'not applicable'."""
    if not raw or not raw.strip():
        return None
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(raw: str | None) -> Decimal | None:
    if not raw or not raw.strip():
        return None
    try:
        return Decimal(raw.strip())
    except InvalidOperation:
        return None


def _parse_int(raw: str | None) -> int | None:
    if not raw or not raw.strip():
        return None
    try:
        return int(float(raw.strip()))
    except (ValueError, TypeError):
        return None


def _parse_break(raw: str | None) -> bool | None:
    """'Y' -> True, 'N' -> False, empty -> None."""
    if not raw:
        return None
    r = raw.strip().upper()
    if r == "Y":
        return True
    if r == "N":
        return False
    return None


def _row_to_params(
    row: dict[str, str], source_id: int, run_id: int | None
) -> dict | None:
    """Transform a raw CSV row into SQL params. Returns None if row is unusable."""
    muni_fips = (row.get(COL_MUNI_FIPS) or "").strip()
    if not muni_fips or len(muni_fips) != 5:
        return None

    external_id = (row.get(COL_ID) or "").strip()
    if not external_id:
        return None

    desig_code = (row.get(COL_DESIG_CODE) or "").strip()
    desig_name = (row.get(COL_DESIG_NAME) or "").strip()
    if not desig_code or not desig_name:
        return None

    return {
        "external_id": external_id,
        "muni_id": muni_fips,
        "designation_code": desig_code,
        "designation_name": desig_name,
        "population_type_code": (row.get(COL_POP_TYPE_CODE) or "").strip() or None,
        "population_type": (row.get(COL_POP_TYPE) or "").strip() or None,
        "imu_score": _parse_decimal(row.get(COL_IMU)),
        "status_code": (row.get(COL_STATUS_CODE) or "").strip() or None,
        "status_description": (row.get(COL_STATUS_DESC) or "").strip() or None,
        "designation_date": _parse_date(row.get(COL_DESIG_DATE)),
        "update_date": _parse_date(row.get(COL_UPDATE_DATE)),
        "withdrawal_date": _parse_date(row.get(COL_WITHDRAWAL_DATE)),
        "break_in_designation": _parse_break(row.get(COL_BREAK)),
        "rural_status_code": (row.get(COL_RURAL_CODE) or "").strip() or None,
        "rural_status": (row.get(COL_RURAL) or "").strip() or None,
        "designated_population": _parse_int(row.get(COL_DESIGNATED_POP)),
        "service_area_name": (row.get(COL_SERVICE_AREA) or "").strip() or None,
        "source_id": source_id,
        "etl_run_id": run_id,
    }


UPSERT_SQL = text(
    """
    INSERT INTO muni_designations (
        external_id, muni_id,
        designation_code, designation_name,
        population_type_code, population_type,
        imu_score, status_code, status_description,
        designation_date, update_date, withdrawal_date, break_in_designation,
        rural_status_code, rural_status,
        designated_population, service_area_name,
        source_id, etl_run_id, updated_at
    )
    VALUES (
        :external_id, :muni_id,
        :designation_code, :designation_name,
        :population_type_code, :population_type,
        :imu_score, :status_code, :status_description,
        :designation_date, :update_date, :withdrawal_date, :break_in_designation,
        :rural_status_code, :rural_status,
        :designated_population, :service_area_name,
        :source_id, :etl_run_id, now()
    )
    ON CONFLICT (external_id, source_id) DO UPDATE SET
        muni_id = EXCLUDED.muni_id,
        designation_code = EXCLUDED.designation_code,
        designation_name = EXCLUDED.designation_name,
        population_type_code = EXCLUDED.population_type_code,
        population_type = EXCLUDED.population_type,
        imu_score = EXCLUDED.imu_score,
        status_code = EXCLUDED.status_code,
        status_description = EXCLUDED.status_description,
        designation_date = EXCLUDED.designation_date,
        update_date = EXCLUDED.update_date,
        withdrawal_date = EXCLUDED.withdrawal_date,
        break_in_designation = EXCLUDED.break_in_designation,
        rural_status_code = EXCLUDED.rural_status_code,
        rural_status = EXCLUDED.rural_status,
        designated_population = EXCLUDED.designated_population,
        service_area_name = EXCLUDED.service_area_name,
        etl_run_id = EXCLUDED.etl_run_id,
        updated_at = now()
    """
)


def main() -> None:
    # Cache the download to /tmp; re-use if already there (e.g. from probe)
    cache_path = Path("/tmp/hrsa_mua_det.csv")
    if cache_path.exists() and cache_path.stat().st_size > 1_000_000:
        log.info("Using cached file at %s (%d bytes)", cache_path, cache_path.stat().st_size)
    else:
        _download_csv(cache_path)

    with EtlRunTracker(source_slug=SOURCE_SLUG) as run:
        read = 0
        pr_rows = 0
        upserted = 0
        skipped = 0
        with cache_path.open("r", encoding="utf-8-sig", newline="") as fh, session_scope() as s:
            reader = csv.DictReader(fh)
            for row in reader:
                read += 1
                if (row.get(COL_STATE_ABBR) or "").strip().upper() != PR_STATE_ABBR:
                    continue
                pr_rows += 1
                params = _row_to_params(row, run.source_id, run.run_id)
                if params is None:
                    skipped += 1
                    continue
                s.execute(UPSERT_SQL, params)
                upserted += 1

        run.rows_read = read
        run.rows_upserted = upserted
        run.rows_skipped = skipped
        log.info(
            "Finished. Total CSV rows=%d | PR rows=%d | Upserted=%d | Skipped=%d",
            read, pr_rows, upserted, skipped,
        )


if __name__ == "__main__":
    main()
