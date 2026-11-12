"""Page 3 — Ask the Data: placeholder, replaced by the real AI in Phase 7."""
import streamlit as st

st.set_page_config(page_title="Ask the Data · NiftyOculus", layout="wide", page_icon="🤖")
st.title("🤖 Ask the Data")
st.info("The AI text-to-SQL analyst is built in Phase 7. "
        "Come back after `.\make.ps1 dbt-run` and the Gemini key is set in `.env`.")
st.code("GEMINI_API_KEY=your_key_here   # .env")

