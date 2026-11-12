import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingestion import ingest  # noqa: E402


def _df(rows):
    return pd.DataFrame(rows, columns=ingest.COLUMNS)


def row(t, d):
    return (t, d, 1.0, 2.0, 0.5, 1.5, 1.5, 100)


def test_load_tickers_have_ns_suffix():
    tickers = ingest.load_tickers()
    assert len(tickers) == 50
    assert all(t.endswith(".NS") for t in tickers)


def test_start_date_new_ticker_uses_default():
    assert ingest.start_date_for("TCS.NS", {}) == ingest.DEFAULT_START


def test_start_date_is_day_after_watermark():
    wm = {"TCS.NS": date(2025, 1, 10)}
    assert ingest.start_date_for("TCS.NS", wm) == date(2025, 1, 11)


def test_filter_new_rows_drops_old_and_keeps_new_tickers():
    wm = {"TCS.NS": date(2025, 1, 10)}
    df = _df([row("TCS.NS", date(2025, 1, 10)),   # already loaded
              row("TCS.NS", date(2025, 1, 13)),   # new
              row("INFY.NS", date(2025, 1, 1))])  # ticker never loaded
    out = ingest.filter_new_rows(df, wm)
    assert len(out) == 2
    assert date(2025, 1, 10) not in out["date"].tolist()


def test_rerun_same_day_is_idempotent(tmp_path):
    day = date(2025, 2, 1)
    df = _df([row("TCS.NS", date(2025, 1, 31))])
    ingest.write_bronze(df, day, tmp_path)
    ingest.write_bronze(df, day, tmp_path)  # second run overwrites
    files = list(tmp_path.rglob("*.parquet"))
    assert len(files) == 1
    assert len(pd.read_parquet(files[0])) == 1


def test_watermark_ignores_todays_partition(tmp_path):
    ingest.write_bronze(_df([row("TCS.NS", date(2025, 1, 30))]), date(2025, 1, 31), tmp_path)
    ingest.write_bronze(_df([row("TCS.NS", date(2025, 1, 31))]), date(2025, 2, 1), tmp_path)
    wm = ingest.get_watermarks(tmp_path, date(2025, 2, 1))
    assert wm["TCS.NS"] == date(2025, 1, 30)  # today's partition excluded

