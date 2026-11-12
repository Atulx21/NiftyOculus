# Windows wrapper for the Makefile targets.
# Usage: .\make.ps1 up | down | psql | reset | build | ingest | silver | dbt-run | dbt-test | dbt-docs | test
# Optional date: .\make.ps1 ingest 2026-11-10
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Date = (Get-Date -Format "yyyy-MM-dd")
)

$run = "docker compose run --rm pipeline"
switch ($Target) {
    "up"       { docker compose up -d --wait }
    "down"     { docker compose down }
    "psql"     { docker compose exec postgres sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB' }
    "reset"    { docker compose down -v }   # deletes all data, re-runs init scripts
    "build"    { docker compose build pipeline }
    "ingest"   { Invoke-Expression "$run python -m ingestion.ingest --sample --run-date $Date" }
    "silver"   { Invoke-Expression "$run python -m spark_jobs.bronze_to_silver --run-date $Date" }
    "dbt-run"  { Invoke-Expression "$run python -m scripts.dbt_runner run --run-date $Date" }
    "dbt-test" { Invoke-Expression "$run python -m scripts.dbt_runner test --run-date $Date" }
    "dbt-docs" { Invoke-Expression "$run dbt docs generate" }
    "test"     { Invoke-Expression "$run python -m pytest tests -q" }
    "airflow-trigger" {
        $d2 = if ($Date) { $Date } else { Get-Date -Format "yyyy-MM-dd" }
        docker compose exec airflow-scheduler airflow dags trigger niftyoculus_daily --run-id "manual_$d2"
    }
    "airflow-status" {
        docker compose exec airflow-scheduler airflow dags list-runs -d niftyoculus_daily --no-backfill 2>&1 |
            Select-String -Pattern 'run_id|success|failed|running'
    }
    default    { Write-Error "Unknown target '$Target'." }
}
