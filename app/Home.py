"""NiftyOculus Streamlit app — landing redirect to Market Overview."""
import streamlit as st

st.set_page_config(page_title="NiftyOculus", layout="wide", page_icon="📈")
st.switch_page("pages/1_Market_Overview.py")

