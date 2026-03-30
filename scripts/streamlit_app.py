"""
TruthShield ML Pipeline Dashboard
Functional Streamlit prototype for offline claim analysis with live Thompson Sampling.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
from math import lgamma

from src.ml.guardian.claim_router import ClaimRouter
from src.ml.guardian.source_ranker import SourceRanker
from src.ml.learning.bandit import (
    get_bandit, GuardianBandit, ToneVariant, SourceMixStrategy,
    BanditContext, BanditDecision, BetaDistribution,
)
from src.ml.learning.feedback import get_collector
from src.ml.learning.logging import get_learning_logger
from src.core.platform_config import get_platform_spec

from scripts.dashboard_helpers import (
    AVATARS, PLATFORMS, TONE_COLORS,
    mock_source_candidates, build_mock_response_text, check_api_status,
)

BANDIT_STATE_PATH = str(PROJECT_ROOT / "demo_data" / "ml" / "bandit_state.json")
FEEDBACK_DIR = str(PROJECT_ROOT / "demo_data" / "ml")
LOG_DIR = str(PROJECT_ROOT / "demo_data" / "ml" / "logs")


def _init():
    if "router" not in st.session_state:
        st.session_state.router = ClaimRouter()
        st.session_state.ranker = SourceRanker()
        st.session_state.bandit = get_bandit(BANDIT_STATE_PATH)
        st.session_state.collector = get_collector(FEEDBACK_DIR)
        st.session_state.ml_logger = get_learning_logger(LOG_DIR)
        st.session_state.history = []


def _beta_pdf(x, a, b):
    log_norm = lgamma(a + b) - lgamma(a) - lgamma(b)
    return np.exp(log_norm + (a - 1) * np.log(x) + (b - 1) * np.log(1 - x))


# --- Page config ---
st.set_page_config(page_title="TruthShield ML Dashboard", page_icon="🛡️", layout="wide")
_init()

# --- Sidebar ---
with st.sidebar:
    st.title("TruthShield")
    st.caption("ML Pipeline Dashboard")
    st.divider()
    st.subheader("API Status")
    for label, ok in check_api_status().items():
        st.markdown(f"{'🟢' if ok else '🔴'} {label}")
    st.divider()
    st.subheader("Pipeline Stats")
    hist = st.session_state.history
    st.metric("Claims Analysed", len(hist))
    scores = [h["feedback"] for h in hist if h.get("feedback") is not None]
    if scores:
        st.metric("Avg Feedback", f"{sum(scores)/len(scores):.1f}")
    tone_counts = {}
    for h in hist:
        t = h.get("tone", "?")
        tone_counts[t] = tone_counts.get(t, 0) + 1
    if tone_counts:
        st.metric("Favourite Tone", max(tone_counts, key=tone_counts.get).title())

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Claim Analyse", "Thompson Sampling Monitor", "Response History"])

# ====================== TAB 1: CLAIM ANALYSIS ============================
with tab1:
    st.header("Claim Analyse")
    col_in, col_out = st.columns([1, 2])

    with col_in:
        claim_text = st.text_area("Claim eingeben", placeholder='z.B. "mRNA-Impfungen veraendern die DNA"', height=120)
        platform = st.selectbox("Platform", PLATFORMS)
        avatar = st.selectbox("Avatar Persona", AVATARS)
        run = st.button("Analysieren & Antwort generieren", type="primary")

    with col_out:
        if run and claim_text.strip():
            bandit: GuardianBandit = st.session_state.bandit

            with st.spinner("Analysiere Claim..."):
                analysis = st.session_state.router.analyze_claim(claim_text)

            candidates = mock_source_candidates(analysis)
            ranked = st.session_state.ranker.rank_sources(
                candidates=candidates, claim_keywords=analysis.keywords,
                claim_type=analysis.claim_types[0].value if analysis.claim_types else None,
            )
            ctx = BanditContext(
                claim_type=analysis.claim_types[0].value if analysis.claim_types else "unknown",
                risk_level=analysis.risk_level.value, language=analysis.language,
                time_of_day=datetime.now().hour,
            )
            decision = bandit.make_decision(ctx)
            selected_sources = [s.model_dump() for s in ranked]
            response_text = build_mock_response_text(analysis, decision.tone_variant, selected_sources, platform)

            st.session_state.last_analysis = analysis
            st.session_state.last_decision = decision
            st.session_state.last_response = response_text
            st.session_state.last_sources = selected_sources

            # -- Claim Analysis Card --
            st.subheader("Claim Analysis")
            c1, c2, c3, c4 = st.columns(4)
            types_disp = ", ".join(ct.value.replace("_", " ").title() for ct in analysis.claim_types[:2])
            c1.metric("Claim Type", types_disp)
            c2.metric("Risk Level", analysis.risk_level.value.upper())
            c3.metric("Volatility", analysis.volatility.value.title())
            c4.metric("IO Score", f"{analysis.io_score:.2f}")

            rm = analysis.response_mode_result
            if rm:
                mode_str = rm.primary.value + (f" + {rm.secondary.value}" if rm.secondary else "")
                st.info(f"Response Mode: **{mode_str}** — {rm.mode_reason}")

            # -- Selected Sources --
            st.subheader("Selected Sources")
            for i, s in enumerate(selected_sources[:3], 1):
                st.markdown(f"**{i}.** {s.get('title','—')} — `{s.get('source_class','?')}` (score: {s.get('final_score',0):.2f})")

            # -- Bandit Decision --
            st.subheader("Bandit Decision")
            b1, b2, b3 = st.columns(3)
            tone_val = decision.tone_variant.value
            color = TONE_COLORS.get(tone_val, "#666")
            b1.markdown(f"Tone: <span style='color:{color};font-weight:bold'>{tone_val.upper()}</span>", unsafe_allow_html=True)
            b2.markdown(f"Source Mix: **{decision.source_mix.value}**")
            b3.markdown(f"Pending: **{len(bandit.pending_decisions)}**")

            # -- Response --
            st.subheader("Generated Response")
            spec = get_platform_spec(platform)
            st.caption(f"{spec.name} | Max {spec.max_chars} chars | {spec.sentences[0]}-{spec.sentences[1]} sentences")
            st.success(response_text)
        elif run:
            st.warning("Bitte einen Claim eingeben.")

    # -- Feedback --
    st.divider()
    if st.session_state.get("last_decision"):
        st.subheader("Feedback")
        f1, f2, f3 = st.columns([1, 1, 2])
        good = f1.button("👍 Gut")
        bad = f2.button("👎 Schlecht")
        with f3:
            score_slider = st.slider("Engagement Score (0-10)", 0, 10, 5, key="fb_slider")
            submit_detail = st.button("Detailliertes Feedback senden")

        fb_val = 8.0 if good else (2.0 if bad else (float(score_slider) if submit_detail else None))

        if fb_val is not None:
            decision = st.session_state.last_decision
            bandit = st.session_state.bandit
            norm = fb_val / 10.0
            metrics = {"top_comment_proxy": norm, "reply_quality": norm, "like_reply_ratio": max(0.3, norm), "shares_proxy": norm * 0.5, "reports_rate": 0.0, "toxicity_in_replies": 0.0}
            reward = bandit.update(decision.decision_id, metrics)

            analysis = st.session_state.last_analysis
            st.session_state.history.append({
                "timestamp": datetime.now().isoformat(), "claim": analysis.normalized_claim[:80],
                "claim_type": ", ".join(ct.value for ct in analysis.claim_types[:2]),
                "risk": analysis.risk_level.value, "tone": decision.tone_variant.value,
                "response": st.session_state.last_response[:100], "feedback": fb_val, "reward": reward,
            })
            st.success(f"Bandit aktualisiert! Reward: **{reward:.3f}** (Tone: {decision.tone_variant.value}, Score: {fb_val}/10)")
            st.session_state.last_decision = None

# ===================== TAB 2: THOMPSON SAMPLING ===========================
with tab2:
    st.header("Thompson Sampling Monitor")
    bandit = st.session_state.bandit
    arm_stats = bandit.get_arm_stats()

    # Tone arms
    st.subheader("Tone Variant Arms")
    tone_data = arm_stats.get("tone_arms", {})
    cols = st.columns(4)
    for i, (name, data) in enumerate(tone_data.items()):
        d, s = data["distribution"], data["stats"]
        cols[i].markdown(f"**{name.upper()}**\nα:{d['alpha']:.1f} β:{d['beta']:.1f}\nMean:{data['mean']:.3f}\nPulls:{s['pulls']} Avg:{s['avg_reward']:.3f}")

    st.subheader("Beta Distributions – Tone")
    x = np.linspace(0.005, 0.995, 200)
    df_tone = pd.DataFrame({n: _beta_pdf(x, d["distribution"]["alpha"], d["distribution"]["beta"]) for n, d in tone_data.items()}, index=np.round(x, 3))
    st.line_chart(df_tone, use_container_width=True)

    if st.session_state.history:
        st.subheader("Tone Selection History")
        st.bar_chart(pd.Series([h["tone"] for h in st.session_state.history]).value_counts())

    st.divider()
    st.subheader("Source Mix Arms")
    src_data = arm_stats.get("source_arms", {})
    scols = st.columns(3)
    for i, (name, data) in enumerate(src_data.items()):
        d, s = data["distribution"], data["stats"]
        scols[i].markdown(f"**{name}**\nα:{d['alpha']:.1f} β:{d['beta']:.1f}\nMean:{data['mean']:.3f}\nPulls:{s['pulls']}")

    df_src = pd.DataFrame({n: _beta_pdf(x, d["distribution"]["alpha"], d["distribution"]["beta"]) for n, d in src_data.items()}, index=np.round(x, 3))
    st.line_chart(df_src, use_container_width=True)

    st.divider()
    if st.button("Bandit auf Prior zuruecksetzen"):
        for arm in bandit.tone_arms:
            bandit.tone_arms[arm] = BetaDistribution(1.0, 1.0)
            bandit.tone_stats[arm].pulls = 0
            bandit.tone_stats[arm].total_reward = 0.0
            bandit.tone_stats[arm].avg_reward = 0.0
        for arm in bandit.source_arms:
            bandit.source_arms[arm] = BetaDistribution(1.0, 1.0)
            bandit.source_stats[arm].pulls = 0
            bandit.source_stats[arm].total_reward = 0.0
            bandit.source_stats[arm].avg_reward = 0.0
        bandit.pending_decisions.clear()
        if bandit.state_path:
            bandit._save_state()
        st.success("Bandit reset to uniform prior (α=1, β=1).")
        st.rerun()

# ====================== TAB 3: RESPONSE HISTORY ==========================
with tab3:
    st.header("Response History")
    if not st.session_state.history:
        st.info("Noch keine Analysen. Starte auf dem 'Claim Analyse' Tab.")
    else:
        df = pd.DataFrame(st.session_state.history)
        show = [c for c in ["timestamp","claim","claim_type","risk","tone","response","feedback","reward"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True)
        st.divider()
        st.download_button("Export als JSON", data=json.dumps(st.session_state.history, indent=2, default=str),
                           file_name=f"truthshield_history_{datetime.now():%Y%m%d_%H%M}.json", mime="application/json")
