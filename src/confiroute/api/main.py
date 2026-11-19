"""FastAPI REST Service for ConfiRoute.

Provides endpoints for query routing, human clinician review queue,
case status resolution, system analytics, side-by-side comparison,
and frontend SPA distribution.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import csv
import io
import json
import re
from fastapi import FastAPI, HTTPException, status, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from confiroute.config import get_config
from confiroute.routing.router import route_query, RouteDecision
from confiroute.llm.base import ask_llm
from confiroute.confidence.combiner import format_mcq_prompt, extract_option_letter
from confiroute.alerts.alerts import check_and_record_alerts
from confiroute.db.connection import get_db_context
from confiroute.db.audit import record_audit_log
from confiroute.db.database import (
    init_db,
    save_pipeline_execution,
    get_pending_reviews,
    record_review_decision,
    get_query_result,
    get_system_stats,
    get_dashboard_query_records,
    get_active_alerts,
    authenticate_user,
    create_user_session,
    get_user_by_session_token,
    revoke_user_session,
    register_user,
    get_review_history,
    create_or_update_conversation,
    get_conversations,
    get_conversation,
    get_conversation_messages,
    save_conversation_message,
    delete_conversation,
    save_routing_log,
    get_routing_logs,
    save_human_review,
    get_admin_users,
    get_admin_conversations,
    get_admin_stats,
    get_admin_reviews,
)

# Initialize database schema
init_db()

config = get_config()

app = FastAPI(
    title="ConfiRoute API",
    description="Confidence-Aware LLM Routing and Safety Service for Medical Inquiries",
    version="0.3.0",
)

# CORS middleware for local frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


COMMON_PRESETS_OPTIONS: Dict[str, Dict[str, str]] = {
    "scurvy": {"A": "Vitamin C (ascorbic acid)", "B": "Vitamin B12", "C": "Vitamin D", "D": "Vitamin A"},
    "paracetamol": {"A": "Adults: max 4 g in 24 hours (1 g per dose)", "B": "8 g in 24 hours", "C": "500 mg every 24 hours", "D": "12 g single dose"},
    "pericarditis": {"A": "Pericarditis", "B": "Aortic dissection", "C": "Costochondritis", "D": "Stable angina"},
    "chest pain": {"A": "Pericarditis", "B": "Aortic dissection", "C": "Costochondritis", "D": "Stable angina"},
    "wernicke": {"A": "Vitamin B1 (Thiamine)", "B": "Vitamin C (Ascorbic acid)", "C": "Vitamin D (Cholecalciferol)", "D": "Vitamin K"},
    "anaphylaxis": {"A": "Intramuscular Epinephrine (Adrenaline)", "B": "Oral Diphenhydramine", "C": "Inhaled Albuterol", "D": "IV Hydrocortisone"},
    "acidosis": {"A": "Type 1 RTA with calcium stones", "B": "Type 2 RTA with Fanconi syndrome", "C": "Type 4 RTA hypoaldosteronism", "D": "Salicylate intoxication mixed disorder"},
    "magnesium": {"A": "4 to 6 grams IV over 15-20 minutes followed by 1-2 g/hr", "B": "20 grams rapid IV push", "C": "500 mg oral tablet single dose", "D": "50 mg subcutaneous every 6 hours"},
    "erythrocytes": {"A": "Synthesizing clotting factors", "B": "Digesting lipid macromolecules", "C": "Producing myelin sheaths", "D": "None of the above / Insufficient information"},
    "sinus": {"A": "Levofloxacin", "B": "Doxycycline monohydrate", "C": "Clindamycin oral suspension", "D": "Azithromycin extended release"},
    "insulin": {"A": "Beta cells", "B": "Alpha cells", "C": "Delta cells", "D": "Acinar cells"},
    "femoral": {"A": "Inguinal ligament, sartorius, adductor longus", "B": "Rectus femoris, gracilis, pectineus", "C": "Pectineus, iliopsoas, tensor fasciae latae", "D": "Adductor magnus, semitendinosus, sartorius"},
    "t waves": {"A": "Hyperkalemia", "B": "Hypokalemia", "C": "Hypercalcemia", "D": "Hypomagnesemia"},
    "night blindness": {"A": "Vitamin A deficiency (rhodopsin impairment)", "B": "Vitamin D deficiency", "C": "Niacin deficiency", "D": "Riboflavin deficiency"},
    "appendicitis": {"A": "Acute appendicitis", "B": "Mesenteric adenitis", "C": "Renal colic", "D": "Diverticulitis"},
    "barking cough": {"A": "Croup (Laryngotracheobronchitis)", "B": "Epiglottitis", "C": "Bronchiolitis", "D": "Foreign body aspiration"},
}


def resolve_or_synthesize_options(question: str, options: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Ensure question has valid candidate multiple-choice options."""
    if options and len(options) >= 2:
        return options

    q_lower = question.lower()
    for kw, opts in COMMON_PRESETS_OPTIONS.items():
        if kw in q_lower:
            return opts

    # Check if options are embedded inside the question text e.g. "A. ... B. ... C. ... D. ..."
    matches = re.findall(r"([A-D])[\.\:\)]\s*([^\n\r]+?)(?=(?:[A-D][\.\:\)]|$))", question)
    if len(matches) >= 2:
        return {letter.upper(): text.strip() for letter, text in matches}

    # Standard candidate options for general clinical inquiry
    return {
        "A": "Primary guideline-recommended medical intervention",
        "B": "Alternative differential diagnostic evaluation",
        "C": "Conservative symptomatic management with monitoring",
        "D": "Inconclusive / Urgent escalation to clinician review",
    }


def format_case_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw database record to frontend Case model."""
    opts = {}
    if "options" in row and isinstance(row["options"], dict):
        opts = row["options"]
    elif "options_json" in row and row["options_json"]:
        try:
            opts = json.loads(row["options_json"])
        except Exception:
            opts = {}

    draft_raw = row.get("ai_draft_answer") or ""
    final_raw = row.get("final_answer")

    def enrich_answer(ans: Optional[str]) -> Optional[str]:
        if not ans:
            return None
        ans_clean = str(ans).strip()
        if opts and ans_clean in opts:
            return f"Option {ans_clean} — {opts[ans_clean]}"
        return ans_clean

    tier1_answer = enrich_answer(draft_raw) or draft_raw
    final_answer = enrich_answer(final_raw) if final_raw else None

    # Status: "answered" | "pending" | "resolved"
    review_dec = row.get("review_decision")
    if review_dec or (row.get("status") in ("completed", "reviewed_approved", "reviewed_edited", "reviewed_rejected") and row.get("route") == "human"):
        status_val = "resolved"
    elif row.get("status") in ("pending_human", "pending_tier2") or (row.get("route") == "human" and row.get("status") != "completed"):
        status_val = "pending"
    else:
        status_val = "answered"

    color = row.get("color")
    if not color:
        color = "green" if row.get("route") == "direct" else ("yellow" if row.get("route") == "tier2" else "red")

    tier_used_num = 2 if row.get("tier_used") == "tier2" else 1

    review_obj = None
    if review_dec:
        rev_dec_norm = "approve" if review_dec == "approved" else ("edit" if review_dec == "edited" else "reject")
        review_obj = {
            "decision": rev_dec_norm,
            "edited_answer": enrich_answer(row.get("corrected_answer")),
            "note": row.get("notes") or "",
            "reviewer": row.get("reviewer_name") or "",
            "ts": row.get("reviewed_at") or row.get("created_at") or "",
        }

    return {
        "id": row.get("id") or row.get("query_id") or "q-0",
        "ts": row.get("created_at") or "",
        "question": row.get("question") or "",
        "options": opts if opts else None,
        "subject": row.get("subject") or "General Medicine",
        "tier1_answer": tier1_answer,
        "signals": {
            "s1": round(float(row.get("s1") or 0.0), 2),
            "s2": round(float(row.get("s2") or 0.0), 2),
            "s3": round(float(row.get("s3") or 0.0), 2),
        },
        "score": round(float(row.get("combined") or 0.0), 2),
        "risk_flag": bool(row.get("is_high_risk")),
        "risk_reason": row.get("risk_reason"),
        "route": row.get("route") or "human",
        "band": color,
        "status": status_val,
        "tier_used": tier_used_num,
        "tier2_answer": tier1_answer if tier_used_num == 2 else None,
        "tier2_score": round(float(row.get("combined")), 2) if tier_used_num == 2 and row.get("combined") is not None else None,
        "final_answer": final_answer,
        "reason": row.get("reason") or "",
        "calls": 2 if tier_used_num == 2 else 1,
        "cost_equiv": float(row.get("equivalent_cost") or 0.0),
        "review": review_obj,
    }


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Medical query or exam question")
    options: Optional[Dict[str, str]] = Field(default=None, description="Candidate multiple choice options (A, B, C, D)")
    model_key: str = Field("tier1", description="Target model tier: tier1 or tier2")
    provider: Optional[str] = Field(None, description="Provider override: mock, ollama, or groq")
    simulated_level: Optional[str] = Field(None, description="Optional simulation preset: high, medium, low")
    subject: Optional[str] = Field("General Medicine", description="Medical specialty / subject")
    topic: Optional[str] = Field("General", description="Clinical topic")


class AskResponse(BaseModel):
    query_id: str
    route: str
    status: str
    color: str
    final_answer: Optional[str]
    ai_draft_answer: str
    scores: Dict[str, Optional[float]]
    is_high_risk: bool
    risk_reason: Optional[str]
    reason: str
    tier_used: str
    cost_metadata: Dict[str, Any]
    tokens_used: Dict[str, int]
    is_mock: bool
    case: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    reviewer_name: str = Field(..., min_length=2, description="Name or identifier of reviewing clinician")
    decision: str = Field(..., description="Review action: approve/approved, edit/edited, reject/rejected")
    corrected_answer: Optional[str] = Field(None, description="Corrected option letter or answer text if edited")
    notes: Optional[str] = Field(None, description="Clinical justification or audit notes")


class ReviewResponse(BaseModel):
    query_id: str
    decision: str
    updated_status: str
    final_answer: Optional[str]
    reviewer_name: str
    message: str


class CompareRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Medical question to compare across systems")
    options: Optional[Dict[str, str]] = Field(default=None, description="Multiple choice options")
    subject: Optional[str] = Field("General Medicine", description="Subject area")
    simulated_level: Optional[str] = Field(None, description="Simulation preset")
    provider: Optional[str] = Field(None, description="Provider override")


# ---------------------------------------------------------------------------
# Auth & Session Request/Response Models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(..., description="Clinician or reviewer email")
    password: str = Field(..., min_length=4, description="Account password")
    remember_me: bool = Field(default=True, description="Extend session duration")


class LoginResponse(BaseModel):
    token: str
    user: Dict[str, Any]
    message: str = "Authenticated successfully"


class RegisterRequest(BaseModel):
    email: str = Field(..., description="Clinician email")
    password: str = Field(..., min_length=6, description="Account password")
    name: str = Field(..., description="Full clinician name / title (e.g. Dr. Sarah Chen)")
    role: str = Field(default="reviewer", description="User role: reviewer, admin, clinician")
    department: str = Field(default="Clinical Review", description="Department")


class ConversationCreateRequest(BaseModel):
    id: Optional[str] = None
    title: str = Field(default="Clinical Inquiry")
    subject: str = Field(default="General Medicine")


class ConversationMessageRequest(BaseModel):
    id: Optional[str] = None
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text content")
    options: Optional[Dict[str, str]] = None
    subject: Optional[str] = None
    query_id: Optional[str] = None


def extract_auth_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Helper to extract user record from Bearer token without raising exceptions."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
    return get_user_by_session_token(token)


def require_auth_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Helper enforcing valid authenticated clinician user session."""
    user = extract_auth_user(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with valid clinical credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Helper enforcing valid authenticated administrator session."""
    user = require_auth_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource.",
        )
    return user


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(req: LoginRequest) -> LoginResponse:
    """Authenticate clinician with email and password."""
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Use demo account clinician@confiroute.ai with Clinical2026!",
        )
    duration = 30 if req.remember_me else 1
    token = create_user_session(user["id"], duration_days=duration)
    try:
        with get_db_context() as db:
            record_audit_log(
                db=db,
                action="user_login",
                resource_type="auth",
                user_id=user["id"],
                resource_id=user["id"],
                details={"email": user["email"], "role": user["role"]},
            )
    except Exception:
        pass
    return LoginResponse(
        token=token,
        user=user,
        message="Clinician session successfully established.",
    )


@app.get("/auth/me", tags=["Authentication"])
def get_me(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Verify session token and retrieve current authenticated user."""
    user = require_auth_user(authorization)
    return {"user": user}


@app.post("/auth/logout", tags=["Authentication"])
def logout(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Revoke authenticated session token."""
    user = extract_auth_user(authorization)
    if authorization:
        token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
        revoke_user_session(token)
        if user:
            try:
                with get_db_context() as db:
                    record_audit_log(
                        db=db,
                        action="user_logout",
                        resource_type="auth",
                        user_id=user["id"],
                        resource_id=user["id"],
                    )
            except Exception:
                pass
    return {"message": "Session terminated successfully."}


@app.post("/auth/register", response_model=LoginResponse, tags=["Authentication"])
def register(
    req: RegisterRequest,
    authorization: Optional[str] = Header(None),
) -> LoginResponse:
    """Register a new verified clinical reviewer account."""
    # Prevent unauthorized privilege escalation to admin role
    assigned_role = req.role.strip().lower()
    if assigned_role == "admin":
        requester = extract_auth_user(authorization)
        if not requester or requester.get("role") != "admin":
            assigned_role = "reviewer"
    elif assigned_role not in ("reviewer", "clinician"):
        assigned_role = "reviewer"

    try:
        user = register_user(
            email=req.email,
            password=req.password,
            name=req.name,
            role=assigned_role,
            department=req.department,
        )
        token = create_user_session(user["id"], duration_days=7)
        try:
            with get_db_context() as db:
                record_audit_log(
                    db=db,
                    action="user_register",
                    resource_type="user",
                    user_id=user["id"],
                    resource_id=user["id"],
                    details={"email": user["email"], "role": user["role"]},
                )
        except Exception:
            pass
        return LoginResponse(
            token=token,
            user=user,
            message="Clinician account registered and authenticated.",
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """Return service health status."""
    return {
        "status": "healthy",
        "app_name": config.app_name,
        "version": config.version,
        "is_mock_mode": config.is_mock_mode,
    }


@app.post("/ask", response_model=AskResponse, tags=["Routing"])
def ask_question(req: AskRequest) -> AskResponse:
    """Submit a medical query for confidence-aware routing."""
    opts = resolve_or_synthesize_options(req.question, req.options)

    decision = route_query(
        question=req.question,
        options=opts,
        model_key=req.model_key,
        simulated_level=req.simulated_level,
        provider=req.provider,
    )

    query_id = save_pipeline_execution(
        question=req.question,
        options=opts,
        decision=decision,
        subject=req.subject,
        topic=req.topic,
    )

    try:
        save_routing_log(
            query_id=query_id,
            routing_decision=decision.route,
            selected_model=decision.tier_used,
            confidence_score=decision.scores.get("combined") if decision.scores else None,
            s1=decision.scores.get("s1") if decision.scores else None,
            s2=decision.scores.get("s2") if decision.scores else None,
            s3=decision.scores.get("s3") if decision.scores else None,
            risk_level="high" if decision.is_high_risk else "standard",
            is_high_risk=decision.is_high_risk,
            escalation_reason=decision.risk_reason or decision.reason,
            latency=decision.cost_metadata.get("latency_ms", 0.0) if decision.cost_metadata else 0.0,
        )
    except Exception:
        pass

    # Format answers
    def enrich(letter: Optional[str]) -> Optional[str]:
        if not letter:
            return None
        clean = str(letter).strip()
        if clean in opts:
            return f"Option {clean} — {opts[clean]}"
        return clean

    ai_draft_enriched = enrich(decision.ai_draft_answer) or decision.ai_draft_answer
    final_enriched = enrich(decision.final_answer) if decision.final_answer else None

    # Fetch full case representation for the frontend
    row = get_query_result(query_id)
    case_dict = format_case_dict(row) if row else None

    return AskResponse(
        query_id=query_id,
        route=decision.route,
        status=decision.status,
        color=decision.color,
        final_answer=final_enriched,
        ai_draft_answer=ai_draft_enriched,
        scores=decision.scores,
        is_high_risk=decision.is_high_risk,
        risk_reason=decision.risk_reason,
        reason=decision.reason,
        tier_used=decision.tier_used,
        cost_metadata=decision.cost_metadata,
        tokens_used=decision.tokens_used,
        is_mock=decision.is_mock,
        case=case_dict,
    )


@app.get("/queue", tags=["Reviewer Queue"])
def get_review_queue(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch pending medical cases awaiting human clinician review."""
    rows = get_pending_reviews(limit=limit)
    return [format_case_dict(r) for r in rows]


@app.post("/review/{query_id}", response_model=ReviewResponse, tags=["Reviewer Queue"])
def submit_review(
    query_id: str,
    review: ReviewRequest,
    authorization: Optional[str] = Header(None),
) -> ReviewResponse:
    """Review and resolve an escalated case (approve, edit, or reject)."""
    reviewer_name = review.reviewer_name
    if authorization:
        auth_user = extract_auth_user(authorization)
        if not auth_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired reviewer session. Please log in again.",
            )
        if auth_user.get("role") not in ("reviewer", "admin", "clinician"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Case reviews require clinical reviewer privileges.",
            )
        if not reviewer_name or reviewer_name in ("reviewer1", "Dr. Sarah Chen"):
            reviewer_name = auth_user.get("name") or reviewer_name

    existing = get_query_result(query_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found.",
        )

    dec_norm = {"approve": "approved", "edit": "edited", "reject": "rejected"}.get(
        review.decision.strip().lower(), review.decision.strip().lower()
    )

    if dec_norm == "edited" and not review.corrected_answer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A corrected answer is required when choosing 'edited'.",
        )

    result = record_review_decision(
        query_id=query_id,
        reviewer_name=reviewer_name,
        decision=dec_norm,
        corrected_answer=review.corrected_answer,
        notes=review.notes,
    )

    try:
        save_human_review(
            query_id=query_id,
            reviewer_name=reviewer_name,
            decision=dec_norm,
            review_status="completed" if dec_norm in ("approved", "edited") else "rejected",
            reviewer_id=auth_user.get("id") if (authorization and auth_user) else None,
            original_response=existing.get("ai_draft_answer"),
            corrected_response=review.corrected_answer,
            reviewer_feedback=review.notes,
            notes=review.notes,
        )
        if authorization and auth_user:
            with get_db_context() as db:
                record_audit_log(
                    db=db,
                    action="review_submit",
                    resource_type="review",
                    user_id=auth_user["id"],
                    resource_id=query_id,
                    details={"decision": dec_norm, "reviewer": reviewer_name},
                )
    except Exception:
        pass

    action_msg = {
        "approved": f"Case approved. AI draft answer ({result['final_answer']}) released to user.",
        "edited": f"Case updated with clinician correction: {result['final_answer']} released to user.",
        "rejected": "Case rejected by clinician. No answer released to user.",
    }.get(dec_norm, "Decision recorded.")

    return ReviewResponse(
        query_id=query_id,
        decision=result["decision"],
        updated_status=result["updated_status"],
        final_answer=result["final_answer"],
        reviewer_name=result["reviewer_name"],
        message=action_msg,
    )


@app.get("/reviews/history", tags=["Reviewer Queue"])
def get_review_history_endpoint(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    """Retrieve historical clinical reviewer audit records from database."""
    records = get_review_history(limit=limit)
    out = []
    for r in records:
        opts = {}
        if r.get("options_json"):
            try:
                opts = json.loads(r["options_json"])
            except Exception:
                opts = {}
        out.append({
            "review_id": r.get("review_id"),
            "query_id": r.get("query_id"),
            "reviewer_name": r.get("reviewer_name"),
            "decision": r.get("decision"),
            "corrected_answer": r.get("corrected_answer"),
            "notes": r.get("notes"),
            "reviewed_at": r.get("reviewed_at"),
            "question": r.get("question"),
            "options": opts,
            "subject": r.get("subject"),
            "route": r.get("route"),
            "status": r.get("status"),
            "color": r.get("color"),
            "score": round(float(r.get("combined") or 0.0), 2),
            "tier1_answer": r.get("ai_draft_answer"),
            "final_answer": r.get("final_answer"),
            "risk_flag": bool(r.get("is_high_risk")),
            "risk_reason": r.get("risk_reason"),
        })
    return out



@app.get("/result/{query_id}", tags=["Routing"])
def get_result(query_id: str) -> Dict[str, Any]:
    """Retrieve the routing status and released final answer for a query."""
    result = get_query_result(query_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found.",
        )
    res = dict(result)
    res["case"] = format_case_dict(result)
    return res


@app.get("/cases", tags=["Routing"])
def list_cases(
    subject: Optional[str] = Query(None, description="Filter by medical specialty"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(200, ge=1, le=1000, description="Max cases to return"),
) -> List[Dict[str, Any]]:
    """Retrieve historical queries and routing decisions formatted for the frontend."""
    records = get_dashboard_query_records(subject=subject, topic=topic, limit=limit)
    return [format_case_dict(r) for r in records]


@app.get("/stats", tags=["Analytics"])
def get_stats() -> Dict[str, Any]:
    """Return real-time database query, routing, and review statistics."""
    return get_system_stats()


@app.get("/alerts", tags=["Analytics"])
def get_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch active operational and clinical safety alerts."""
    try:
        check_and_record_alerts()
    except Exception:
        pass
    return get_active_alerts(limit=limit)


@app.post("/compare", tags=["Routing"])
def compare_systems(req: CompareRequest) -> Dict[str, Any]:
    """Side-by-side comparison between an unrouted LLM (B0) and ConfiRoute (B3)."""
    opts = resolve_or_synthesize_options(req.question, req.options)

    # 1. Baseline B0: Standard unrouted LLM (answers blindly)
    prompt_b0 = format_mcq_prompt(req.question, opts)
    resp_b0 = ask_llm(
        model_key="tier1",
        prompt=prompt_b0,
        temperature=0.0,
        simulated_level=req.simulated_level,
        provider=req.provider,
    )
    ans_b0_letter = extract_option_letter(resp_b0.text, opts)
    unrouted_text = (
        f"Option {ans_b0_letter} — {opts.get(ans_b0_letter, '')}"
        if ans_b0_letter in opts
        else resp_b0.text
    )

    # 2. ConfiRoute System B3
    decision = route_query(
        question=req.question,
        options=opts,
        model_key="tier1",
        simulated_level=req.simulated_level,
        provider=req.provider,
    )

    query_id = save_pipeline_execution(
        question=req.question,
        options=opts,
        decision=decision,
        subject=req.subject,
    )

    row = get_query_result(query_id)
    case_dict = format_case_dict(row) if row else None

    return {
        "unrouted": {
            "answer": unrouted_text,
            "letter": ans_b0_letter,
            "model": "tier1 (Small LLM)",
            "warning": "Blind Release: Answers with zero uncertainty detection, zero hallucination checks, and zero clinical safety screening.",
        },
        "confiroute": case_dict,
    }


@app.post("/seed", tags=["Development"])
def seed_traffic(count: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
    """Load real medical benchmark cases into the database for demonstration."""
    dev_path = config.root_dir / "data" / "processed" / "dev.jsonl"
    seeded_count = 0
    if dev_path.exists():
        with open(dev_path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()][:count]
        for item in lines:
            try:
                dec = route_query(
                    question=item["question"],
                    options=item["options"],
                    model_key="tier1",
                    provider="mock",
                )
                save_pipeline_execution(
                    question=item["question"],
                    options=item["options"],
                    decision=dec,
                    subject=item.get("subject", "General Medicine"),
                    topic=item.get("topic", "General"),
                )
                seeded_count += 1
            except Exception:
                continue

    return {
        "message": f"Successfully processed and seeded {seeded_count} clinical benchmark cases.",
        "count": seeded_count,
    }


@app.get("/export/csv", tags=["Analytics"])
def export_csv_file(subject: Optional[str] = None):
    """Download database query audit records as CSV."""
    records = get_dashboard_query_records(subject=subject, limit=1000)
    cases = [format_case_dict(r) for r in records]

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id", "ts", "question", "subject", "s1", "s2", "s3", "score",
            "risk_flag", "route", "band", "status", "tier_used",
            "tier1_answer", "final_answer", "reason", "calls",
            "reviewer", "decision", "note",
        ],
    )
    writer.writeheader()
    for c in cases:
        rev = c.get("review") or {}
        sig = c.get("signals") or {}
        writer.writerow({
            "id": c["id"],
            "ts": c["ts"],
            "question": c["question"],
            "subject": c["subject"],
            "s1": sig.get("s1", 0.0),
            "s2": sig.get("s2", 0.0),
            "s3": sig.get("s3", 0.0),
            "score": c["score"],
            "risk_flag": c["risk_flag"],
            "route": c["route"],
            "band": c["band"],
            "status": c["status"],
            "tier_used": c["tier_used"],
            "tier1_answer": c["tier1_answer"],
            "final_answer": c["final_answer"] or "",
            "reason": c["reason"],
            "calls": c["calls"],
            "reviewer": rev.get("reviewer", ""),
            "decision": rev.get("decision", ""),
            "note": rev.get("note", ""),
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=confiroute_query_records.csv"},
    )


# ---------------------------------------------------------------------------
# Persistent Chat Conversations Endpoints
# ---------------------------------------------------------------------------

@app.get("/conversations", tags=["Conversations"])
def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Retrieve chat conversation sessions for workspace sidebar."""
    user = extract_auth_user(authorization)
    user_id = user["id"] if user else None
    return get_conversations(user_id=user_id, limit=limit)


@app.post("/conversations", tags=["Conversations"])
def save_conversation(
    req: ConversationCreateRequest,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Create or update a conversation session with user isolation."""
    user = extract_auth_user(authorization)
    user_id = user["id"] if user else None
    conv_id = req.id or f"sess_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    saved = create_or_update_conversation(
        conversation_id=conv_id,
        title=req.title,
        user_id=user_id,
        subject=req.subject,
    )
    if user:
        try:
            with get_db_context() as db:
                record_audit_log(
                    db=db,
                    action="conversation_create",
                    resource_type="conversation",
                    user_id=user["id"],
                    resource_id=conv_id,
                    details={"title": req.title, "subject": req.subject},
                )
        except Exception:
            pass
    return saved


@app.get("/conversations/{conversation_id}", tags=["Conversations"])
def get_conversation_endpoint(
    conversation_id: str,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Retrieve full conversation details and all associated messages with ownership check."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found.")

    user = extract_auth_user(authorization)
    if user and user.get("role") != "admin":
        if conv.get("user_id") and conv["user_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not have permission to view this conversation.",
            )

    messages = get_conversation_messages(conversation_id)
    enriched_messages = []
    for m in messages:
        cdata = None
        if m.get("query_id"):
            q_row = get_query_result(m["query_id"])
            if q_row:
                cdata = format_case_dict(q_row)
        enriched_messages.append({
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "timestamp": m["created_at"],
            "options": m.get("options"),
            "subject": m.get("subject"),
            "caseData": cdata,
        })
    conv["messages"] = enriched_messages
    return conv


@app.post("/conversations/{conversation_id}/messages", tags=["Conversations"])
def append_conversation_message(
    conversation_id: str,
    req: ConversationMessageRequest,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Append a user or assistant message to the persistent conversation."""
    conv = get_conversation(conversation_id)
    user = extract_auth_user(authorization)
    if conv and user and user.get("role") != "admin":
        if conv.get("user_id") and conv["user_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot add messages to another clinician's conversation.",
            )

    msg_id = req.id or f"msg_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    saved = save_conversation_message(
        message_id=msg_id,
        conversation_id=conversation_id,
        role=req.role,
        content=req.content,
        options=req.options,
        subject=req.subject,
        query_id=req.query_id,
    )

    if req.query_id:
        try:
            save_routing_log(
                query_id=req.query_id,
                routing_decision="assistant_response",
                conversation_id=conversation_id,
                message_id=msg_id,
            )
        except Exception:
            pass

    return saved


@app.delete("/conversations/{conversation_id}", tags=["Conversations"])
def remove_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Delete a conversation session with ownership validation."""
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found.")

    user = extract_auth_user(authorization)
    if user and user.get("role") != "admin":
        if conv.get("user_id") and conv["user_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot delete another clinician's conversation.",
            )

    deleted = delete_conversation(
        conversation_id,
        user_id=user["id"] if user else None,
        is_admin=bool(user and user.get("role") == "admin"),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found.")

    if user:
        try:
            with get_db_context() as db:
                record_audit_log(
                    db=db,
                    action="conversation_delete",
                    resource_type="conversation",
                    user_id=user["id"],
                    resource_id=conversation_id,
                )
        except Exception:
            pass

    return {"message": "Conversation deleted successfully."}


# ---------------------------------------------------------------------------
# Administrator Dashboard & Routing Logs Endpoints
# ---------------------------------------------------------------------------

@app.get("/admin/users", tags=["Admin Dashboard"])
def admin_get_users(
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Retrieve all registered accounts for system administrator review."""
    require_admin_user(authorization)
    return get_admin_users(limit=limit)


@app.get("/admin/stats", tags=["Admin Dashboard"])
def admin_get_stats(
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Retrieve aggregate administrative system metrics."""
    require_admin_user(authorization)
    return get_admin_stats()


@app.get("/admin/conversations", tags=["Admin Dashboard"])
def admin_get_conversations(
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Retrieve all conversation sessions across all clinicians."""
    require_admin_user(authorization)
    return get_admin_conversations(limit=limit)


@app.get("/admin/reviews", tags=["Admin Dashboard"])
def admin_get_reviews(
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Retrieve all clinical reviews for quality assurance oversight."""
    require_admin_user(authorization)
    return get_admin_reviews(limit=limit)


@app.get("/routing/logs", tags=["Routing Logs"])
def get_routing_logs_endpoint(
    limit: int = Query(100, ge=1, le=500),
    conversation_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
) -> List[Dict[str, Any]]:
    """Retrieve structured routing logs for clinical safety monitoring."""
    require_auth_user(authorization)
    return get_routing_logs(limit=limit, conversation_id=conversation_id)


# Mount static assets and SPA fallback if frontend production build exists
frontend_dist = config.root_dir / "frontend" / "dist"
if not frontend_dist.exists():
    frontend_dist = config.root_dir.parent / "confiroute" / "frontend" / "dist"

if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        target = frontend_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist / "index.html")
