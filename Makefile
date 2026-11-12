.PHONY: up down psql reset build ingest silver dbt-run dbt-test dbt-docs test

RUN = docker compose run --rm pipeline
D ?= $(shell date +%F)

up:        ## start the stack
	docker compose up -d --wait

down:      ## stop the stack (data kept)
	docker compose down

psql:      ## open a SQL shell in the warehouse
	docker compose exec postgres sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

reset:     ## stop and DELETE all data
	docker compose down -v

build:     ## build the Python/Spark/dbt image
	docker compose build pipeline

ingest:    ## ingest with the offline sample:  make ingest D=2026-11-10
	$(RUN) python -m ingestion.ingest --sample --run-date $(D)

silver:    ## bronze -> silver with Spark
	$(RUN) python -m spark_jobs.bronze_to_silver --run-date $(D)

dbt-run:   ## silver -> gold
	$(RUN) python -m scripts.dbt_runner run --run-date $(D)

dbt-test:  ## data-quality tests
	$(RUN) python -m scripts.dbt_runner test --run-date $(D)

dbt-docs:  ## generate dbt docs (catalog + manifest)
	$(RUN) dbt docs generate

test:      ## pytest
	$(RUN) python -m pytest tests -q

airflow-trigger: ## manually trigger the DAG for today
	docker compose exec airflow-scheduler airflow dags trigger niftyoculus_daily

airflow-status: ## list recent DAG runs
	docker compose exec airflow-scheduler airflow dags list-runs -d niftyoculus_daily --no-backfill 2>&1 | grep -E 'run_id|success|failed|running'
