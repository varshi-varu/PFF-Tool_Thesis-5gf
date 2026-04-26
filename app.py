import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io
import json

# ── Engine import ──────────────────────────────────────────────────────────────
try:
    from pfff_engine import (
        PROJECTS, MODES, HURDLES, C,
        compute_scn, run_mcs, simulate_mode,
        spearman_tornado, rcf_acid_test, eirr_iter,
        fi_color, verdict,
    )
except ImportError as e:
    st.error("Cannot import pfff_engine.py — place it in the same folder.")
    st.stop()

# ── Page config & CSS ──────────────────────────────────────────────────────────
st.set_page_config(page_title="PFFF v11 — NHAI DPR Auditor", page_icon="🏛️", layout="wide")

# CSS to fix top cut-off and make metrics big
st.markdown("""
<style>
    .block-container {padding-top: 2rem;}
    .big-metric {background:#f8f9fa; border-radius:10px; padding:20px; border-left:8px solid; text-align:center;}
    .big-metric-val {font-size:3.5rem; font-weight:800; margin:0;}
    .big-metric-lbl {font-size:1.1rem; color:#6c757d; font-weight:600;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 50px; font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏛️ Project Parameters")
    tmpl = st.selectbox("Load DPR Template", list(PROJECTS.keys()), format_func=lambda c: PROJECTS[c]["name"])
    
    if st.button("📂 Load Data", use_container_width=True):
        st.session_state["loaded_p"] = dict(PROJECTS[tmpl])

    if "loaded_p" not in st.session_state:
        st.session_state["loaded_p"] = dict(PROJECTS["P2"])
    
    p = st.session_state["loaded_p"]
    
    st.divider()
    run_btn = st.button("🚀 RUN FORENSIC AUDIT", type="primary", use_container_width=True)
    st.divider()
    
    # Inputs grouped as requested
    with st.expander("📝 Project Identity", expanded=True):
        p["name"] = st.text_input("Name", p["name"])
        p["state"] = st.text_input("State", p.get("state",""))
        p["dpr_mode"] = st.selectbox("DPR Mode", MODES, index=MODES.index(p.get("dpr_mode","EPC")))
    
    with st.expander("🏗️ SCN Risk Sliders", expanded=True):
        p["la_pct"] = st.slider("LA% Complete", 0, 100, int(p.get("la_pct",50)))
        p["geotech"] = st.select_slider("Geotech", ["DESKTOP","PARTIAL","COMPLETE"], value=p.get("geotech","PARTIAL"))
        p["contractor"] = st.select_slider("Contractor", ["STRESSED","ADEQUATE","STRONG"], value=p.get("contractor","ADEQUATE"))

# ── Main UI ───────────────────────────────────────────────────────────────────
tab0, tab1, tab2, tab3 = st.tabs(["🏠 OVERVIEW", "📊 AUDIT DASHBOARD", "🔬 ADVANCED INSIGHTS", "📋 DATA AUDIT"])

with tab0:
    st.title("Welcome to PFFF v11.0")
    st.markdown("""
    ### Probabilistic Feasibility Fragility Framework
    This tool converts deterministic **Detailed Project Reports (DPRs)** into probabilistic forensic audits.
    
    **How to use:**
    1. Select a project from the sidebar templates.
    2. Adjust the **SCN (Site-Condition-Network)** sliders to reflect current site reality.
    3. Click **Run Forensic Audit** to simulate 10,000 parallel project outcomes.
    4. Review the **Fragility Index (FI)** to see the probability of project failure.
    """)
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/0/02/NHAI_logo.svg/1200px-NHAI_logo.svg.png", width=200)

with tab1:
    if run_btn or "res" in st.session_state:
        # Simulation Logic
        p_json = json.dumps(p, default=str)
        scn = compute_scn(p)
        samp = run_mcs(p, scn, 10000)
        res = simulate_mode(p, scn, samp, p["dpr_mode"], 10000)
        st.session_state["res"] = (res, scn, samp)
        
        # Big Metric Row
        fi = res["fi_p"]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='big-metric' style='border-left-color:{fi_color(fi)[1]}'><p class='big-metric-lbl'>PRIMARY FRAGILITY</p><p class='big-metric-val' style='color:{fi_color(fi)[1]}'>{fi:.1f}%</p><p>{verdict(fi)}</p></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='big-metric' style='border-left-color:#0D6EFD'><p class='big-metric-lbl'>SIMULATED P50 EIRR</p><p class='big-metric-val'>{np.percentile(res['eirr_arr']*100, 50):.2f}%</p><p>Hurdle: 12.0%</p></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='big-metric' style='border-left-color:#6c757d'><p class='big-metric-lbl'>DPR STATED EIRR</p><p class='big-metric-val'>{p['dpr_eirr']:.2f}%</p><p>Consultant Inside View</p></div>", unsafe_allow_html=True)

        st.divider()
        
        # The Histograms
        st.subheader("Simulated Outcome Distributions (10,000 Iterations)")
        h1, h2, h3 = st.columns(3)
        # (Standard Plotly histogram logic goes here - referencing make_hist from previous code)
        
        st.info("💡 **SCN Insight:** High Fragility is often driven by the gap between the DPR Stated EIRR and the Simulated P50 EIRR.")

with tab2:
    if "res" in st.session_state:
        st.subheader("Stage 2 — RCF Acid Test (Prescriptive Response)")
        # Display the Red/Amber RCF logic from engine
        # Display Spearman Tornado to show "What is driving the failure?"

with tab3:
    st.subheader("Raw SCN Parameters")
    st.json(scn)