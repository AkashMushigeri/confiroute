"""ConfiRoute — Clinician Human Review Queue.

Streamlit interface allowing medical experts to inspect, approve, edit,
or reject low-confidence and high-risk escalated medical queries.
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from confiroute.db.database import (
    get_pending_reviews,
    record_review_decision,
    get_resolved_reviews,
    init_db,
)

st.set_page_config(
    page_title="Reviewer Queue — ConfiRoute",
    page_icon="🩺",
    layout="wide",
)

init_db()

# Styling
st.markdown(
    """
    <style>
    .case-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .tag-high-risk {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .tag-low-conf {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
        display: inline-block;
    }
    .draft-box {
        background-color: #f8fafc;
        border-left: 4px solid #f59e0b;
        padding: 10px 14px;
        margin: 10px 0;
        border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🩺 Clinician Human Review Queue")
st.caption("Human-in-the-Loop review interface for low-certainty and high-risk medical escalations.")

# Research disclaimer
st.info(
    "🔒 **Research & Local Prototype Notice:** This queue is intended for research demonstrations and clinical audit. "
    "Production deployments require institutional authentication, RBAC, and HIPAA compliance."
)

tab_pending, tab_audit = st.tabs(["⏳ Pending Reviews", "📋 Resolved Cases & Audit Log"])

with tab_pending:
    pending_cases = get_pending_reviews(limit=50)

    if not pending_cases:
        st.success("🎉 No pending cases in the review queue. All submitted queries have been resolved or answered directly.")
    else:
        st.subheader(f"Cases Awaiting Review ({len(pending_cases)})")

        for i, item in enumerate(pending_cases, 1):
            qid = item["id"]
            question = item["question"]
            options = item.get("options", {})
            ai_draft = item.get("ai_draft_answer", "N/A")
            is_risk = item.get("is_high_risk", 0)
            risk_reason = item.get("risk_reason")
            esc_reason = item.get("reason", "Escalated for review")
            score = item.get("combined")

            with st.container():
                st.markdown(f"### Case #{i}: `{qid}`")

                # Tags
                col_tags1, col_tags2 = st.columns([3, 1])
                with col_tags1:
                    if is_risk:
                        st.markdown(f'<span class="tag-high-risk">⚠️ HIGH RISK: {risk_reason}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="tag-low-conf">⚠️ LOW CERTAINTY (Score: {score:.2f})</span>', unsafe_allow_html=True)
                with col_tags2:
                    st.caption(f"Submitted: {item.get('created_at', '')}")

                # Question and options display
                st.markdown(f"**Medical Query:**\n> {question}")

                col_opts1, col_opts2 = st.columns(2)
                with col_opts1:
                    st.write(f"**A:** {options.get('A', '')}")
                    st.write(f"**C:** {options.get('C', '')}")
                with col_opts2:
                    st.write(f"**B:** {options.get('B', '')}")
                    st.write(f"**D:** {options.get('D', '')}")

                # AI Draft details
                st.markdown(
                    f"""
                    <div class="draft-box">
                    <strong>AI Proposed Draft (Withheld from user):</strong> Option <strong>{ai_draft}</strong> (<em>{options.get(ai_draft, '')}</em>)<br/>
                    <strong>Escalation Reason:</strong> {esc_reason}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Review Action Form
                with st.form(key=f"review_form_{qid}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        rev_name = st.text_input(
                            "Reviewer Name / ID",
                            value=st.session_state.get("reviewer_name", "Dr. Clinician"),
                            key=f"name_{qid}",
                        )
                        decision = st.radio(
                            "Action Decision",
                            ["Approve AI Draft", "Edit / Provide Correct Answer", "Reject Case (Do not answer)"],
                            key=f"action_{qid}",
                        )

                    with c2:
                        corrected_choice = None
                        if "Edit" in decision:
                            option_keys = list(options.keys()) if options else ["A", "B", "C", "D"]
                            corrected_choice = st.selectbox(
                                "Select Clinically Correct Option:",
                                option_keys,
                                key=f"corr_{qid}",
                            )
                        notes = st.text_area(
                            "Clinical Justification / Audit Notes",
                            placeholder="Add reason for approval, correction, or rejection...",
                            key=f"notes_{qid}",
                        )

                    submitted_review = st.form_submit_button("✅ Submit Decision to ConfiRoute", use_container_width=True)

                    if submitted_review:
                        st.session_state["reviewer_name"] = rev_name
                        action_map = {
                            "Approve AI Draft": "approved",
                            "Edit / Provide Correct Answer": "edited",
                            "Reject Case (Do not answer)": "rejected",
                        }
                        dec_key = action_map[decision]

                        record_review_decision(
                            query_id=qid,
                            reviewer_name=rev_name,
                            decision=dec_key,
                            corrected_answer=corrected_choice if dec_key == "edited" else None,
                            notes=notes,
                        )
                        st.success(f"Case `{qid}` successfully updated ({decision}). Response updated in database.")
                        st.rerun()

                st.markdown("---")

with tab_audit:
    st.subheader("Review History & Audit Trail")
    resolved = get_resolved_reviews(limit=50)
    if not resolved:
        st.info("No resolved reviews recorded yet.")
    else:
        import pandas as pd
        df_audit = pd.DataFrame(resolved)
        st.dataframe(
            df_audit[[
                "query_id", "decision", "reviewer_name", "ai_draft_answer",
                "final_answer", "notes", "reviewed_at"
            ]],
            use_container_width=True,
        )
