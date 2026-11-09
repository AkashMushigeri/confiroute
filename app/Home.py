"""ConfiRoute — Confidence-Aware LLM Routing System.

Streamlit Demonstration Web Application with Multi-Provider Support
and Clinician Human Review Escalation.
"""

import sys
import os
import socket
from pathlib import Path
import streamlit as st

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from confiroute.config import get_config
from confiroute.routing.router import route_query
from confiroute.db.database import save_pipeline_execution, get_recent_history, init_db

# Configure Page
st.set_page_config(
    page_title="ConfiRoute — Confidence-Aware Medical Routing",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Minimalist Blue, White, Gray, Traffic Light Badges)
st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }
    .badge-demo {
        background-color: #1e3a8a;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
        display: inline-block;
        margin-bottom: 12px;
    }
    .badge-live {
        background-color: #047857;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
        display: inline-block;
        margin-bottom: 12px;
    }
    .disclaimer-box {
        background-color: #f1f5f9;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 4px;
        font-size: 0.88rem;
        color: #334155;
        margin-bottom: 16px;
    }
    .status-badge-green {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #86efac;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1.05rem;
    }
    .status-badge-yellow {
        background-color: #fef9c3;
        color: #854d0e;
        border: 1px solid #fde047;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1.05rem;
    }
    .status-badge-red {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1.05rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure database is ready
init_db()
config = get_config()


def check_ollama_port(host="localhost", port=11434, timeout=0.4) -> bool:
    """Quick socket check if Ollama is listening locally."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# Presets for Deterministic Testing of the 3 States
PRESETS = {
    "Select a preset...": None,
    "🟢 High Confidence (Direct Answer)": {
        "question": "Which vitamin deficiency is the specific cause of Wernicke encephalopathy?",
        "options": {
            "A": "Vitamin B1 (Thiamine)",
            "B": "Vitamin C (Ascorbic acid)",
            "C": "Vitamin D (Cholecalciferol)",
            "D": "Vitamin K",
        },
        "level": "high",
        "description": "Clear factual question where simulated confidence is high (score >= 0.80).",
    },
    "🟡 Moderate Confidence (Escalate to Tier 2)": {
        "question": "What is the second-line alternative for refractory atypical bacterial sinus infection?",
        "options": {
            "A": "Levofloxacin",
            "B": "Doxycycline monohydrate",
            "C": "Clindamycin oral suspension",
            "D": "Azithromycin extended release",
        },
        "level": "medium",
        "description": "Subtle clinical scenario with moderate ambiguity (0.50 <= score < 0.80).",
    },
    "🔴 Low Confidence (Hold for Human Review)": {
        "question": "An undifferentiated metabolic acidosis presents with normal anion gap and hyperchloremia. What is the definitive proximal tubule etiology?",
        "options": {
            "A": "Type 1 RTA with calcium stones",
            "B": "Type 2 RTA with Fanconi syndrome",
            "C": "Type 4 RTA hypoaldosteronism",
            "D": "Salicylate intoxication mixed disorder",
        },
        "level": "low",
        "description": "High model ambiguity / conflicting samples causing score < 0.50.",
    },
    "🔴 High-Risk Override (Dosage / Poisoning Emergency)": {
        "question": "What is the recommended IV loading dose of Magnesium Sulfate for severe pre-eclampsia eclampsia prophylaxis?",
        "options": {
            "A": "4 to 6 grams IV over 15-20 minutes followed by 1-2 g/hr",
            "B": "20 grams rapid IV push",
            "C": "500 mg oral tablet single dose",
            "D": "50 mg subcutaneous every 6 hours",
        },
        "level": "high",
        "description": "Question contains dosage/emergency keywords; overrides high score directly to clinical review.",
    },
}

# Sidebar: Provider Selection & System Health
with st.sidebar:
    st.header("⚙️ Execution Mode")
    provider_mode = st.radio(
        "Provider Engine:",
        ["Mock Engine (Offline / ₹0)", "Real AI (Ollama + Groq)"],
        index=0,
    )
    is_real_mode = "Real AI" in provider_mode
    active_provider = "real" if is_real_mode else "mock"

    st.markdown("---")
    st.subheader("Model Status")

    ollama_live = check_ollama_port()
    if ollama_live:
        st.success("🟢 Local Ollama: Online (:11434)")
    else:
        st.info("⚪ Local Ollama: Offline (Mock fallback)")

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.strip():
        st.success("🟢 Groq API: Key Configured")
    else:
        st.info("⚪ Groq API: Key Missing in .env")

    st.markdown("---")
    st.header("📐 Routing Thresholds & Calibration")
    st.markdown(
        f"""
        - **Direct Answer (Green):** $\\ge {config.threshold_high:.2f}$
        - **Tier 2 Escalation (Yellow):** $[{config.threshold_low:.2f}, {config.threshold_high:.2f})$
        - **Tier 2 Acceptance:** $\\ge {config.tier2_accept:.2f}$
        - **Human Review (Red):** $< {config.threshold_low:.2f}$
        - **High-Risk Medical Override:** Active

        **Signal Weights:**
        - S1 Token Prob: `{config.weight_s1*100:.0f}%`
        - S2 Self-Consistency: `{config.weight_s2*100:.0f}%`
        - S3 Self-Rated: `{config.weight_s3*100:.0f}%`
        
        **Calibration Status:**
        - Meta-Model: Platt Scaling / Isotonic ready
        - Current Mode: Dynamic Redistributed Average
        """
    )
    st.markdown("---")
    st.subheader("📑 Application Pages")
    st.markdown(
        """
        - 🩺 [Reviewer Queue](/Reviewer_Queue)
        - ⚖️ [Side-by-Side View](/Side_by_Side)
        - 📊 [Analytics Dashboard](/Dashboard)
        """
    )

# Header Section
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    if not is_real_mode:
        st.markdown('<div class="badge-demo">DEMO MODE — SIMULATED AI OUTPUT</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-live">LIVE MODE — REAL AI PROVIDERS</div>', unsafe_allow_html=True)
    st.title("ConfiRoute")
    st.subheader("Confidence-Aware LLM Routing System that Escalates Low-Certainty Cases to Humans")
with col_head2:
    st.metric("System Provider", "Mock Tier 1" if not is_real_mode else "Ollama / Groq", "₹0 Budget")

# Disclaimer
st.markdown(
    """
    <div class="disclaimer-box">
    <strong>⚠️ Research Prototype Disclaimer:</strong> This application is an AI safety research prototype evaluated on exam-style medical QA benchmarks (MedMCQA).
    It does <strong>NOT</strong> provide clinical advice. Low-confidence questions and high-risk medical topics automatically escalate to human clinician review.
    </div>
    """,
    unsafe_allow_html=True,
)

# Preset Selector
selected_preset_name = st.selectbox(
    "💡 Choose a Deterministic Test Case or enter custom question below:",
    list(PRESETS.keys()),
)

preset_data = PRESETS[selected_preset_name]

# Default values based on preset
if preset_data:
    default_q = preset_data["question"]
    default_a = preset_data["options"]["A"]
    default_b = preset_data["options"]["B"]
    default_c = preset_data["options"]["C"]
    default_d = preset_data["options"]["D"]
    sim_level = preset_data.get("level")
    st.info(f"**Preset Detail:** {preset_data['description']}")
else:
    default_q = "Which of the following is the standard first-line treatment for uncomplicated community-acquired pneumonia?"
    default_a = "Amoxicillin"
    default_b = "Ciprofloxacin"
    default_c = "Gentamicin"
    default_d = "Vancomycin"
    sim_level = None

# Input Form
with st.form("medical_query_form"):
    q_input = st.text_area("Medical Question", value=default_q, height=90)
    col_a, col_b = st.columns(2)
    with col_a:
        opt_a = st.text_input("Option A", value=default_a)
        opt_c = st.text_input("Option C", value=default_c)
    with col_b:
        opt_b = st.text_input("Option B", value=default_b)
        opt_d = st.text_input("Option D", value=default_d)

    submitted = st.form_submit_button("🛡️ Submit Question to ConfiRoute", use_container_width=True)

if submitted:
    options_dict = {"A": opt_a, "B": opt_b, "C": opt_c, "D": opt_d}

    with st.spinner("Calculating confidence signals, checking safety rules, and routing..."):
        decision = route_query(
            question=q_input,
            options=options_dict,
            model_key="tier1",
            simulated_level=sim_level,
            provider=active_provider,
        )

        query_id = save_pipeline_execution(
            question=q_input,
            options=options_dict,
            decision=decision,
            subject="Clinical Medicine",
            topic="General",
        )

    st.markdown("---")
    st.header("📋 Routing & Confidence Results")

    # Traffic Light Status Banner
    col_status, col_score = st.columns([2, 1])
    with col_status:
        if decision.color == "green":
            st.markdown(
                f'<div class="status-badge-green">🟢 ROUTE: DIRECT ANSWER (High Certainty)</div>',
                unsafe_allow_html=True,
            )
        elif decision.color == "yellow":
            st.markdown(
                f'<div class="status-badge-yellow">🟡 ROUTE: TIER 2 ESCALATION (Moderate Certainty)</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-badge-red">🔴 ROUTE: HELD FOR CLINICAL REVIEW (Human Queue)</div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"**Decision Reason:** {decision.reason}")

    with col_score:
        comb_val = decision.scores.get("combined")
        comb_str = f"{comb_val:.2f}" if comb_val is not None else "N/A"
        st.metric("Combined Confidence Score", comb_str, f"Threshold: {config.threshold_high:.2f}")

    # Answer Presentation Box
    st.subheader("💡 System Answer Status")
    if decision.route == "direct":
        st.success(
            f"**Answer Released ({decision.tier_used.upper()}):** Option **{decision.final_answer}** — "
            f"*{options_dict.get(decision.final_answer, '')}*"
        )
    elif decision.route == "tier2":
        st.warning(
            f"**Pending Stronger Model:** The preliminary model chose Option **{decision.ai_draft_answer}**, "
            "but confidence is below the direct answer threshold. Awaiting Tier 2 re-evaluation."
        )
    else:
        st.error(
            f"**Held for Human Review:** AI draft answer (Option **{decision.ai_draft_answer}**) is withheld from the user "
            f"and routed to the clinician review queue. "
            f"{'Reason: High-risk medical topic (' + str(decision.risk_reason) + ')' if decision.is_high_risk else 'Reason: Confidence score below safety threshold.'}"
        )
        st.info("👉 Clinicians can review and release this case from the **1_Reviewer_Queue** page in the left sidebar.")

    # 3 Confidence Signal Metrics
    st.subheader("📊 Individual Confidence Signals")
    sig_col1, sig_col2, sig_col3, sig_col4 = st.columns(4)

    s1_val = decision.scores.get("s1")
    s2_val = decision.scores.get("s2")
    s3_val = decision.scores.get("s3")

    with sig_col1:
        st.metric(
            "S1: Token Probability",
            f"{s1_val:.2f}" if s1_val is not None else "Unavailable",
            f"Weight: {config.weight_s1*100:.0f}%",
        )
    with sig_col2:
        st.metric(
            "S2: Self-Consistency",
            f"{s2_val:.2f}" if s2_val is not None else "Unavailable",
            f"Weight: {config.weight_s2*100:.0f}%",
        )
    with sig_col3:
        st.metric(
            "S3: Self-Rated Certainty",
            f"{s3_val:.2f}" if s3_val is not None else "Unavailable",
            f"Weight: {config.weight_s3*100:.0f}%",
        )
    with sig_col4:
        eq_cost = decision.cost_metadata.get("equivalent_cost", 0.0)
        st.metric(
            "Equivalent Cost",
            f"${eq_cost:.5f}",
            "Real Cost: $0.00",
        )

    # Deep-dive expander
    with st.expander("🔍 Deep-Dive Diagnostic Breakdown"):
        st.json({
            "query_id": query_id,
            "routing_decision": decision.to_dict(),
            "cost_breakdown": {
                "real_cost_spent": "$0.00 (Zero-Cost Local / Free Tier)",
                "equivalent_benchmark_cost": f"${eq_cost:.6f} USD",
                "tokens_prompt": decision.tokens_used.get("prompt_tokens"),
                "tokens_completion": decision.tokens_used.get("completion_tokens"),
            },
        })

# Query History Section
st.markdown("---")
st.subheader("📜 Recent Query History (Logged to SQLite)")
history = get_recent_history(limit=10)
if history:
    import pandas as pd
    df_hist = pd.DataFrame(history)
    display_cols = ["id", "question", "combined", "route", "status", "final_answer", "is_high_risk", "reason", "created_at"]
    present_cols = [c for c in display_cols if c in df_hist.columns]
    st.dataframe(df_hist[present_cols], use_container_width=True)
else:
    st.caption("No queries recorded in SQLite database yet.")
