"""
pages/2_history.py — Browse and search past intake records with triage reports.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.session import require_login, get_token
from utils.api import fetch_intakes, fetch_intake, delete_intake

st.set_page_config(page_title="Intake History — Shelter Triage", page_icon="📂", layout="wide")
pass  # no auth

# ── Helpers ──────────────────────────────────────────────────────

TIER_LABELS = {1: "🔴 Critical", 2: "🟡 Urgent", 3: "🟢 Stable"}
TIER_COLORS = {1: "🔴", 2: "🟡", 3: "🟢"}

def severity_css(severity: str) -> str:
    return {"urgent": "flag-urgent", "caution": "flag-caution",
            "info": "flag-info", "positive": "flag-positive"}.get(severity, "flag-info")


def fmt_date(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return dt_str


# ── State ────────────────────────────────────────────────────────
if "history_page" not in st.session_state:
    st.session_state["history_page"] = 1
if "selected_intake_id" not in st.session_state:
    st.session_state["selected_intake_id"] = None


# ── Page ─────────────────────────────────────────────────────────
st.markdown("## 📂 Intake History")

# Fetch data
PAGE_SIZE = 15
data, error = fetch_intakes(get_token(), page=st.session_state["history_page"], page_size=PAGE_SIZE)

if error:
    st.error(f"Could not load intakes: {error}")
    st.stop()

items = data.get("items", [])
total = data.get("total", 0)
total_pages = max(1, -(-total // PAGE_SIZE))  # Ceiling division

# ── Filters bar ──────────────────────────────────────────────────
f1, f2, f3 = st.columns([2, 1, 1])
with f1:
    search_q = st.text_input("🔍 Filter by ID, species, or breed", placeholder="e.g. INK-47291 or Dog")
with f2:
    tier_filter = st.selectbox("Filter by tier", ["All", "🔴 Critical (1)", "🟡 Urgent (2)", "🟢 Stable (3)"])
with f3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Apply client-side filters
filtered = items
if search_q:
    q = search_q.lower()
    filtered = [i for i in filtered if
                q in i.get("intake_code", "").lower() or
                q in (i.get("species") or "").lower() or
                q in (i.get("breed") or "").lower()]
if tier_filter != "All":
    tier_num = int(tier_filter.split("(")[1].replace(")", ""))
    filtered = [i for i in filtered if i.get("urgency_tier") == tier_num]

st.caption(f"Showing {len(filtered)} of {total} total records")
st.divider()

# ── Two-column layout: list | detail ─────────────────────────────
list_col, detail_col = st.columns([1, 1.4], gap="large")

with list_col:
    if not filtered:
        st.info("No intakes match your filters.")
    else:
        for item in filtered:
            tier = item.get("urgency_tier")
            tier_icon = TIER_COLORS.get(tier, "⚪")
            selected = st.session_state["selected_intake_id"] == item["id"]

            with st.container():
                btn_label = (
                    f"{tier_icon} **{item['intake_code']}** — {item['species']}"
                    + (f", {item.get('estimated_age', '')}" if item.get("estimated_age") else "")
                    + (f"\n_{item.get('breed', '')}_" if item.get("breed") else "")
                    + f"\n{fmt_date(item['created_at'])}"
                )
                if st.button(btn_label, key=f"sel_{item['id']}", use_container_width=True,
                             type="primary" if selected else "secondary"):
                    st.session_state["selected_intake_id"] = item["id"]
                    st.rerun()

    # Pagination
    st.divider()
    pg_prev, pg_info, pg_next = st.columns([1, 2, 1])
    with pg_prev:
        if st.button("← Prev", disabled=st.session_state["history_page"] <= 1, use_container_width=True):
            st.session_state["history_page"] -= 1
            st.rerun()
    with pg_info:
        st.caption(f"Page {st.session_state['history_page']} / {total_pages}")
    with pg_next:
        if st.button("Next →", disabled=st.session_state["history_page"] >= total_pages, use_container_width=True):
            st.session_state["history_page"] += 1
            st.rerun()


with detail_col:
    if not st.session_state["selected_intake_id"]:
        st.info("👈 Select an intake to view its full triage report.")
    else:
        intake_data, err = fetch_intake(st.session_state["selected_intake_id"], get_token())
        if err:
            st.error(f"Could not load intake: {err}")
        elif not intake_data:
            st.warning("Intake not found.")
        else:
            r = intake_data
            report = r.get("triage_report")

            # Header
            tier = report.get("urgency_tier", 3) if report else None
            tier_label = TIER_LABELS.get(tier, "Pending") if tier else "⏳ Pending"

            h1, h2 = st.columns([2, 1])
            with h1:
                st.markdown(f"### {r['intake_code']}")
                st.caption(f"Submitted {fmt_date(r['created_at'])}")
            with h2:
                st.markdown(f"**{tier_label}**")

            st.divider()

            # Intake raw data
            with st.expander("📋 Intake Details", expanded=False):
                d1, d2 = st.columns(2)
                with d1:
                    st.write(f"**Species:** {r['species']}")
                    st.write(f"**Age:** {r.get('estimated_age') or '—'}")
                    st.write(f"**Breed:** {r.get('breed') or '—'}")
                    st.write(f"**Sex:** {r.get('sex') or '—'}")
                with d2:
                    st.write(f"**Source:** {r['intake_source']}")
                st.write("**Observed Behavior:**")
                st.info(r["observed_behavior"])
                if r.get("medical_notes"):
                    st.write("**Medical Notes:**")
                    st.info(r["medical_notes"])
                if r.get("additional_context"):
                    st.write("**Additional Context:**")
                    st.info(r["additional_context"])

            if report:
                with st.expander("📊 Urgency Assessment", expanded=True):
                    st.write(report.get("urgency_reason", "—"))

                with st.expander("🏠 Recommended Placement", expanded=True):
                    icon = report.get("placement_icon", "🏠")
                    st.markdown(f"**{icon} {report.get('placement_type', '—')}**")
                    st.caption(report.get("placement_description", ""))

                with st.expander("🚩 Flags", expanded=True):
                    all_flags = report.get("behavioral_flags", []) + report.get("medical_flags", [])
                    if all_flags:
                        flags_html = " ".join(
                            f'<span class="{severity_css(f["severity"])}">{f["label"]}</span>'
                            for f in all_flags
                        )
                        st.markdown(flags_html, unsafe_allow_html=True)
                    else:
                        st.write("No flags.")

                with st.expander("✅ Next Steps", expanded=True):
                    for i, step in enumerate(report.get("next_steps", []), 1):
                        st.markdown(f"**{i:02d}.** {step}")

                with st.expander("📝 Staff Summary", expanded=True):
                    st.write(report.get("summary", "—"))

                st.caption(
                    f"🤖 {report.get('model_used', 'llama3.1:8b')} · "
                    f"{report.get('latency_ms', '?')}ms"
                )
            else:
                st.warning("No triage report available for this intake.")

            # Admin delete
            if get_user_role() == "admin":
                st.divider()
                with st.expander("⚠️ Admin Actions"):
                    st.warning("Deleting an intake is permanent and cannot be undone.")
                    if st.button("🗑️ Delete This Intake", type="secondary", key="del_btn"):
                        ok, del_err = delete_intake(r["id"], get_token())
                        if ok:
                            st.success("Intake deleted.")
                            st.session_state["selected_intake_id"] = None
                            st.rerun()
                        else:
                            st.error(f"Delete failed: {del_err}")
