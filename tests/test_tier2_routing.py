"""Tests for Tier 2 escalation, acceptance, and fallback routing."""

import pytest
from unittest.mock import patch
from confiroute.routing.router import route_query
from confiroute.llm.providers import ProviderUnavailableError


def test_tier1_direct_routing_high_score():
    q = "What cell produces insulin?"
    opts = {"A": "Beta cells", "B": "Alpha cells", "C": "Delta cells", "D": "Acinar cells"}

    decision = route_query(q, opts, simulated_level="high", check_risk_flag=False)
    if decision.scores["combined"] >= 0.80:
        assert decision.route == "direct"
        assert decision.status == "completed"
        assert decision.color == "green"
        assert decision.final_answer == decision.ai_draft_answer
        assert decision.tier_used == "tier1"


def test_tier2_escalation_and_acceptance():
    q = "Complex diagnostic reasoning case?"
    opts = {"A": "Treatment A", "B": "Treatment B", "C": "Treatment C", "D": "Treatment D"}

    # Mock Tier 1 to return moderate score (e.g. 0.65) and Tier 2 to return high score (0.90)
    def mock_get_confidence(question, options, model_key="tier1", **kwargs):
        if model_key == "tier1":
            return {
                "answer": "B",
                "s1": 0.60,
                "s2": 0.67,
                "s3": 0.70,
                "combined": 0.65,  # Moderate score -> triggers Tier 2
                "tokens_used": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
                "cost_metadata": {"real_cost": 0.0, "equivalent_cost": 0.0001},
                "is_mock": True,
            }
        else:
            # Tier 2 re-evaluation
            return {
                "answer": "A",
                "s1": None,  # No logprobs for Tier 2
                "s2": 1.0,
                "s3": 0.85,
                "combined": 0.925,  # High score >= 0.80 -> Accepted!
                "tokens_used": {"prompt_tokens": 70, "completion_tokens": 15, "total_tokens": 85},
                "cost_metadata": {"real_cost": 0.0, "equivalent_cost": 0.0002},
                "is_mock": True,
            }

    with patch("confiroute.routing.router.get_confidence", side_effect=mock_get_confidence):
        decision = route_query(q, opts, check_risk_flag=False, execute_tier2=True)

    assert decision.route == "direct"
    assert decision.status == "completed"
    assert decision.color == "green"
    assert decision.final_answer == "A"
    assert decision.tier_used == "tier2"
    assert "Escalated to Tier 2" in decision.reason


def test_tier2_escalation_and_rejection_to_human():
    q = "Ambiguous case where both Tier 1 and Tier 2 are uncertain"
    opts = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}

    def mock_get_confidence(question, options, model_key="tier1", **kwargs):
        if model_key == "tier1":
            return {
                "answer": "B",
                "s1": 0.60,
                "s2": 0.67,
                "s3": 0.60,
                "combined": 0.62,  # Triggers Tier 2
                "tokens_used": {"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
                "cost_metadata": {"real_cost": 0.0, "equivalent_cost": 0.00008},
                "is_mock": True,
            }
        else:
            # Tier 2 re-evaluation also has moderate/low score (< 0.80)
            return {
                "answer": "B",
                "s1": None,
                "s2": 0.67,
                "s3": 0.70,
                "combined": 0.685,  # < 0.80 -> Rejected to human review
                "tokens_used": {"prompt_tokens": 60, "completion_tokens": 10, "total_tokens": 70},
                "cost_metadata": {"real_cost": 0.0, "equivalent_cost": 0.00015},
                "is_mock": True,
            }

    with patch("confiroute.routing.router.get_confidence", side_effect=mock_get_confidence):
        decision = route_query(q, opts, check_risk_flag=False, execute_tier2=True)

    assert decision.route == "human"
    assert decision.status == "pending_human"
    assert decision.color == "red"
    assert decision.final_answer is None  # Held from user!
    assert decision.ai_draft_answer == "B"
    assert decision.tier_used == "tier2"
    assert "is below acceptance" in decision.reason


def test_tier2_provider_unavailable_safe_fallback():
    q = "Case where Tier 2 API is down"
    opts = {"A": "A", "B": "B", "C": "C", "D": "D"}

    def mock_get_confidence(question, options, model_key="tier1", **kwargs):
        if model_key == "tier1":
            return {
                "answer": "C",
                "s1": 0.60,
                "s2": 0.67,
                "s3": 0.60,
                "combined": 0.62,
                "tokens_used": {"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
                "cost_metadata": {"real_cost": 0.0, "equivalent_cost": 0.00008},
                "is_mock": True,
            }
        else:
            raise ProviderUnavailableError("Groq free tier unavailable")

    with patch("confiroute.routing.router.get_confidence", side_effect=mock_get_confidence):
        decision = route_query(q, opts, check_risk_flag=False, execute_tier2=True)

    assert decision.route == "tier2"
    assert decision.status == "pending_tier2"
    assert decision.color == "yellow"
    assert decision.final_answer is None
    assert "held in pending queue" in decision.reason


def test_high_risk_overrides_high_tier1_score():
    q = "Immediate resuscitation protocol for pediatric cardiac arrest and epinephrine dosage"
    opts = {"A": "0.01 mg/kg IV", "B": "10 mg rapid IV", "C": "50 mg oral", "D": "None"}

    # Even with high score, high risk rule MUST escalate to human
    decision = route_query(q, opts, simulated_level="high", check_risk_flag=True)
    assert decision.route == "human"
    assert decision.status == "pending_human"
    assert decision.color == "red"
    assert decision.final_answer is None  # Answer withheld!
    assert decision.is_high_risk is True
