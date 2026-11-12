"""Page 1 — Market Overview: top gainers/losers table and sector heatmap."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from app.db import ro_query

st.set_page_config(page_title="Market Overview · NiftyOculus", layout="wide", page_icon="📈")
st.title("📈 Market Overview")


@st.cache_data(ttl=300)
def latest_date() -> str:
    return ro_query("select max(trade_date)::text from gold.top_gainers_losers_daily").iloc[0, 0]


@st.cache_data(ttl=300)
def gainers_losers(d: str) -> pd.DataFrame:
    return ro_query(
        "select rank_type, rank, ticker, company, sector, "
        "round(daily_return*100,2) as pct, close "
        "from gold.top_gainers_losers_daily where trade_date=%s order by rank_type, rank",
        (d,),
    )


@st.cache_data(ttl=300)
def sector_perf(d: str) -> pd.DataFrame:
    return ro_query(
        "select sector, round(avg_return*100,2) as avg_return_pct, total_volume "
        "from gold.sector_performance_daily where trade_date=%s order by avg_return_pct desc",
        (d,),
    )


d = latest_date()
st.caption(f"Data as of **{d}**")

gl = gainers_losers(d)
col1, col2 = st.columns(2)

with col1:
    st.subheader("🟢 Top 5 Gainers")
    g = gl[gl["rank_type"] == "gainer"][["rank", "ticker", "company", "pct", "close"]].reset_index(drop=True)
    g["pct"] = g["pct"].map(lambda x: f"+{x:.2f}%")
    st.dataframe(g, width="stretch", hide_index=True)

with col2:
    st.subheader("🔴 Top 5 Losers")
    l = gl[gl["rank_type"] == "loser"][["rank", "ticker", "company", "pct", "close"]].reset_index(drop=True)
    l["pct"] = l["pct"].map(lambda x: f"{x:.2f}%")
    st.dataframe(l, width="stretch", hide_index=True)

st.divider()
st.subheader("🌐 Sector Performance Heatmap")
sp = sector_perf(d)
# Color sectors by avg return: green > 0, red < 0
def color_return(val):
    color = "background-color: #d4edda" if val >= 0 else "background-color: #f8d7da"
    return color

styled = sp.style.map(color_return, subset=["avg_return_pct"])
st.dataframe(styled, width="stretch", hide_index=True)

