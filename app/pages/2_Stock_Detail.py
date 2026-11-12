"""Page 2 — Stock Detail: price chart, moving averages, volatility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.db import ro_query

st.set_page_config(page_title="Stock Detail · NiftyOculus", layout="wide", page_icon="📊")
st.title("📊 Stock Detail")


@st.cache_data(ttl=300)
def ticker_list():
    return ro_query("select ticker, company from gold.dim_stock order by company")


tdf = ticker_list()
options = {f"{r.company} ({r.ticker})": r.ticker for r in tdf.itertuples()}
chosen = st.selectbox("Select a stock", list(options.keys()))
ticker = options[chosen]

col1, col2 = st.columns([3, 1])
with col2:
    days = st.radio("Period", ["3 months", "6 months", "1 year", "All"], index=2)

period_map = {"3 months": 90, "6 months": 180, "1 year": 365, "All": 99999}
n_days = period_map[days]


@st.cache_data(ttl=300)
def price_data(tkr, n):
    return ro_query(
        """
        select m.trade_date, m.close, m.ma_20, m.ma_50, v.volatility_20d
        from gold.moving_averages m
        left join gold.volatility v
            on v.ticker = m.ticker and v.trade_date = m.trade_date
        where m.ticker = %s
          and m.trade_date >= (select max(trade_date) - %s from gold.moving_averages)
        order by m.trade_date
        """,
        (tkr, n),
    )


df = price_data(ticker, n_days)

if df.empty:
    st.warning("No data for this ticker.")
else:
    st.subheader(f"{chosen} — Price & Moving Averages")
    chart_df = df.set_index("trade_date")[["close", "ma_20", "ma_50"]].dropna(how="all")
    st.line_chart(chart_df, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
    st.caption("Blue = Close  |  Orange = MA20  |  Green = MA50")

    st.subheader("Rolling 20-day Volatility (std of daily returns)")
    vol_df = df.set_index("trade_date")[["volatility_20d"]].dropna()
    if not vol_df.empty:
        st.area_chart(vol_df, color=["#9467bd"])
    else:
        st.info("Volatility needs at least 20 trading days of returns.")

    # Quick stats
    latest = df.iloc[-1]
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Latest Close", f"₹{latest['close']:.2f}")
    m2.metric("20-day MA", f"₹{latest['ma_20']:.2f}" if latest["ma_20"] else "—")
    m3.metric("50-day MA", f"₹{latest['ma_50']:.2f}" if latest["ma_50"] else "—")
    m4.metric("20-day Volatility", f"{float(latest['volatility_20d'])*100:.2f}%" if latest["volatility_20d"] else "—")

