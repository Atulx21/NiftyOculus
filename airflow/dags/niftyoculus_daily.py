"""Daily NiftyOculus pipeline:  ingest -> silver (Spark) -> dbt run -> dbt test.

Runs Mon-Fri at 16:30 IST (NSE closes at 15:30). Each task calls the same Python
entry points you can run by hand. If a task fails, downstream tasks do not run.
"""
import os
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

PY = "/opt/airflow/pipeline-venv/bin/python"
PROJECT = "/opt/airflow/project"
# The run date is the day the schedule fires for (UTC date == IST date at 16:30 IST).
RUN_DATE = "{{ data_interval_end | ds }}"


def log_failure(context):
    """Runs after the LAST retry fails. Records the error in ops.pipeline_run_log,
    which also covers crashes where the Python script could not log by itself."""
    import psycopg2

    ti = context["task_instance"]
    with psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"), user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], dbname=os.environ["POSTGRES_DB"],
    ) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ops.pipeline_run_log (run_date, stage, status, error_message) "
            "VALUES (%s, %s, 'failed', %s)",
            (context["data_interval_end"].date(), f"airflow:{ti.task_id}",
             str(context.get("exception"))[:500]),
        )


default_args = {
    "retries": 2,                          # transient failures (network, rate limits)
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": log_failure,
}

with DAG(
    dag_id="niftyoculus_daily",
    start_date=pendulum.datetime(2026, 11, 2, tz="Asia/Kolkata"),
    schedule="30 16 * * 1-5",
    catchup=True,                          # missed days are run automatically
    max_active_runs=1,                     # runs go one at a time (watermark safety)
    default_args=default_args,
    tags=["niftyoculus"],
) as dag:
    # NIFTY_USE_SAMPLE=1 (in .env) uses the offline CSV instead of yfinance.
    ingest = BashOperator(
        task_id="ingest",
        # Remove '--sample' once yfinance is reliable; uses offline CSV for demo/CI.
        bash_command=(f"cd {PROJECT} && {PY} -m ingestion.ingest --run-date {RUN_DATE} --sample"),
    )
    silver = BashOperator(
        task_id="silver",
        bash_command=f"cd {PROJECT} && {PY} -m spark_jobs.bronze_to_silver --run-date {RUN_DATE}",
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(f"cd {PROJECT} && PATH=/opt/airflow/pipeline-venv/bin:$PATH "
                      f"{PY} -m scripts.dbt_runner run --run-date {RUN_DATE}"),
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(f"cd {PROJECT} && PATH=/opt/airflow/pipeline-venv/bin:$PATH "
                      f"{PY} -m scripts.dbt_runner test --run-date {RUN_DATE}"),
    )

    ingest >> silver >> dbt_run >> dbt_test

