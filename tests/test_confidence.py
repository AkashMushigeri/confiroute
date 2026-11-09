"""Tests for the three confidence signals (S1, S2, S3) and signal combination."""

import pytest
import math
from confiroute.confidence.token_prob import compute_s1_token_prob
from confiroute.confidence.consistency import compute_s2_consistency
from confiroute.confidence.self_rating import parse_self_rating
from confiroute.confidence.combiner import combine_signals, get_confidence


def test_s1_token_prob_softmax_and_normalization():
    # Numerically stable softmax
    logprobs = {"A": -0.1, "B": -2.5, "C": -3.0, "D": -4.0}
    score_a, probs = compute_s1_token_prob("A", logprobs)
    assert score_a is not None
    assert 0.0 <= score_a <= 1.0
    assert score_a > 0.80  # Option A dominates

    # Sum of normalized probabilities should be ~1.0
    assert pytest.approx(sum(probs.values()), 0.001) == 1.0


def test_s1_missing_logprobs():
    score, probs = compute_s1_token_prob("A", None)
    assert score is None
    assert probs is None

    score_empty, _ = compute_s1_token_prob("A", {})
    assert score_empty is None


def test_s2_consistency():
    # 3 out of 3 agree
    score, maj, counts = compute_s2_consistency(["A", "A", "A"])
    assert score == 1.0
    assert maj == "A"
    assert counts["A"] == 3

    # 2 out of 3 agree
    score, maj, counts = compute_s2_consistency(["B", "A", "A"])
    assert pytest.approx(score, 0.01) == 0.67
    assert maj == "A"

    # Empty list
    score, maj, counts = compute_s2_consistency([])
    assert score == 0.0


def test_s3_parse_self_rating_varieties():
    assert parse_self_rating("Confidence: 85/100") == 0.85
    assert parse_self_rating("I am 90% certain.") == 0.90
    assert parse_self_rating("score: 75") == 0.75
    assert parse_self_rating("Confidence: 0.80") == 0.80
    assert parse_self_rating("95") == 0.95
    assert parse_self_rating("Completely invalid text without number") is None
    assert parse_self_rating(None) is None


def test_combine_signals_redistribution():
    # All three present (0.4, 0.3, 0.3)
    s1, s2, s3 = 0.90, 0.80, 0.70
    comb, weights = combine_signals(s1, s2, s3, weights={"w_s1": 0.4, "w_s2": 0.3, "w_s3": 0.3})
    expected = 0.4 * 0.90 + 0.3 * 0.80 + 0.3 * 0.70
    assert pytest.approx(comb, 0.001) == round(expected, 4)

    # Missing S1 (e.g. Tier 2 model without logprobs): weights redistributed between S2 and S3 (0.5 each)
    comb_no_s1, weights_no_s1 = combine_signals(None, 0.80, 0.70, weights={"w_s1": 0.4, "w_s2": 0.3, "w_s3": 0.3})
    assert weights_no_s1["s1"] == 0.0
    assert pytest.approx(weights_no_s1["s2"], 0.01) == 0.50
    assert pytest.approx(weights_no_s1["s3"], 0.01) == 0.50
    assert pytest.approx(comb_no_s1, 0.01) == 0.75

    # All None
    comb_none, _ = combine_signals(None, None, None)
    assert comb_none == 0.0


def test_get_confidence_pipeline():
    q = "What is the primary cause of scurvy?"
    opts = {"A": "Vitamin C deficiency", "B": "Iron deficiency", "C": "Vitamin A toxicity", "D": "Lead poisoning"}
    result = get_confidence(q, opts, model_key="tier1", use_cache=False)

    assert result["answer"] in {"A", "B", "C", "D"}
    assert result["combined"] is not None
    assert 0.0 <= result["combined"] <= 1.0
    assert result["is_mock"] is True
    assert "real_cost" in result["cost_metadata"]
