"""Shared DB helpers for the Streamlit app.

The app always uses ONE of two connections:
  - owner  (read/write): ingest, silver and pipeline-health pages
  - ro     (READ-ONLY):  gold schema only — used by the AI analyst and chart pages

All gold queries therefore run through the read-only role, limiting blast radius.

pandas 3.x prefers SQLAlchemy connections, so we wrap psycopg2 with a thin helper
that uses cursor + fetchall instead of pd.read_sql to avoid the deprecation warning.
"""
import os

import pandas as pd
import psycopg2


def _dsn(user_env: str, pw_env: str) -> dict:
    return dict(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.environ[user_env],
        password=os.environ[pw_env],
        dbname=os.environ["POSTGRES_DB"],
        connect_timeout=5,
    )


def ro_conn():
    """Read-only connection (gold schema only)."""
    return psycopg2.connect(**_dsn("READONLY_USER", "READONLY_PASSWORD"))


def owner_conn():
    """Owner connection (all schemas)."""
    return psycopg2.connect(**_dsn("POSTGRES_USER", "POSTGRES_PASSWORD"))


def _query(conn_fn, sql: str, params=None) -> pd.DataFrame:
    """Run SQL and return a DataFrame without triggering the SQLAlchemy warning."""
    with conn_fn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame.from_records(rows, columns=cols, coerce_float=True)  # Decimal -> float


def ro_query(sql: str, params=None) -> pd.DataFrame:
    """Run a SELECT against the gold schema with the read-only role."""
    return _query(ro_conn, sql, params)


def owner_query(sql: str, params=None) -> pd.DataFrame:
    return _query(owner_conn, sql, params)

