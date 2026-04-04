"""
app.py — Streamlit entry point. No login — open access.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))

import streamlit as st
from utils.api import fetch_health

st.set_page_config(
    page_title="Shelter Intake Triage",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .tier-1 { background:#3d1010; color:#e05a4e; padding:4px 12px; border-radius:4px; font-weight:600; font-size:13px; }
  .tier-2 { background:#3d2a10; color:#e8a83a; padding:4px 12px; border-radius:4px; font-weight:600; font-size:13px; }
  .tier-3 { background:#1c3328; color:#4caf72; padding:4px 12px; border-radius:4px; font-weight:600; font-size:13px; }
  .flag-urgent  { background:#3d1010; color:#e05a4e; padding:2px 8px; border-radius:3px; font-size:12px; margin:2px; display:inline-block; }
  .flag-caution { background:#3d2a10; color:#e8a83a; padding:2px 8px; border-radius:3px; font-size:12px; margin:2px; display:inline-block; }
  .flag-info    { background:#1c3328; color:#4caf72; padding:2px 8px; border-radius:3px; font-size:12px; margin:2px; display:inline-block; }
  .flag-positive{ background:#142233; color:#5b9fd4; padding:2px 8px; border-radius:3px; font-size:12px; margin:2px; display:inline-block; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🐾 Shelter Triage")
    st.divider()
    st.page_link("pages/1_intake.py",  label="New Intake",     icon="➕")
    st.page_link("pages/2_history.py", label="Intake History", icon="📂")
    st.divider()
    with st.expander("System Status"):
        health = fetch_health()
        st.write("🟢 API" if health.get("status") == "ok" else "🔴 API")
        st.write("🟢 Ollama" if health.get("ollama_reachable") else "🔴 Ollama")
        st.write("🟢 Supabase" if health.get("supabase_reachable") else "🔴 Supabase")

st.markdown("## 🐾 Shelter Intake Triage Assistant")
st.info("👈 Use the sidebar to submit a **New Intake** or browse **Intake History**.")
