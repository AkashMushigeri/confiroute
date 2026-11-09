"""Unit tests for threshold tuning, grid search, and Pareto trade-off optimization."""

import json
import tempfile
from pathlib import Path
import pytest
import pandas as pd

from confiroute.routing.thresholds import (
    simulate_routing_for_thresholds,
    grid_search_thresholds,
    save_thresholds,
)


def test_simulate_routing_threshold_logic():
    """Verify routing decisions properly adhere to thresholds and risk override."""
    # 4 queries:
    # 0: score=0.90, risk=False -> >= 0.80 -> direct
    # 1: score=0.65, risk=False -> in [0.50, 0.80) -> tier2
    # 2: score=0.30, risk=False -> < 0.50 -> human
    # 3: score=0.95, risk=True  -> risk override -> human
    scores = [0.90, 0.65, 0.30, 0.95]
    is_correct = [1, 1, 0, 1]
    is_risk = [False, False, False, True]

    metrics = simulate_routing_for_thresholds(
        confidence_scores=scores,
        is_correct=is_correct,
        is_high_risk=is_risk,
        low_threshold=0.50,
        high_threshold=0.80,
    )

    assert metrics["auto_count"] == 1  # Only query 0 is direct
    assert metrics["auto_accuracy"] == 1.0  # Query 0 is correct
    assert metrics["ucer"] == 0.0  # No wrong answers auto-answered
    assert metrics["escalation_rate"] == 0.75  # 3 out of 4 (tier2 + 2 humans)


def test_grid_search_min_ucer():
    """Verify grid search identifies candidate minimizing UCER under escalation limit."""
    scores = [0.95, 0.85, 0.70, 0.40, 0.20, 0.88]
    is_correct = [1, 0, 1, 0, 0, 1]
    is_risk = [False, False, False, False, False, False]

    optimal, df = grid_search_thresholds(
        confidence_scores=scores,
        is_correct=is_correct,
        is_high_risk=is_risk,
        low_range=(0.40, 0.60, 0.10),
        high_range=(0.70, 0.90, 0.10),
        objective="min_ucer",
        max_escalation=0.70,
    )

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "ucer" in optimal
    assert "low_threshold" in optimal
    assert "high_threshold" in optimal
    assert optimal["high_threshold"] > optimal["low_threshold"]
    assert optimal["escalation_rate"] <= 0.70


def test_grid_search_max_utility():
    """Verify grid search optimizes composite utility function."""
    scores = [0.95, 0.90, 0.85, 0.60, 0.30]
    is_correct = [1, 1, 0, 1, 0]
    is_risk = [False, False, False, False, False]

    optimal, df = grid_search_thresholds(
        confidence_scores=scores,
        is_correct=is_correct,
        is_high_risk=is_risk,
        low_range=(0.40, 0.60, 0.10),
        high_range=(0.70, 0.90, 0.10),
        objective="max_utility",
        tradeoff_lambda=0.5,
    )

    assert "utility" in optimal
    assert optimal["high_threshold"] > optimal["low_threshold"]
    assert len(df) > 0


def test_save_thresholds():
    """Verify optimal thresholds are saved to JSON with required metadata."""
    optimal = {
        "low_threshold": 0.45,
        "high_threshold": 0.80,
        "auto_accuracy": 0.92,
        "ucer": 0.02,
        "escalation_rate": 0.25,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "thresholds.json"
        saved = save_thresholds(optimal, json_path, metadata={"split": "val", "samples": 100})
        assert saved.exists()

        with open(saved, "r") as f:
            data = json.load(f)

        assert data["low_threshold"] == 0.45
        assert data["high_threshold"] == 0.80
        assert data["metadata"]["split"] == "val"
