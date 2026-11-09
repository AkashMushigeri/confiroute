"""Unit tests for signal and calibration ablation studies."""

import tempfile
from pathlib import Path
import pytest
import pandas as pd

from confiroute.eval.ablation import compute_brier_score, run_ablation_study


def test_compute_brier_score():
    """Verify Brier score calculation (MSE between probs and labels)."""
    # Perfect predictions: probs == labels -> MSE = 0.0
    assert compute_brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0

    # Completely wrong: probs = 1.0 when labels = 0 -> MSE = 1.0
    assert compute_brier_score([1.0, 1.0], [0, 0]) == 1.0

    # Intermediate: probs=[0.8, 0.2], labels=[1, 0] -> diffs are 0.2, 0.2 -> MSE = 0.04
    assert compute_brier_score([0.8, 0.2], [1, 0]) == 0.04


def test_run_ablation_study():
    """Verify ablation runner evaluates all signal combinations."""
    records = [
        {"id": f"q-{i}", "s1": 0.85, "s2": 1.0, "s3": 0.90, "combined": 0.91, "is_correct": 1}
        for i in range(10)
    ] + [
        {"id": f"q-{i+10}", "s1": 0.35, "s2": 0.33, "s3": 0.40, "combined": 0.36, "is_correct": 0}
        for i in range(10)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        df = run_ablation_study(records, eval_threshold=0.70, output_dir=Path(tmpdir))
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 7
        assert "ece_10_bin" in df.columns
        assert "brier_score" in df.columns
        assert "auroc" in df.columns
        assert (Path(tmpdir) / "ablation_results.csv").exists()
