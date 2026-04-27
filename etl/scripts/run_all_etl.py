#!/usr/bin/env python3
"""
SaludPR — Master ETL runner.

Runs all ETL sources in dependency order, validates results, writes a run
log to data/etl_log.json, sends WhatsApp + email notifications, and commits
the log to git.

Usage:
    cd /home/work/projects/saludpr/etl
    uv run python scripts/run_all_etl.py [--dry-run] [--source NAME]

Environment variables (read from backend/.env):
    DATABASE_URL — PostgreSQL connection string
    OPENCLAW_NOTIFY_WEBHOOK — optional: if set, used for WhatsApp delivery
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ETL_DIR = REPO_ROOT / "etl"
LOG_PATH = REPO_ROOT / "data" / "etl_log.json"

# ---------------------------------------------------------------------------
# Notification config
# ---------------------------------------------------------------------------
NOTIFY_EMAIL = "carlos.perez@dataurea.com"
NOTIFY_WHATSAPP = "+17874031552"
VM_NAME = os.environ.get("OPENCLAW_VM_NAME", "")

# ---------------------------------------------------------------------------
# Source definitions — in dependency order
# ---------------------------------------------------------------------------
SOURCES = [
    {
        "name": "census_tiger_municipalities",
        "module": "sources.census_tiger_municipalities",
        "description": "Census TIGER/Line — municipal boundaries (78 municipios)",
        "required": True,   # must pass or abort
    },
    {
        "name": "census_tiger_barrios",
        "module": "sources.census_tiger_barrios",
        "description": "Census TIGER/Line — barrio boundaries",
        "required": False,
    },
    {
        "name": "census_acs",
        "module": "sources.census_acs",
        "description": "Census ACS — demographics, poverty, insurance (municipios)",
        "required": True,
    },
    {
        "name": "census_acs_barrios",
        "module": "sources.census_acs_barrios",
        "description": "Census ACS — demographics, poverty, insurance (barrios)",
        "required": False,
    },
    {
        "name": "hrsa_mua",
        "module": "sources.hrsa_mua",
        "description": "HRSA — Medically Underserved Areas/Populations",
        "required": True,
    },
    {
        "name": "cdc_places_county",
        "module": "sources.cdc_places_county",
        "description": "CDC PLACES — chronic disease rates by municipio",
        "required": True,
    },
    {
        "name": "cdc_brfss_territory",
        "module": "sources.cdc_brfss_territory",
        "description": "CDC BRFSS — territory-level chronic disease trends (PR)",
        "required": True,
    },
]


# ---------------------------------------------------------------------------
# Validation checks — run after all ETL completes
# ---------------------------------------------------------------------------
VALIDATION_SQL = {
    "municipalities_count": {
        "sql": "SELECT COUNT(*) FROM municipalities",
        "expected_min": 78,
        "expected_max": 78,
        "description": "Los 78 municipios deben estar cargados",
    },
    "health_metrics_rows": {
        "sql": "SELECT COUNT(*) FROM health_metrics",
        "expected_min": 100,
        "expected_max": None,
        "description": "health_metrics debe tener al menos 100 filas",
    },
    "territory_metrics_rows": {
        "sql": "SELECT COUNT(*) FROM territory_health_metrics",
        "expected_min": 10,
        "expected_max": None,
        "description": "territory_health_metrics debe tener al menos 10 filas",
    },
    "diabetes_rate_sanity": {
        "sql": (
            "SELECT AVG(value::float) FROM territory_health_metrics "
            "WHERE indicator_code = 'pct_diabetes_diagnosed'"
        ),
        "expected_min": 5.0,
        "expected_max": 50.0,
        "description": "Tasa promedio de diabetes debe estar entre 5% y 50%",
    },
}


def _run_validation() -> tuple[bool, list[dict]]:
    """Run DB validations. Returns (all_passed, list_of_results)."""
    try:
        import sqlalchemy
        from lib.db import get_engine
    except ImportError:
        return False, [{"check": "import", "passed": False, "error": "SQLAlchemy import failed"}]

    engine = get_engine()
    results = []
    all_passed = True

    with engine.connect() as conn:
        for check_name, check in VALIDATION_SQL.items():
            try:
                result = conn.execute(sqlalchemy.text(check["sql"])).scalar()
                value = float(result) if result is not None else None

                passed = True
                if value is None:
                    passed = False
                if check["expected_min"] is not None and value is not None:
                    if value < check["expected_min"]:
                        passed = False
                if check["expected_max"] is not None and value is not None:
                    if value > check["expected_max"]:
                        passed = False

                results.append({
                    "check": check_name,
                    "description": check["description"],
                    "value": value,
                    "expected_min": check["expected_min"],
                    "expected_max": check["expected_max"],
                    "passed": passed,
                })
                if not passed:
                    all_passed = False
            except Exception as e:
                results.append({
                    "check": check_name,
                    "description": check["description"],
                    "passed": False,
                    "error": str(e),
                })
                all_passed = False

    return all_passed, results


def _run_source(source: dict, dry_run: bool) -> dict:
    """Run a single ETL source. Returns a result dict."""
    name = source["name"]
    module = source["module"]
    start = datetime.now(timezone.utc)

    print(f"\n{'='*60}")
    print(f"  Running: {name}")
    print(f"  {source['description']}")
    print(f"{'='*60}")

    if dry_run:
        print(f"  [DRY RUN] Skipping execution")
        return {
            "source": name,
            "status": "skipped_dry_run",
            "started_at": start.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0,
        }

    try:
        result = subprocess.run(
            [sys.executable, "-m", module],
            cwd=str(ETL_DIR),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per source
            env={**os.environ, "PYTHONPATH": str(ETL_DIR)},
        )
        finished = datetime.now(timezone.utc)
        duration = (finished - start).total_seconds()

        if result.returncode == 0:
            print(f"  ✅ SUCCESS ({duration:.0f}s)")
            if result.stdout:
                print(result.stdout[-2000:])  # last 2000 chars
            return {
                "source": name,
                "status": "success",
                "started_at": start.isoformat(),
                "finished_at": finished.isoformat(),
                "duration_seconds": round(duration),
                "stdout_tail": result.stdout[-500:] if result.stdout else "",
            }
        else:
            print(f"  ❌ FAILED (exit {result.returncode}, {duration:.0f}s)")
            print(result.stderr[-1000:] if result.stderr else "(no stderr)")
            return {
                "source": name,
                "status": "failed",
                "started_at": start.isoformat(),
                "finished_at": finished.isoformat(),
                "duration_seconds": round(duration),
                "error": result.stderr[-1000:] if result.stderr else "no error output",
                "stdout_tail": result.stdout[-500:] if result.stdout else "",
            }
    except subprocess.TimeoutExpired:
        return {
            "source": name,
            "status": "timeout",
            "started_at": start.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": "Timed out after 600 seconds",
        }
    except Exception as e:
        return {
            "source": name,
            "status": "error",
            "started_at": start.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": traceback.format_exc(),
        }


def _write_log(run_results: list[dict], validation_results: list[dict], overall_status: str) -> None:
    """Write/update data/etl_log.json."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing log (history of runs)
    existing = []
    if LOG_PATH.exists():
        try:
            existing = json.loads(LOG_PATH.read_text()).get("runs", [])
        except Exception:
            existing = []

    now = datetime.now(timezone.utc)
    entry = {
        "run_at": now.isoformat(),
        "overall_status": overall_status,
        "sources": run_results,
        "validations": validation_results,
    }

    # Keep last 10 runs
    runs = [entry] + existing[:9]

    log_data = {
        "last_updated": now.isoformat(),
        "last_status": overall_status,
        "runs": runs,
    }

    LOG_PATH.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
    print(f"\n📋 Log written to {LOG_PATH}")


def _send_notifications(
    run_results: list[dict],
    validation_results: list[dict],
    overall_status: str,
    dry_run: bool,
) -> None:
    """Send WhatsApp + email notifications via gsk CLI."""
    if dry_run:
        print("\n[DRY RUN] Skipping notifications")
        return

    failed_sources = [r for r in run_results if r["status"] not in ("success", "skipped_dry_run")]
    failed_validations = [v for v in validation_results if not v.get("passed", True)]

    emoji = "✅" if overall_status == "success" else "❌"
    now_pr = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # --- Build message ---
    lines = [
        f"{emoji} *SaludPR ETL — {overall_status.upper()}*",
        f"📅 {now_pr}",
        "",
    ]

    for r in run_results:
        s = r["status"]
        icon = "✅" if s == "success" else ("⏭️" if "skip" in s else "❌")
        lines.append(f"{icon} {r['source']} ({r.get('duration_seconds', 0)}s)")

    if failed_validations:
        lines += ["", "⚠️ *Validation failures:*"]
        for v in failed_validations:
            lines.append(f"  • {v['description']}: {v.get('value', 'N/A')}")

    if not failed_sources and not failed_validations:
        lines += ["", "All checks passed. Dashboard data is up to date."]

    message = "\n".join(lines)
    print(f"\n📨 Notification:\n{message}")

    # Send via gsk vm_email
    email_body = message.replace("*", "**")
    subject = f"SaludPR ETL — {overall_status.upper()} — {now_pr}"
    try:
        subprocess.run(
            ["gsk", "vm_email", "send", NOTIFY_EMAIL,
             "-s", subject,
             "-b", email_body,
             "-f", VM_NAME or "saludpr"],
            timeout=30,
            capture_output=True,
        )
        print(f"  ✅ Email sent to {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"  ⚠️ Email failed: {e}")

    # Send via openclaw WhatsApp (uses the message tool via CLI)
    try:
        subprocess.run(
            ["openclaw", "message", "send",
             "--to", NOTIFY_WHATSAPP,
             "--channel", "whatsapp",
             "--message", message],
            timeout=30,
            capture_output=True,
        )
        print(f"  ✅ WhatsApp sent to {NOTIFY_WHATSAPP}")
    except Exception as e:
        print(f"  ⚠️ WhatsApp failed: {e}")


def _git_commit(dry_run: bool) -> None:
    """Commit data/etl_log.json to git."""
    if dry_run:
        print("\n[DRY RUN] Skipping git commit")
        return

    try:
        subprocess.run(
            ["git", "add", "data/etl_log.json"],
            cwd=str(REPO_ROOT), capture_output=True, check=True,
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        subprocess.run(
            ["git", "commit", "-m", f"etl: update data log {now} [skip ci]"],
            cwd=str(REPO_ROOT), capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=str(REPO_ROOT), capture_output=True,
        )
        print("  ✅ Git commit pushed")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Git commit failed (may be nothing to commit): {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SaludPR master ETL runner")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute, just show plan")
    parser.add_argument("--source", help="Run only this source (by name)")
    parser.add_argument("--skip-git", action="store_true", help="Skip git commit")
    parser.add_argument("--skip-notify", action="store_true", help="Skip notifications")
    args = parser.parse_args()

    print(f"\n🚀 SaludPR ETL — {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"   Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Repo: {REPO_ROOT}")

    # Filter sources if --source given
    sources_to_run = SOURCES
    if args.source:
        sources_to_run = [s for s in SOURCES if s["name"] == args.source]
        if not sources_to_run:
            print(f"❌ Unknown source: {args.source}")
            sys.exit(1)

    # Run sources
    run_results = []
    aborted = False
    for source in sources_to_run:
        result = _run_source(source, args.dry_run)
        run_results.append(result)

        # Abort on required source failure
        if result["status"] not in ("success", "skipped_dry_run") and source.get("required"):
            print(f"\n🛑 Required source '{source['name']}' failed. Aborting.")
            aborted = True
            break

    # Validate
    print("\n\n🔍 Running data validation checks...")
    if args.dry_run or aborted:
        validation_passed = not aborted
        validation_results = []
        print("  [DRY RUN or ABORTED] Skipping validation")
    else:
        # Add ETL dir to path for imports
        sys.path.insert(0, str(ETL_DIR))
        validation_passed, validation_results = _run_validation()
        for v in validation_results:
            icon = "✅" if v["passed"] else "❌"
            print(f"  {icon} {v['check']}: {v.get('value', 'N/A')} — {v['description']}")

    # Determine overall status
    failed = [r for r in run_results if r["status"] not in ("success", "skipped_dry_run")]
    failed_validations = [v for v in validation_results if not v.get("passed", True)]

    if aborted or failed or failed_validations:
        overall_status = "failed"
    else:
        overall_status = "success"

    print(f"\n{'🎉' if overall_status == 'success' else '💥'} Overall: {overall_status.upper()}")

    # Write log
    _write_log(run_results, validation_results, overall_status)

    # Notifications
    if not args.skip_notify:
        _send_notifications(run_results, validation_results, overall_status, args.dry_run)

    # Git commit
    if not args.skip_git:
        _git_commit(args.dry_run)

    sys.exit(0 if overall_status == "success" else 1)


if __name__ == "__main__":
    main()
