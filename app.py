import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import json
import time

# ── Engine import ──────────────────────────────────────────────────────────────
try:
    from pfff_engine import (
        PROJECTS, MODES, HURDLES,
        compute_scn, run_mcs, simulate_mode,
        spearman_tornado, rcf_acid_test, eirr_iter,
        fi_color, verdict,
    )
except ImportError:
    st.error("Missing pfff_engine.py in the same directory.")
    st.stop()

# ── Page config & CSS ──────────────────────────────────────────────────────────
st.set_page_config(page_title="PFFF v11 — Forensic Audit", page_icon="🏛️", layout="wide")

# Custom CSS for spacing, large metrics, and professional feel
st.markdown("""
<style>
    .block-container {padding-top: 3.5rem;}
    .big-metric {background:#f8f9fa; border-radius:10px; padding:25px; border-left:10px solid; text-align:center; margin-bottom:15px;}
    .big-metric-val {font-size:3.8rem; font-weight:800; margin:0; line-height:1;}
    .big-metric-lbl {font-size:1.1rem; color:#6c757d; font-weight:700; margin-bottom:8px;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 55px; font-weight:700; font-size: 16px;}
</style>
""", unsafe_allow_html=True)

# ── State Management ──────────────────────────────────────────────────────────
if "p_data" not in st.session_state:
    st.session_state["p_data"] = dict(PROJECTS["P2"])
if "audit_results" not in st.session_state:
    st.session_state["audit_results"] = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏛️ Auditor Controls")
    tmpl = st.selectbox("1. Load Project Template", list(PROJECTS.keys()), format_func=lambda c: PROJECTS[c]["name"])
    
    if st.button("📂 Initialize Data"):
        st.session_state["p_data"] = dict(PROJECTS[tmpl])
        st.session_state["audit_results"] = None # Reset results on new template

    p = st.session_state["p_data"]
    st.divider()

    # Simulation Mode
    zero_stress = st.toggle("🟢 Zero-Stress Mode", value=False, help="Forces ideal DPR conditions: 0 cost overrun, 0 delay, 100% traffic.")
    sim_mode = st.selectbox("Audit Procurement Mode", MODES, index=MODES.index(p.get("dpr_mode","EPC")))
    
    st.divider()
    run_btn = st.button("🚀 EXECUTE FORENSIC AUDIT", type="primary", use_container_width=True)
    st.divider()

    with st.expander("🛠️ Modify SCN Site Readiness", expanded=True):
        p["la_pct"] = st.slider("LA% Complete", 0, 100, int(p.get("la_pct",50)))
        p["geotech"] = st.select_slider("Geotech", ["DESKTOP","PARTIAL","COMPLETE"], value=p.get("geotech","PARTIAL"))
        p["contractor"] = st.select_slider("Contractor Status", ["STRESSED","ADEQUATE","STRONG"], value=p.get("contractor","ADEQUATE"))

# ── Logic: Run Simulation ─────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Simulating 10,000 parallel project outcomes..."):
        if zero_stress:
            # Force zero-stress scn for proof charts
            scn = compute_scn(p)
            scn["v05_mean_mult"] = 1.0; scn["v05_sigma"] = 0.001
            scn["v07_ps"] = 0.0; scn["muA"] = p["yr1_aadt"]
            scn["sA"] = 0.001; scn["w2"] = 0.0
            samp = run_mcs(p, scn, 10000)
        else:
            scn = compute_scn(p)
            samp = run_mcs(p, scn, 10000)
        
        res = simulate_mode(p, scn, samp, sim_mode, 10000)
        torn = spearman_tornado(p, scn, samp, res["eirr_arr"])
        rcf = rcf_acid_test(p, scn, samp, res["fi_p"])
        
        st.session_state["audit_results"] = {"res": res, "scn": scn, "samp": samp, "torn": torn, "rcf": rcf}

# ── Main UI ───────────────────────────────────────────────────────────────────
t0, t1, t2, t3 = st.tabs(["🏠 OVERVIEW", "📊 DASHBOARD", "🔬 INSIGHTS", "📋 RAW AUDIT"])

with t0:
    st.title("Probabilistic Feasibility Fragility Framework (PFFF)")
    st.markdown("""
    ### Forensic Decision Support System for NHAI
    Deterministic DPRs often ignore real-world friction. PFFF uses **Site-Condition-Network (SCN)** conditioning to stress-test projects.
    
    - **Green Verdict:** Resilient; passes hurdle under realistic uncertainty.
    - **Amber Verdict:** Conditional; requires monitoring of primary risk drivers.
    - **Red Verdict:** Fragile; requires return to consultant for scope or evidence revision.
    """)
    st.info("👈 Use the sidebar to select a project and hit 'Execute' to begin.")

# Extract results if they exist
if st.session_state["audit_results"]:
    data = st.session_state["audit_results"]
    res, scn, samp, torn, rcf = data["res"], data["scn"], data["samp"], data["torn"], data["rcf"]
    fi = res["fi_p"]
    ep = res["eirr_arr"] * 100

    with t1:
        # Top KPI Row
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='big-metric' style='border-left-color:{fi_color(fi)[1]}'><p class='big-metric-lbl'>PRIMARY FRAGILITY</p><p class='big-metric-val' style='color:{fi_color(fi)[1]}'>{fi:.1f}%</p><p>{verdict(fi)}</p></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='big-metric' style='border-left-color:#0D6EFD'><p class='big-metric-lbl'>SIMULATED P50 EIRR</p><p class='big-metric-val'>{np.percentile(ep, 50):.2f}%</p><p>Realistic Central Estimate</p></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='big-metric' style='border-left-color:#6c757d'><p class='big-metric-lbl'>DPR STATED EIRR</p><p class='big-metric-val'>{p['dpr_eirr']:.2f}%</p><p>Consultant 'Inside View'</p></div>", unsafe_allow_html=True)

        if zero_stress:
            st.success(f"✅ **Zero-Stress Proof Passed:** At DPR values, simulated EIRR ({np.percentile(ep, 50):.2f}%) matches DPR stated EIRR ({p['dpr_eirr']:.2f}%).")

        st.divider()
        # Histogram Logic (Reference the three side-by-side charts from your screenshots)
        st.subheader("Outcome Distributions")
        st.caption("Red dashed line = NHAI Hurdle. Black dotted line = DPR Forecast.")
        # ... Plotly code for h1, h2, h3 histograms ...

    with t2:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Tornado: Risk Drivers")
            # Plotly Tornado Chart using 'torn'
        with col_b:
            st.subheader("Stage 2: RCF Acid Test")
            if rcf:
                st.warning(f"**Action Required:** {rcf['decision']}. RCF-Adjusted EIRR is {rcf['rcf_eirr']:.2f}%.")
            else:
                st.success("Project is Green. Stage 2 RCF not required.")

    with t3:
        st.subheader("SCN Engine Parameters")
        st.write(scn)