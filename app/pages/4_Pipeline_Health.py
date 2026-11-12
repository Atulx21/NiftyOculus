"""Page 4 — Pipeline Health: reads ops.pipeline_run_log and shows status."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.db import owner_query   # ops schema is not in gold, so we use owner conn

st.set_page_config(page_title="Pipeline Health · NiftyOculus", layout="wide", page_icon="🩺")
st.title("🩺 Pipeline Health")

st.caption("Reads `ops.pipeline_run_log` — the audit trail written by every stage.")


@st.cache_data(ttl=30)
def run_log():
    return owner_query(
        """
        select run_date, stage,
               coalesce(rows_read::text, '—')    as rows_read,
               coalesce(rows_written::text, '—') as rows_written,
               coalesce(duration_sec::text, '—') as duration_sec,
               status,
               coalesce(error_message, '')        as error
        from ops.pipeline_run_log
        order by logged_at desc
        limit 100
        """,
    )


df = run_log()

# KPI cards: last 24-hour counts
import pandas as pd
today = df[df["run_date"] == df["run_date"].max()]
ok = (today["status"] == "success").sum()
fail = (today["status"] != "success").sum()

k1, k2, k3 = st.columns(3)
k1.metric("Runs today", len(today))
k2.metric("✅ Passed", ok)
k3.metric("❌ Failed", fail, delta=f"-{fail}" if fail > 0 else None,
          delta_color="inverse")

st.divider()
st.subheader("All runs (latest first)")

def highlight_status(val):
    if val == "success":
        return "background-color: #d4edda; color: #155724"
    elif val == "failed":
        return "background-color: #f8d7da; color: #721c24"
    return ""

styled = df.style.map(highlight_status, subset=["status"])
st.dataframe(styled, width="stretch", hide_index=True)

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

