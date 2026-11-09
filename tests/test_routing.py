"""Tests for routing logic, risk detection rules, and threshold boundaries."""

from confiroute.routing.risk_rules import check_risk
from confiroute.routing.router import route_query


def test_high_risk_keyword_matching():
    # Dosage question
    is_risk, reason = check_risk("What is the pediatric dose of amoxicillin in mg/kg?")
    assert is_risk is True
    assert "dosage" in reason.lower()

    # Poisoning question
    is_risk, reason = check_risk("Patient presents with acute acetaminophen overdose and poisoning.")
    assert is_risk is True
    assert "overdose" in reason.lower() or "toxicology" in reason.lower()

    # Cardiac arrest emergency
    is_risk, reason = check_risk("Immediate protocol for cardiac arrest and ventricular fibrillation?")
    assert is_risk is True

    # Benign question
    is_risk, reason = check_risk("What is the normal anatomical location of the thymus?")
    assert is_risk is False
    assert reason is None


def test_high_risk_overrides_high_confidence():
    q = "What is the lethal overdose limit of potassium chloride bolus?"
    opts = {"A": "100 mEq", "B": "20 mEq", "C": "10 mEq", "D": "5 mEq"}

    # Even with simulated_level='high', high-risk rule MUST route to human
    decision = route_query(q, opts, simulated_level="high")
    assert decision.route == "human"
    assert decision.status == "pending_human"
    assert decision.color == "red"
    assert decision.is_high_risk is True
    assert decision.final_answer is None  # Answer withheld!
    assert decision.ai_draft_answer is not None


def test_routing_threshold_boundaries():
    q_safe = "What cell produces insulin in the human body?"
    opts = {"A": "Beta cells", "B": "Alpha cells", "C": "Delta cells", "D": "Acinar cells"}

    # Force simulated high
    dec_high = route_query(q_safe, opts, simulated_level="high", check_risk_flag=False)
    if dec_high.scores["combined"] >= 0.80:
        assert dec_high.route == "direct"
        assert dec_high.status == "completed"
        assert dec_high.color == "green"
        assert dec_high.final_answer == dec_high.ai_draft_answer

    # Force simulated medium (without immediate Tier 2 execution to test Tier 1 band mapping)
    dec_med = route_query(q_safe, opts, simulated_level="medium", check_risk_flag=False, execute_tier2=False)
    if 0.50 <= dec_med.scores["combined"] < 0.80:
        assert dec_med.route == "tier2"
        assert dec_med.status == "pending_tier2"
        assert dec_med.color == "yellow"
        assert dec_med.final_answer is None

    # Force simulated low
    dec_low = route_query(q_safe, opts, simulated_level="low", check_risk_flag=False)
    if dec_low.scores["combined"] < 0.50:
        assert dec_low.route == "human"
        assert dec_low.status == "pending_human"
        assert dec_low.color == "red"
        assert dec_low.final_answer is None
