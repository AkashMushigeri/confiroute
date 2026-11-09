"""Confidence-Aware Routing Engine for ConfiRoute.

Directs medical queries based on calibrated confidence thresholds
and high-risk topic overrides.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from confiroute.config import get_config
from confiroute.confidence.combiner import get_confidence
from confiroute.routing.risk_rules import check_risk


@dataclass
class RouteDecision:
    """Structured decision output from the ConfiRoute routing engine."""

    route: str  # 'direct', 'tier2', 'human'
    status: str  # 'completed', 'pending_tier2', 'pending_human'
    color: str  # 'green', 'yellow', 'red'
    final_answer: Optional[str]  # Revealed only if route == 'direct'
    ai_draft_answer: str  # Always preserved internally
    scores: Dict[str, Optional[float]]
    is_high_risk: bool
    risk_reason: Optional[str]
    reason: str  # One-line explanation for UI meter
    tier_used: str
    tokens_used: Dict[str, int]
    cost_metadata: Dict[str, float]
    is_mock: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def route_query(
    question: str,
    options: Dict[str, str],
    model_key: str = "tier1",
    simulated_level: Optional[str] = None,
    high_threshold: Optional[float] = None,
    low_threshold: Optional[float] = None,
    check_risk_flag: bool = True,
) -> RouteDecision:
    """Route a medical question through confidence estimation and safety checks."""
    config = get_config()
    high_thresh = high_threshold if high_threshold is not None else config.threshold_high
    low_thresh = low_threshold if low_threshold is not None else config.threshold_low

    # 1. Run Confidence Estimation Pipeline
    conf_res = get_confidence(
        question=question,
        options=options,
        model_key=model_key,
        simulated_level=simulated_level,
    )

    ai_draft = conf_res["answer"]
    combined_score = conf_res["combined"]
    scores = {
        "s1": conf_res["s1"],
        "s2": conf_res["s2"],
        "s3": conf_res["s3"],
        "combined": combined_score,
    }

    # 2. Check High-Risk Safety Override
    combined_options_text = " ".join(options.values())
    is_high_risk, risk_reason = check_risk(
        text=question,
        options_text=combined_options_text,
        enabled=check_risk_flag,
    )

    # 3. Apply Decision Logic
    if is_high_risk:
        # Mandatory override: High risk questions ALWAYS escalate to human review
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,  # AI answer withheld pending clinician review
            ai_draft_answer=ai_draft,
            scores=scores,
            is_high_risk=True,
            risk_reason=risk_reason,
            reason=f"Held for clinical review: high-risk medical topic ({risk_reason})",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )

    # Missing or invalid score safety check
    if combined_score is None:
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,
            ai_draft_answer=ai_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason="Held for review: confidence estimation unavailable or invalid",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )

    # Threshold based routing
    if combined_score >= high_thresh:
        # High confidence -> Direct Answer
        return RouteDecision(
            route="direct",
            status="completed",
            color="green",
            final_answer=ai_draft,
            ai_draft_answer=ai_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason=f"High confidence ({combined_score:.2f} >= {high_thresh:.2f}): direct AI answer displayed",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )
    elif combined_score >= low_thresh:
        # Moderate confidence -> Tier 2 Strong Model Escalation
        return RouteDecision(
            route="tier2",
            status="pending_tier2",
            color="yellow",
            final_answer=None,  # Do not display fabricated Tier 2 response
            ai_draft_answer=ai_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason=f"Moderate confidence ({combined_score:.2f} in [{low_thresh:.2f}, {high_thresh:.2f})): escalated to Tier 2 strong model",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )
    else:
        # Low confidence -> Human Review Queue
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,  # AI answer withheld pending human review
            ai_draft_answer=ai_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason=f"Low confidence ({combined_score:.2f} < {low_thresh:.2f}): held for human review",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )
