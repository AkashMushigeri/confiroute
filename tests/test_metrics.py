"""Unit tests for evaluation metrics module with hand-calculated test cases."""

import pytest
import numpy as np

from confiroute.eval.metrics import (
    compute_auto_accuracy,
    compute_ucer,
    compute_ucer_high,
    compute_ece,
    compute_escalation_rate,
    compute_auroc,
    compute_all_metrics,
)


def test_compute_auto_accuracy_hand_calculated():
    """Verify auto_accuracy matches hand-calculated values."""
    # 3 auto-answered: 2 correct, 1 wrong -> 2/3 = 0.6667
    is_correct = [1, 0, 1, 1]
    is_auto = [True, True, True, False]
    acc = compute_auto_accuracy(is_correct, is_auto)
    assert acc == 0.6667

    # Edge case: no auto answers -> 0.0
    acc_zero = compute_auto_accuracy([1, 1, 1], [False, False, False])
    assert acc_zero == 0.0

    # 100% accuracy
    assert compute_auto_accuracy([1, 1], [True, True]) == 1.0


def test_compute_ucer_hand_calculated():
    """Verify UCER = (auto AND wrong) / total_queries."""
    # 4 queries: index 1 is auto AND wrong. Total queries = 4. UCER = 1/4 = 0.25
    is_correct = [1, 0, 1, 0]
    is_auto = [True, True, False, False]
    assert compute_ucer(is_correct, is_auto) == 0.25

    # Safe system: no wrong answers are auto-answered
    assert compute_ucer([1, 0, 1, 0], [True, False, True, False]) == 0.0

    # Worst system: all 4 queries auto-answered and all wrong
    assert compute_ucer([0, 0, 0, 0], [True, True, True, True]) == 1.0

    # Empty inputs
    assert compute_ucer([], []) == 0.0


def test_compute_ucer_high_hand_calculated():
    """Verify UCER_high strictly evaluates confidence >= threshold."""
    scores = [0.90, 0.85, 0.70, 0.95]
    is_correct = [1, 0, 0, 1]
    is_auto = [True, True, True, False]

    # Threshold 0.80:
    # Auto queries:
    # idx 0: s=0.90 (>=0.8), corr=1
    # idx 1: s=0.85 (>=0.8), corr=0 (wrong)
    # idx 2: s=0.70 (<0.8), corr=0 (excluded from high pool)
    # idx 3: s=0.95 (>=0.8), auto=False (excluded)
    # High-auto count = 2, wrong high-auto = 1 -> 1/2 = 0.50
    assert compute_ucer_high(is_correct, is_auto, scores, high_threshold=0.80) == 0.50

    # Threshold 0.99 (no auto queries meet threshold) -> 0.0
    assert compute_ucer_high(is_correct, is_auto, scores, high_threshold=0.99) == 0.0


def test_compute_ece_hand_calculated():
    """Verify ECE with hand-calculated bins."""
    # Test 1: Perfect calibration across two bins
    # Bin [0.6, 0.7): 5 samples, conf=0.6, 3 correct (acc=0.6) -> diff = 0.0
    # Bin [0.8, 0.9): 5 samples, conf=0.8, 4 correct (acc=0.8) -> diff = 0.0
    confs = [0.6] * 5 + [0.8] * 5
    corrs = [1, 1, 1, 0, 0] + [1, 1, 1, 1, 0]
    ece_perf = compute_ece(confs, corrs, n_bins=10)
    assert ece_perf == 0.0

    # Test 2: Known miscalibration
    # 10 samples all conf=0.85, 8 correct, 2 wrong -> acc=0.80.
    # diff = |0.80 - 0.85| = 0.05. Weight = 1.0. ECE = 0.05
    confs_mis = [0.85] * 10
    corrs_mis = [1] * 8 + [0] * 2
    assert compute_ece(confs_mis, corrs_mis, n_bins=10) == 0.05

    # Empty inputs
    assert compute_ece([], []) == 0.0


def test_compute_escalation_rate():
    """Verify escalation rate calculates fraction of escalated queries."""
    assert compute_escalation_rate([True, False, True, False]) == 0.50
    assert compute_escalation_rate([False, False]) == 0.0
    assert compute_escalation_rate([True, True, True]) == 1.0
    assert compute_escalation_rate([]) == 0.0


def test_compute_auroc():
    """Verify AUROC discriminates correct from wrong answers."""
    # Perfect ranking: correct items have higher scores than wrong
    scores = [0.95, 0.85, 0.35, 0.15]
    labels = [1, 1, 0, 0]
    assert compute_auroc(scores, labels) == 1.0

    # Inverted ranking
    assert compute_auroc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0.0

    # Single class returns None
    assert compute_auroc([0.8, 0.9], [1, 1]) is None
    assert compute_auroc([], []) is None


def test_compute_all_metrics_integration():
    """Verify comprehensive metrics calculation dictionary."""
    is_correct = [1, 0, 1, 1, 0]
    routes = ["direct", "direct", "tier2", "human", "direct"]
    scores = [0.92, 0.81, 0.65, 0.30, 0.88]
    latencies = [120.0, 150.0, 450.0, 50.0, 110.0]
    costs = [0.0001, 0.0001, 0.0005, 0.0, 0.0001]

    results = compute_all_metrics(
        is_correct=is_correct,
        routes=routes,
        confidence_scores=scores,
        latencies=latencies,
        costs=costs,
    )

    expected_keys = {
        "total_queries",
        "auto_count",
        "direct_count",
        "tier2_count",
        "human_count",
        "auto_accuracy",
        "ucer",
        "ucer_high",
        "ece",
        "escalation_rate",
        "auroc",
        "mean_latency_ms",
        "total_equivalent_cost_usd",
    }
    assert expected_keys.issubset(set(results.keys()))
    assert results["total_queries"] == 5
    assert results["direct_count"] == 3
    assert results["tier2_count"] == 1
    assert results["human_count"] == 1
    assert results["escalation_rate"] == 0.40  # (tier2 + human) / 5 = 2/5 = 0.40
    assert results["mean_latency_ms"] == pytest.approx(176.0, rel=1e-2)
