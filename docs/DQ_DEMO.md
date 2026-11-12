# Data-quality demo: a dbt test catching bad data

Goal: show in an interview that bad data is caught, logged, and stops the pipeline.

## 1. Insert a deliberately bad row into silver
`high < low` and `close < 0` are impossible prices.

```powershell
"insert into silver.daily_prices (ticker,trade_date,open,high,low,close,ingestion_date) values ('TCS.NS','2026-11-12',100,90,95,-5,'2026-11-12');" | docker compose exec -T postgres sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
```

## 2. Run the tests
```powershell
docker compose run --rm pipeline python -m scripts.dbt_runner test --run-date 2026-11-12
```
Real output from my run:
```
14 of 19 FAIL 1 source_valid_ohlc_silver_daily_prices_ ......... [FAIL 1 in 0.07s]
Done. PASS=18 WARN=0 ERROR=1 SKIP=0 NO-OP=0 REUSED=0 TOTAL=19
```
The script exits non-zero, so in Airflow the downstream tasks would not run.

## 3. See it in the run log
```sql
select stage, rows_read, rows_written, status, error_message
from ops.pipeline_run_log where stage = 'dbt_test' order by run_id desc limit 1;
```
```
 dbt_test | 19 | 18 | failed | 1 failed: source_valid_ohlc_silver_daily_prices_
```
(`rows_read` = tests executed, `rows_written` = tests passed.) The Pipeline Health page shows this.

## 4. Clean up
```powershell
"delete from silver.daily_prices where trade_date='2026-11-12';" | docker compose exec -T postgres sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
```
Re-running the tests gives 19 of 19 PASS.

## Why the Spark job did not stop it
`clean()` already drops bad prices before they reach silver, so this row had to be inserted by hand.
Two layers of defence: Spark filters known-bad rows, dbt tests catch anything that slips through
(for example, a bug in the Spark job or a manual edit).

## A real bug the tests caught during development
A blank line at the end of `tickers.csv` produced an empty row in `dim_stock` (51 rows instead of 50).
`not_null` on `ticker` is the kind of test that flags this, and it was fixed in the CSV.

