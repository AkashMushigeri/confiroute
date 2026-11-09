"""Confidence-Aware Routing Engine for ConfiRoute.

Directs medical queries based on multi-signal confidence thresholds,
high-risk safety overrides, and Tier 2 escalation logic.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from confiroute.config import get_config
from confiroute.confidence.combiner import get_confidence
from confiroute.routing.risk_rules import check_risk
from confiroute.llm.providers import ProviderError, MissingAPIKeyError, ProviderUnavailableError, RateLimitExceededError


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
    tier2_attempted: bool = False

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
    provider: Optional[str] = None,
    execute_tier2: bool = True,
) -> RouteDecision:
    """Route a medical question through confidence estimation, risk screening, and Tier 2 escalation."""
    config = get_config()
    high_thresh = high_threshold if high_threshold is not None else config.threshold_high
    low_thresh = low_threshold if low_threshold is not None else config.threshold_low
    tier2_accept = config.tier2_accept

    # 0. Input validation check (Empty or abnormal query)
    if not question or not question.strip():
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,
            ai_draft_answer="",
            scores={"s1": 0.0, "s2": 0.0, "s3": 0.0, "combined": 0.0},
            is_high_risk=False,
            risk_reason=None,
            reason="Held for review: empty or invalid clinical query input",
            tier_used=model_key,
            tokens_used={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            cost_metadata={"real_cost": 0.0, "equivalent_cost": 0.0, "currency": "USD"},
            is_mock=True,
            tier2_attempted=False,
        )

    # 1. Run Tier 1 Confidence Estimation Pipeline
    conf_res = get_confidence(
        question=question,
        options=options,
        model_key=model_key,
        simulated_level=simulated_level,
        provider=provider,
    )

    t1_draft = conf_res["answer"]
    t1_combined = conf_res["combined"]
    scores = {
        "s1": conf_res["s1"],
        "s2": conf_res["s2"],
        "s3": conf_res["s3"],
        "combined": t1_combined,
    }

    # 2. Check High-Risk Safety Override
    combined_options_text = " ".join(options.values())
    is_high_risk, risk_reason = check_risk(
        text=question,
        options_text=combined_options_text,
        enabled=check_risk_flag,
    )

    # 3. High-Risk Safety Override (Overrides all confidence scores)
    if is_high_risk:
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,  # AI answer withheld pending clinician review
            ai_draft_answer=t1_draft,
            scores=scores,
            is_high_risk=True,
            risk_reason=risk_reason,
            reason=f"Held for clinical review: high-risk medical topic ({risk_reason})",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )

    # 4. Missing or invalid score safety check
    if t1_combined is None:
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,
            ai_draft_answer=t1_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason="Held for review: confidence estimation unavailable or invalid",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )

    # 5. Threshold-based Routing Logic
    if t1_combined >= high_thresh:
        # High confidence -> Direct Answer
        return RouteDecision(
            route="direct",
            status="completed",
            color="green",
            final_answer=t1_draft,
            ai_draft_answer=t1_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason=f"High confidence ({t1_combined:.2f} >= {high_thresh:.2f}): direct AI answer displayed",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )

    elif t1_combined >= low_thresh:
        # Moderate confidence -> Tier 2 Strong Model Escalation
        if not execute_tier2:
            return RouteDecision(
                route="tier2",
                status="pending_tier2",
                color="yellow",
                final_answer=None,
                ai_draft_answer=t1_draft,
                scores=scores,
                is_high_risk=False,
                risk_reason=None,
                reason=f"Moderate confidence ({t1_combined:.2f} in [{low_thresh:.2f}, {high_thresh:.2f})): escalated to Tier 2 strong model",
                tier_used=model_key,
                tokens_used=conf_res["tokens_used"],
                cost_metadata=conf_res["cost_metadata"],
                is_mock=conf_res["is_mock"],
                tier2_attempted=False,
            )

        # Attempt Tier 2 re-evaluation
        tier2_provider = "groq" if provider == "real" else (provider or config.models.get("tier2", {}).get("provider", "mock"))

        try:
            t2_conf = get_confidence(
                question=question,
                options=options,
                model_key="tier2",
                simulated_level=simulated_level,
                provider=tier2_provider,
            )

            t2_draft = t2_conf["answer"]
            t2_combined = t2_conf["combined"]

            # Merge token counts and costs
            combined_tokens = {
                "prompt_tokens": conf_res["tokens_used"]["prompt_tokens"] + t2_conf["tokens_used"]["prompt_tokens"],
                "completion_tokens": conf_res["tokens_used"]["completion_tokens"] + t2_conf["tokens_used"]["completion_tokens"],
                "total_tokens": conf_res["tokens_used"]["total_tokens"] + t2_conf["tokens_used"]["total_tokens"],
            }
            combined_costs = {
                "real_cost": conf_res["cost_metadata"]["real_cost"] + t2_conf["cost_metadata"]["real_cost"],
                "equivalent_cost": round(conf_res["cost_metadata"]["equivalent_cost"] + t2_conf["cost_metadata"]["equivalent_cost"], 6),
                "currency": "USD",
            }
            combined_scores = {
                "tier1_combined": t1_combined,
                "tier2_s1": t2_conf["s1"],
                "tier2_s2": t2_conf["s2"],
                "tier2_s3": t2_conf["s3"],
                "combined": t2_combined,
            }

            # Evaluate Tier 2 acceptance
            if t2_combined is not None and t2_combined >= tier2_accept:
                # Tier 2 Accepted -> Direct Answer
                return RouteDecision(
                    route="direct",
                    status="completed",
                    color="green",
                    final_answer=t2_draft,
                    ai_draft_answer=t2_draft,
                    scores=combined_scores,
                    is_high_risk=False,
                    risk_reason=None,
                    reason=f"Escalated to Tier 2: strong model answered Option {t2_draft} with high confidence ({t2_combined:.2f} >= {tier2_accept:.2f})",
                    tier_used="tier2",
                    tokens_used=combined_tokens,
                    cost_metadata=combined_costs,
                    is_mock=t2_conf["is_mock"],
                    tier2_attempted=True,
                )
            else:
                # Tier 2 Score below acceptance -> Escalate to Human Review
                score_disp = f"{t2_combined:.2f}" if t2_combined is not None else "N/A"
                return RouteDecision(
                    route="human",
                    status="pending_human",
                    color="red",
                    final_answer=None,  # Withheld
                    ai_draft_answer=t2_draft,
                    scores=combined_scores,
                    is_high_risk=False,
                    risk_reason=None,
                    reason=f"Escalated to Tier 2, but confidence ({score_disp} < {tier2_accept:.2f}) is below acceptance: held for clinical review",
                    tier_used="tier2",
                    tokens_used=combined_tokens,
                    cost_metadata=combined_costs,
                    is_mock=t2_conf["is_mock"],
                    tier2_attempted=True,
                )

        except (MissingAPIKeyError, ProviderUnavailableError, RateLimitExceededError, ProviderError) as err:
            # Safe Fallback: do NOT release unverified draft; hold for pending review
            return RouteDecision(
                route="tier2",
                status="pending_tier2",
                color="yellow",
                final_answer=None,
                ai_draft_answer=t1_draft,
                scores=scores,
                is_high_risk=False,
                risk_reason=None,
                reason=f"Tier 2 escalation deferred ({err}): question held in pending queue",
                tier_used=model_key,
                tokens_used=conf_res["tokens_used"],
                cost_metadata=conf_res["cost_metadata"],
                is_mock=conf_res["is_mock"],
                tier2_attempted=True,
            )

    else:
        # Low confidence -> Human Review Queue
        return RouteDecision(
            route="human",
            status="pending_human",
            color="red",
            final_answer=None,  # AI answer withheld pending human review
            ai_draft_answer=t1_draft,
            scores=scores,
            is_high_risk=False,
            risk_reason=None,
            reason=f"Low confidence ({t1_combined:.2f} < {low_thresh:.2f}): held for human review",
            tier_used=model_key,
            tokens_used=conf_res["tokens_used"],
            cost_metadata=conf_res["cost_metadata"],
            is_mock=conf_res["is_mock"],
        )
