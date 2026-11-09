"""Unit tests for evaluation figures and plotting modules."""

import tempfile
from pathlib import Path
import pytest
import pandas as pd

from confiroute.eval.plots import (
    plot_reliability_diagram,
    plot_pareto_tradeoff,
    plot_baseline_comparison,
    plot_cost_vs_accuracy,
    plot_answer_removal_analysis,
    generate_all_evaluation_figures,
)


def test_plot_reliability_diagram():
    """Verify reliability diagram generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test_reliability.png"
        res = plot_reliability_diagram([0.8, 0.4, 0.9], [0.75, 0.45, 0.85], [1, 0, 1], out)
        assert res.exists()
        assert res.stat().st_size > 1000


def test_plot_pareto_tradeoff():
    """Verify Pareto trade-off curve generation."""
    df = pd.DataFrame({
        "escalation_rate": [0.1, 0.2, 0.3],
        "auto_accuracy": [0.7, 0.8, 0.9],
        "ucer": [0.1, 0.05, 0.02],
    })
    chosen = {"escalation_rate": 0.2, "auto_accuracy": 0.8, "low_threshold": 0.5, "high_threshold": 0.8}

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test_pareto.png"
        res = plot_pareto_tradeoff(df, chosen, out)
        assert res.exists()
        assert res.stat().st_size > 1000


def test_plot_baseline_comparison():
    """Verify baseline comparison bar chart generation."""
    df = pd.DataFrame([
        {"baseline": "B0: Small LLM", "auto_accuracy": 0.55, "ucer": 0.45, "human_escalation_rate": 0.0},
        {"baseline": "B3: ConfiRoute", "auto_accuracy": 0.88, "ucer": 0.04, "human_escalation_rate": 0.25},
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test_baseline.png"
        res = plot_baseline_comparison(df, out)
        assert res.exists()
        assert res.stat().st_size > 1000


def test_plot_cost_vs_accuracy():
    """Verify cost vs accuracy plot generation."""
    df = pd.DataFrame([
        {"baseline": "B0: Small LLM", "oracle_accuracy": 0.55, "equivalent_cost_per_query": 0.000015},
        {"baseline": "B3: ConfiRoute", "oracle_accuracy": 0.93, "equivalent_cost_per_query": 0.000045},
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test_cost.png"
        res = plot_cost_vs_accuracy(df, out)
        assert res.exists()
        assert res.stat().st_size > 1000


def test_generate_all_evaluation_figures():
    """Verify batch generator creates all 5 figures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        figs = generate_all_evaluation_figures(Path(tmpdir))
        assert len(figs) == 5
        for name, path in figs.items():
            assert path.exists()
            assert path.stat().st_size > 1000
