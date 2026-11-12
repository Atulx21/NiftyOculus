#!/bin/bash
# Creates schemas, the run-log table and the read-only role used by the AI layer.
# Runs automatically once, when the Postgres volume is first created.
set -e

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v ro_user="$READONLY_USER" -v ro_pass="$READONLY_PASSWORD" -v owner="$POSTGRES_USER" <<'EOSQL'

-- Separate database for Airflow's own metadata (keeps it away from the warehouse)
CREATE DATABASE airflow;

-- Medallion layers (bronze lives as Parquet files, not in Postgres)
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;

-- One row per pipeline stage per run: the source of the real numbers for the resume
CREATE TABLE IF NOT EXISTS ops.pipeline_run_log (
    run_id        BIGSERIAL PRIMARY KEY,
    run_date      DATE        NOT NULL,   -- logical date of the run
    stage         TEXT        NOT NULL,   -- ingest | silver | dbt_run | dbt_test
    rows_read     BIGINT,
    rows_written  BIGINT,
    duration_sec  NUMERIC(10,2),
    status        TEXT        NOT NULL,   -- success | failed
    error_message TEXT,
    logged_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Read-only role: can only SELECT from the gold schema.
CREATE ROLE :"ro_user" LOGIN PASSWORD :'ro_pass';
REVOKE ALL ON SCHEMA silver, ops FROM PUBLIC;
GRANT USAGE ON SCHEMA gold TO :"ro_user";
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO :"ro_user";
-- Tables dbt creates later are also readable automatically
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA gold GRANT SELECT ON TABLES TO :"ro_user";
EOSQL

