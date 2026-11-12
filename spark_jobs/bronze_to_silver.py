"""Bronze (Parquet) -> Silver (Postgres) with PySpark.

Steps: read all bronze partitions -> fix types -> drop nulls and bad prices ->
dedupe on (ticker, trade_date) keeping the latest ingestion -> write to a staging
table -> upsert into silver.daily_prices in ONE transaction (idempotent).
"""
import argparse
import os
import time
from datetime import date

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, DateType

from common.run_log import get_conn, log_run

BRONZE = "data/bronze/prices"
JDBC_JAR = os.getenv("JDBC_JAR", "/opt/jars/postgresql.jar")

DDL = """
CREATE TABLE IF NOT EXISTS silver.daily_prices (
    ticker         TEXT          NOT NULL,
    trade_date     DATE          NOT NULL,
    open           NUMERIC(18,4) NOT NULL,
    high           NUMERIC(18,4) NOT NULL,
    low            NUMERIC(18,4) NOT NULL,
    close          NUMERIC(18,4) NOT NULL,
    adj_close      NUMERIC(18,4),
    volume         BIGINT,
    ingestion_date DATE          NOT NULL,
    loaded_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, trade_date)
)"""

# Upsert = insert new rows, overwrite existing ones with the same key.
UPSERT = """
INSERT INTO silver.daily_prices
    (ticker, trade_date, open, high, low, close, adj_close, volume, ingestion_date)
SELECT ticker, trade_date, open, high, low, close, adj_close, volume, ingestion_date
FROM silver.stage_prices
ON CONFLICT (ticker, trade_date) DO UPDATE SET
    open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
    close = EXCLUDED.close, adj_close = EXCLUDED.adj_close, volume = EXCLUDED.volume,
    ingestion_date = EXCLUDED.ingestion_date, loaded_at = now()"""


def clean(df: DataFrame) -> DataFrame:
    """Pure transformation (no I/O) so it can be unit-tested."""
    typed = (
        df.withColumn("ticker", F.upper(F.trim("ticker")))
          .withColumn("trade_date", F.to_date("date"))
          .withColumn("ingestion_date", F.to_date("ingestion_date"))
          .withColumn("volume", F.col("volume").cast("long"))
    )
    for c in ["open", "high", "low", "close", "adj_close"]:
        typed = typed.withColumn(c, F.col(c).cast("decimal(18,4)"))

    valid = typed.dropna(subset=["ticker", "trade_date", "open", "high", "low", "close"]).filter(
        (F.col("close") > 0) & (F.col("open") > 0) & (F.col("low") > 0)
        & (F.col("high") >= F.col("low"))
    )
    # Same (ticker, date) may appear in several bronze partitions: keep the latest ingestion.
    w = Window.partitionBy("ticker", "trade_date").orderBy(F.col("ingestion_date").desc())
    deduped = valid.withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn")
    return deduped.select("ticker", "trade_date", "open", "high", "low", "close",
                          "adj_close", "volume", "ingestion_date")


def get_spark() -> SparkSession:
    # Small settings on purpose: laptop with limited RAM and tiny data.
    return (SparkSession.builder.master("local[2]").appName("niftyoculus-silver")
            .config("spark.driver.memory", "1g")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.ui.enabled", "false")
            .config("spark.jars", JDBC_JAR)
            .getOrCreate())


def run(run_date: date) -> dict:
    t0 = time.time()
    spark = get_spark()
    try:
        # Enforce schema to avoid Spark mis-inferring ingestion_date partition as int.
        bronze_schema = StructType([
            StructField("ticker",        StringType(), True),
            StructField("date",          DateType(),   True),
            StructField("open",          DoubleType(), True),
            StructField("high",          DoubleType(), True),
            StructField("low",           DoubleType(), True),
            StructField("close",         DoubleType(), True),
            StructField("adj_close",     DoubleType(), True),
            StructField("volume",        LongType(),   True),
            StructField("ingestion_date", StringType(), True),
        ])
        bronze = spark.read.schema(bronze_schema).parquet(BRONZE)
        rows_read = bronze.count()
        silver = clean(bronze).cache()
        rows_written = silver.count()

        url = (f"jdbc:postgresql://{os.getenv('POSTGRES_HOST', 'postgres')}:5432/"
               f"{os.environ['POSTGRES_DB']}")
        (silver.write.format("jdbc").option("url", url).option("dbtable", "silver.stage_prices")
               .option("user", os.environ["POSTGRES_USER"])
               .option("password", os.environ["POSTGRES_PASSWORD"])
               .option("driver", "org.postgresql.Driver").mode("overwrite").save())
    finally:
        spark.stop()

    # `with conn` = one transaction: all or nothing.
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute(UPSERT)
    stats = {"rows_read": rows_read, "rows_written": rows_written,
             "rejected": rows_read - rows_written, "duration_sec": round(time.time() - t0, 2)}
    print(stats)
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date", default=str(date.today()))
    d = date.fromisoformat(ap.parse_args().run_date)
    start = time.time()
    try:
        s = run(d)
        log_run(d, "silver", s["rows_read"], s["rows_written"], s["duration_sec"])
    except Exception as exc:
        log_run(d, "silver", None, None, round(time.time() - start, 2), "failed", str(exc)[:500])
        raise

