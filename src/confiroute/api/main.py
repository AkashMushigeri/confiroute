"""FastAPI REST Service for ConfiRoute.

Provides endpoints for query routing, human clinician review queue,
case status resolution, and system analytics.

NOTICE: For this milestone, reviewer endpoints are designed for local evaluation.
Production deployment requires token-based clinician authentication and RBAC.
"""

from typing import Any, Dict, List, Literal, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from confiroute.config import get_config
from confiroute.routing.router import route_query, RouteDecision
from confiroute.db.database import (
    init_db,
    save_pipeline_execution,
    get_pending_reviews,
    record_review_decision,
    get_query_result,
    get_system_stats,
)

# Initialize database schema
init_db()

config = get_config()

app = FastAPI(
    title="ConfiRoute API",
    description="Confidence-Aware LLM Routing and Safety Service for Medical Inquiries",
    version="0.2.0",
)

# CORS middleware for local frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Medical query or exam question")
    options: Dict[str, str] = Field(..., description="Four candidate multiple choice options (A, B, C, D)")
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


class ReviewRequest(BaseModel):
    reviewer_name: str = Field(..., min_length=2, description="Name or identifier of reviewing clinician")
    decision: Literal["approved", "edited", "rejected"] = Field(..., description="Review action")
    corrected_answer: Optional[str] = Field(None, description="Corrected option letter (A, B, C, D) if edited")
    notes: Optional[str] = Field(None, description="Clinical justification or audit notes")


class ReviewResponse(BaseModel):
    query_id: str
    decision: str
    updated_status: str
    final_answer: Optional[str]
    reviewer_name: str
    message: str


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
    """Submit a medical multiple-choice question for confidence-aware routing."""
    # Validate options have candidate keys
    if not req.options or len(req.options) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least 2 answer options are required.",
        )

    decision = route_query(
        question=req.question,
        options=req.options,
        model_key=req.model_key,
        simulated_level=req.simulated_level,
        provider=req.provider,
    )

    query_id = save_pipeline_execution(
        question=req.question,
        options=req.options,
        decision=decision,
        subject=req.subject,
        topic=req.topic,
    )

    return AskResponse(
        query_id=query_id,
        route=decision.route,
        status=decision.status,
        color=decision.color,
        final_answer=decision.final_answer,
        ai_draft_answer=decision.ai_draft_answer,
        scores=decision.scores,
        is_high_risk=decision.is_high_risk,
        risk_reason=decision.risk_reason,
        reason=decision.reason,
        tier_used=decision.tier_used,
        cost_metadata=decision.cost_metadata,
        tokens_used=decision.tokens_used,
        is_mock=decision.is_mock,
    )


@app.get("/queue", tags=["Reviewer Queue"])
def get_review_queue(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch pending medical cases awaiting human clinician review."""
    return get_pending_reviews(limit=limit)


@app.post("/review/{query_id}", response_model=ReviewResponse, tags=["Reviewer Queue"])
def submit_review(query_id: str, review: ReviewRequest) -> ReviewResponse:
    """Review and resolve an escalated case (approve, edit, or reject)."""
    # Verify query exists
    existing = get_query_result(query_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found.",
        )

    if review.decision == "edited" and not review.corrected_answer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A corrected answer letter is required when choosing 'edited'.",
        )

    result = record_review_decision(
        query_id=query_id,
        reviewer_name=review.reviewer_name,
        decision=review.decision,
        corrected_answer=review.corrected_answer,
        notes=review.notes,
    )

    action_msg = {
        "approved": f"Case approved. AI draft answer (Option {result['final_answer']}) released to user.",
        "edited": f"Case updated with clinician correction: Option {result['final_answer']} released to user.",
        "rejected": "Case rejected by clinician. No answer released to user.",
    }.get(review.decision, "Decision recorded.")

    return ReviewResponse(
        query_id=query_id,
        decision=result["decision"],
        updated_status=result["updated_status"],
        final_answer=result["final_answer"],
        reviewer_name=result["reviewer_name"],
        message=action_msg,
    )


@app.get("/result/{query_id}", tags=["Routing"])
def get_result(query_id: str) -> Dict[str, Any]:
    """Retrieve the routing status and released final answer for a query."""
    result = get_query_result(query_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query ID '{query_id}' not found.",
        )
    return result


@app.get("/stats", tags=["Analytics"])
def get_stats() -> Dict[str, Any]:
    """Return real-time database query, routing, and review statistics."""
    return get_system_stats()
