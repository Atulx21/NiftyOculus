import sys
from pathlib import Path

import pytest

pytest.importorskip("pyspark")  # needs Java; runs inside the Docker image / CI
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pyspark.sql import SparkSession  # noqa: E402

from spark_jobs.bronze_to_silver import clean  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[1]").config("spark.ui.enabled", "false")
         .config("spark.sql.shuffle.partitions", "1").getOrCreate())
    yield s
    s.stop()


COLS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "ingestion_date"]


def test_clean_drops_bad_rows_and_dedupes(spark):
    rows = [
        ("tcs.ns", "2025-01-01", 10.0, 12.0, 9.0, 11.0, 11.0, 100, "2025-01-02"),   # ok (ticker upper-cased)
        ("TCS.NS", "2025-01-01", 10.0, 12.0, 9.0, 11.5, 11.5, 100, "2025-01-03"),   # duplicate, newer wins
        ("INFY.NS", "2025-01-01", 10.0, 8.0, 9.0, 9.5, 9.5, 100, "2025-01-02"),     # high < low
        ("WIPRO.NS", "2025-01-01", 10.0, 12.0, 9.0, -1.0, -1.0, 100, "2025-01-02"), # close <= 0
        ("ITC.NS", "2025-01-01", None, 12.0, 9.0, 11.0, 11.0, 100, "2025-01-02"),   # null open
    ]
    out = clean(spark.createDataFrame(rows, COLS)).collect()
    assert len(out) == 1
    assert out[0]["ticker"] == "TCS.NS"
    assert float(out[0]["close"]) == 11.5

