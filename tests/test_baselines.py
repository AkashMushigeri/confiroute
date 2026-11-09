"""Unit tests for formal baseline evaluations (B0, B1, B2-S1, B2-S2, B2-S3, B3)."""

import tempfile
from pathlib import Path
import pytest
import pandas as pd

from confiroute.eval.run_baselines import (
    evaluate_b0,
    evaluate_b1,
    evaluate_b2_single_signal,
    evaluate_b3_confiroute,
    run_all_baselines,
)
from confiroute.eval.metrics import compute_oracle_accuracy, compute_bootstrap_ci


@pytest.fixture
def sample_eval_dataset():
    """Create a minimal deterministic test dataset."""
    return [
        {
            "id": "t-001",
            "question": "Which vitamin deficiency is the specific cause of Wernicke encephalopathy?",
            "options": {"A": "Vitamin B1 (Thiamine)", "B": "Vitamin C", "C": "Vitamin D", "D": "Vitamin K"},
            "correct_option": "A",
            "subject": "Medicine",
        },
        {
            "id": "t-002",
            "question": "What is the definitive proximal tubule etiology of type 2 RTA?",
            "options": {"A": "Fanconi syndrome", "B": "Distal stone", "C": "Hypoaldosteronism", "D": "Salicylate"},
            "correct_option": "A",
            "subject": "Pathology",
        },
        {
            "id": "t-003",
            "question": "What is the recommended IV push bolus dosage of Adenosine for SVT?",
            "options": {"A": "6 mg rapid IV push", "B": "60 mg IV drip", "C": "100 mcg oral", "D": "1 mg sublingual"},
            "correct_option": "A",
            "subject": "Pharmacology",
        },
    ]


def test_evaluate_b0_small_llm_only(sample_eval_dataset):
    """Verify B0: Small LLM only with zero routing and 100% direct release."""
    res = evaluate_b0(sample_eval_dataset, provider="mock")
    assert "B0" in res["baseline"]
    assert res["human_escalation_rate"] == 0.0
    assert res["tier2_rate"] == 0.0
    assert res["total_queries"] == 3
    assert "auto_accuracy" in res
    assert "ucer" in res


def test_evaluate_b1_strong_llm_only(sample_eval_dataset):
    """Verify B1: Strong LLM only with zero routing and 100% Tier 2 usage."""
    res = evaluate_b1(sample_eval_dataset, provider="mock")
    assert "B1" in res["baseline"]
    assert res["human_escalation_rate"] == 0.0
    assert res["tier2_rate"] == 1.0
    assert res["total_queries"] == 3


def test_evaluate_b2_single_signal(sample_eval_dataset):
    """Verify B2: Routing strictly using single confidence signal."""
    for sig in ["s1", "s2", "s3"]:
        res = evaluate_b2_single_signal(sig, sample_eval_dataset, threshold=0.70, provider="mock")
        assert f"B2-{sig.upper()}" in res["baseline"]
        assert 0.0 <= res["human_escalation_rate"] <= 1.0
        assert 0.0 <= res["auto_accuracy"] <= 1.0


def test_evaluate_b3_confiroute(sample_eval_dataset):
    """Verify B3: Full ConfiRoute architecture."""
    res = evaluate_b3_confiroute(sample_eval_dataset, provider="mock")
    assert "B3" in res["baseline"]
    assert 0.0 <= res["auto_accuracy"] <= 1.0
    assert 0.0 <= res["human_escalation_rate"] <= 1.0
    assert "ci_95_accuracy" in res


def test_run_all_baselines_pipeline(sample_eval_dataset):
    """Verify full baseline comparative runner produces DataFrame and persists files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = run_all_baselines(sample_eval_dataset, provider="mock", output_dir=Path(tmpdir))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 6  # B0, B1, B2-S1, B2-S2, B2-S3, B3
        assert (Path(tmpdir) / "baseline_comparison.csv").exists()
        assert (Path(tmpdir) / "baseline_comparison.json").exists()


def test_compute_oracle_accuracy():
    """Verify Idealized Clinician Oracle accuracy calculation."""
    # 4 queries:
    # 0: direct, correct=1 -> correct
    # 1: direct, correct=0 -> wrong
    # 2: human, correct=0  -> oracle resolves to 1
    # 3: tier2, correct=1  -> correct
    # Total correct under oracle = 1 + 0 + 1 + 1 = 3 / 4 = 0.75
    is_correct = [1, 0, 0, 1]
    routes = ["direct", "direct", "human", "tier2"]
    acc = compute_oracle_accuracy(is_correct, routes)
    assert acc == 0.75
