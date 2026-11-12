"""Ingestion: yfinance (or sample CSV) -> bronze Parquet, incrementally.

Bronze layout:  data/bronze/prices/ingestion_date=YYYY-MM-DD/part.parquet
Watermark = latest price date per ticker found in *earlier* ingestion partitions.
Re-running the same day overwrites that day's partition, so it is idempotent.
"""
import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BRONZE_DIR = ROOT / "data" / "bronze" / "prices"
TICKERS_CSV = Path(__file__).resolve().parent / "tickers.csv"
SAMPLE_CSV = ROOT / "data" / "sample" / "sample_prices.csv"
DEFAULT_START = date(2024, 1, 1)  # first load goes back this far
COLUMNS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]


def load_tickers(path: Path = TICKERS_CSV) -> list[str]:
    return pd.read_csv(path)["ticker"].tolist()


def get_watermarks(bronze_dir: Path, run_date: date) -> dict[str, date]:
    """Max price date per ticker, ignoring today's partition (so a re-run re-fetches it)."""
    frames = []
    for part in bronze_dir.glob("ingestion_date=*"):
        if part.name == f"ingestion_date={run_date}":
            continue
        frames.append(pd.read_parquet(part, columns=["ticker", "date"]))
    if not frames:
        return {}
    df = pd.concat(frames)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.groupby("ticker")["date"].max().to_dict()


def start_date_for(ticker: str, watermarks: dict[str, date]) -> date:
    """Fetch from the day after the watermark; full history if the ticker is new."""
    last = watermarks.get(ticker)
    return last + timedelta(days=1) if last else DEFAULT_START


def filter_new_rows(df: pd.DataFrame, watermarks: dict[str, date]) -> pd.DataFrame:
    """Keep only rows strictly after each ticker's watermark."""
    if df.empty:
        return df
    wm = df["ticker"].map(watermarks)  # NaN for tickers never loaded
    d = pd.to_datetime(df["date"]).dt.date
    keep = wm.isna() | (d > wm.where(wm.notna(), date.min))
    return df[keep].reset_index(drop=True)


def fetch_ticker(ticker: str, start: date, retries: int = 3) -> pd.DataFrame:
    """Download one ticker from yfinance with simple retry; returns COLUMNS."""
    import yfinance as yf  # imported here so tests do not need network libs

    for attempt in range(1, retries + 1):
        try:
            raw = yf.download(ticker, start=str(start), auto_adjust=False,
                              progress=False, multi_level_index=False)
            if raw.empty:
                return pd.DataFrame(columns=COLUMNS)
            raw = raw.reset_index().rename(columns={
                "Date": "date", "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Adj Close": "adj_close", "Volume": "volume"})
            raw["ticker"] = ticker
            return raw[COLUMNS]
        except Exception as exc:  # network / rate limit
            print(f"  {ticker} attempt {attempt} failed: {exc}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"yfinance failed for {ticker} after {retries} attempts")


def write_bronze(df: pd.DataFrame, run_date: date, bronze_dir: Path = BRONZE_DIR) -> Path:
    """Write the day's partition, replacing any previous file (idempotent)."""
    part = bronze_dir / f"ingestion_date={run_date}"
    part.mkdir(parents=True, exist_ok=True)
    out = part / "part.parquet"
    df.to_parquet(out, index=False)
    return out


def run(run_date: date, use_sample: bool = False) -> dict:
    t0 = time.time()
    watermarks = get_watermarks(BRONZE_DIR, run_date)
    if use_sample:
        df = pd.read_csv(SAMPLE_CSV)  # offline fallback
        df["date"] = pd.to_datetime(df["date"]).dt.date
    else:
        frames = [fetch_ticker(t, start_date_for(t, watermarks)) for t in load_tickers()]
        df = pd.concat(frames, ignore_index=True)
        df["date"] = pd.to_datetime(df["date"]).dt.date
    rows_read = len(df)
    df = filter_new_rows(df, watermarks)
    out = write_bronze(df, run_date)
    stats = {"rows_read": rows_read, "rows_written": len(df),
             "duration_sec": round(time.time() - t0, 2), "path": str(out)}
    print(stats)
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date", default=str(date.today()))
    ap.add_argument("--sample", action="store_true", help="use data/sample CSV, no network")
    args = ap.parse_args()
    from common.run_log import log_run  # needs Postgres; kept out of the tested helpers

    d = date.fromisoformat(args.run_date)
    start = time.time()
    try:
        s = run(d, args.sample)
        log_run(d, "ingest", s["rows_read"], s["rows_written"], s["duration_sec"])
    except Exception as exc:
        log_run(d, "ingest", None, None, round(time.time() - start, 2), "failed", str(exc)[:500])
        raise

