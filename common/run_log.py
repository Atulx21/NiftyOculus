"""Tiny helper: write one row to ops.pipeline_run_log. Every stage uses it."""
import os

import psycopg2


def get_conn():
    """Owner-account connection to the warehouse (host 'postgres' inside Docker)."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT_INTERNAL", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def log_run(run_date, stage, rows_read, rows_written, duration_sec,
            status="success", error_message=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ops.pipeline_run_log
               (run_date, stage, rows_read, rows_written, duration_sec, status, error_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (run_date, stage, rows_read, rows_written, duration_sec, status, error_message),
        )

