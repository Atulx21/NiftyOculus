"""Run dbt and record the outcome in ops.pipeline_run_log.

Usage:  python -m scripts.dbt_runner run  --run-date 2026-11-10
        python -m scripts.dbt_runner test --run-date 2026-11-10
Exit code is non-zero on failure, so Airflow stops the downstream tasks.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from common.run_log import log_run

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"
FLAGS = ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]


def dbt(command: str) -> int:
    # Run dbt with THIS interpreter and a clean environment, so packages leaked in by a
    # parent process (e.g. Airflow's own protobuf via PYTHONPATH) cannot shadow the venv's.
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    env["PYTHONNOUSERSITE"] = "1"
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()", command, *FLAGS]
    return subprocess.run(cmd, env=env).returncode


def results() -> list[dict]:
    """Per-node results of the most recent dbt command."""
    return json.loads((DBT_DIR / "target" / "run_results.json").read_text())["results"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "test"])
    ap.add_argument("--run-date", default=str(date.today()))
    args = ap.parse_args()
    run_date = date.fromisoformat(args.run_date)
    t0 = time.time()

    if args.stage == "run":
        rc = dbt("seed") or dbt("run")
        res = results() if (DBT_DIR / "target" / "run_results.json").exists() else []
        rows = sum(r.get("adapter_response", {}).get("rows_affected", 0) or 0 for r in res)
        err = None if rc == 0 else "dbt run failed; see Airflow task log"
        log_run(run_date, "dbt_run", None, rows, round(time.time() - t0, 2),
                "success" if rc == 0 else "failed", err)
    else:
        rc = dbt("test")
        res = results()
        passed = sum(1 for r in res if r["status"] == "pass")
        failed_names = [r["unique_id"].split(".")[-2] for r in res if r["status"] != "pass"]
        # rows_read = tests executed, rows_written = tests passed
        log_run(run_date, "dbt_test", len(res), passed, round(time.time() - t0, 2),
                "success" if rc == 0 else "failed",
                None if rc == 0 else f"{len(failed_names)} failed: {', '.join(failed_names)}"[:500])
    return rc


if __name__ == "__main__":
    sys.exit(main())

