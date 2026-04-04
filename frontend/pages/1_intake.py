"""
pages/1_intake.py — New animal intake form + AI triage report display.
"""

import random
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils"))

import streamlit as st
from utils.session import require_login, get_token
from utils.api import submit_intake

st.set_page_config(page_title="New Intake — Shelter Triage", page_icon="➕", layout="wide")

# ── Helpers ──────────────────────────────────────────────────────

def gen_intake_code() -> str:
    return f"INK-{random.randint(10000, 99999)}"

def severity_css(severity: str) -> str:
    return {"urgent": "flag-urgent", "caution": "flag-caution",
            "info": "flag-info", "positive": "flag-positive"}.get(severity, "flag-info")

def tier_label(tier: int) -> str:
    return {1: "🔴 TIER 1 — CRITICAL", 2: "🟡 TIER 2 — URGENT", 3: "🟢 TIER 3 — STABLE"}.get(tier, "—")

def tier_css(tier: int) -> str:
    return {1: "tier-1", 2: "tier-2", 3: "tier-3"}.get(tier, "tier-3")


# ── Session State ─────────────────────────────────────────────────
if "intake_code" not in st.session_state:
    st.session_state["intake_code"] = gen_intake_code()

if "last_report" not in st.session_state:
    st.session_state["last_report"] = None


# ── Layout ───────────────────────────────────────────────────────
st.markdown("## ➕ New Intake")
st.caption("Fill in all required fields, then click **Run Triage Assessment**.")

form_col, report_col = st.columns([1, 1], gap="large")

with form_col:
    st.markdown("#### Intake Form")

    # Intake code row
    code_col, regen_col = st.columns([3, 1])
    with code_col:
        st.text_input("Intake ID", value=st.session_state["intake_code"],
                      disabled=True, key="intake_code_display")
    with regen_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↻ New ID", use_container_width=True):
            st.session_state["intake_code"] = gen_intake_code()
            st.rerun()

    # Animal details
    sp_col, age_col = st.columns(2)
    with sp_col:
        species = st.selectbox("Species *", ["", "Dog", "Cat", "Rabbit", "Bird",
                                              "Reptile", "Small mammal", "Other"])
    with age_col:
        estimated_age = st.selectbox("Estimated Age", ["", "Neonatal (0–4 weeks)",
            "Juvenile (1–6 months)", "Young adult (6m–2yr)", "Adult (2–7yr)", "Senior (7yr+)"])

    br_col, sx_col = st.columns(2)
    with br_col:
        breed = st.text_input("Breed / Description", placeholder="e.g. Mixed terrier, black/tan")
    with sx_col:
        sex = st.selectbox("Sex", ["", "Male intact", "Male neutered",
                                    "Female intact", "Female spayed"])

    intake_source = st.selectbox("Intake Source *", ["", "Owner surrender",
        "Stray — public drop-off", "Animal control impound",
        "Transfer from another shelter", "Rescue pull",
        "Field pick-up (injured/sick)", "Cruelty/neglect case", "Other"])

    observed_behavior = st.text_area(
        "Observed Behavior *",
        height=130,
        placeholder="Describe body language, reactions to handling, stress signals, "
                    "aggression, fearfulness, playfulness. Be specific.\n\n"
                    "e.g. 'Cowering in corner, flinches when touched, growled once when "
                    "leash approached. Did approach gate for treats.'"
    )

    medical_notes = st.text_area(
        "Medical / Physical Notes",
        height=100,
        placeholder="Visible injuries, body condition, coat/skin, eyes, discharge, "
                    "limping, wounds.\n\ne.g. 'Thin, ribs visible, laceration on left rear leg, eyes clear.'"
    )

    additional_context = st.text_area(
        "Additional Context",
        height=80,
        placeholder="Surrender reason, bite history, household animals, anything else relevant."
    )

    st.divider()
    run_btn = st.button("▶ Run Triage Assessment", type="primary",
                        use_container_width=True, key="run_triage")

# ── Submission Logic ─────────────────────────────────────────────
if run_btn:
    errors = []
    if not species:
        errors.append("Species is required.")
    if not intake_source:
        errors.append("Intake Source is required.")
    if not observed_behavior or len(observed_behavior.strip()) < 10:
        errors.append("Observed Behavior must be at least 10 characters.")

    if errors:
        for e in errors:
            form_col.error(e)
    else:
        payload = {
            "intake_code": st.session_state["intake_code"],
            "species": species,
            "estimated_age": estimated_age or None,
            "breed": breed or None,
            "sex": sex or None,
            "intake_source": intake_source,
            "observed_behavior": observed_behavior.strip(),
            "medical_notes": medical_notes.strip() or None,
            "additional_context": additional_context.strip() or None,
        }
        with st.spinner("🤖 Generating triage report via gpt-oss:120b..."):
            data, error = submit_intake(payload, get_token())

        if error:
            # Always regenerate code on any error to avoid duplicate key on retry
            st.session_state["intake_code"] = gen_intake_code()
            form_col.error(f"Triage failed: {error}")
        else:
            st.session_state["last_report"] = data
            st.session_state["intake_code"] = gen_intake_code()
            st.rerun()


# ── Report Display ───────────────────────────────────────────────
with report_col:
    st.markdown("#### Triage Report")

    if not st.session_state["last_report"]:
        st.info("Submit an intake to see the AI triage report here.")
    else:
        r = st.session_state["last_report"]
        report = r.get("triage_report", {})

        if not report:
            st.warning("Intake saved but no triage report was returned.")
        else:
            tier = report.get("urgency_tier", 3)
            tier_css_cls = tier_css(tier)

            # Header
            hdr_c, badge_c = st.columns([2, 1])
            with hdr_c:
                st.markdown(f"**{r['intake_code']}**")
                st.caption(f"{r['species']} · {r.get('estimated_age', '')} · {r.get('breed', '')}")
            with badge_c:
                st.markdown(
                    f'<span class="{tier_css_cls}">{tier_label(tier)}</span>',
                    unsafe_allow_html=True
                )

            st.divider()

            with st.expander("📊 Urgency Assessment", expanded=True):
                st.write(report.get("urgency_reason", "—"))

            with st.expander("🏠 Recommended Placement", expanded=True):
                icon = report.get("placement_icon", "🏠")
                ptype = report.get("placement_type", "—")
                pdesc = report.get("placement_description", "")
                st.markdown(f"**{icon} {ptype}**")
                st.caption(pdesc)

            with st.expander("🚩 Behavioral & Medical Flags", expanded=True):
                all_flags = report.get("behavioral_flags", []) + report.get("medical_flags", [])
                if all_flags:
                    flags_html = " ".join(
                        f'<span class="{severity_css(f["severity"])}">{f["label"]}</span>'
                        for f in all_flags
                    )
                    st.markdown(flags_html, unsafe_allow_html=True)
                else:
                    st.write("No flags identified.")

            with st.expander("✅ Immediate Next Steps", expanded=True):
                for i, step in enumerate(report.get("next_steps", []), 1):
                    st.markdown(f"**{i:02d}.** {step}")

            with st.expander("📝 Staff Summary", expanded=True):
                st.write(report.get("summary", "—"))

            st.divider()
            st.caption(
                f"🤖 Generated by {report.get('model_used', 'gpt-oss:120b')} · "
                f"{report.get('latency_ms', '?')}ms · "
                f"Verify Tier 1 & 2 reports with senior staff"
            )

            if st.button("🔄 Start New Intake", key="new_intake_btn"):
                st.session_state["last_report"] = None
                st.rerun()
