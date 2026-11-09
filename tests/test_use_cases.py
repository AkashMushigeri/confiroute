"""Unit tests for clinical use-case demonstrations (UC1 to UC6)."""

import tempfile
from pathlib import Path
import pytest

from confiroute.eval.use_cases import (
    run_uc1_high_confidence,
    run_uc2_ambiguous_question,
    run_uc3_missing_information,
    run_uc4_cost_aware_routing,
    run_uc5_high_risk_and_abnormal_inputs,
    run_uc6_side_by_side,
    run_all_use_cases,
)


def test_uc1_high_confidence():
    """Verify UC1 factual query produces direct release."""
    res = run_uc1_high_confidence(provider="mock")
    assert res["verified"] is True
    assert res["confidence_score"] >= 0.70


def test_uc2_ambiguous_question():
    """Verify UC2 ambiguous query holds answer for escalation."""
    res = run_uc2_ambiguous_question(provider="mock")
    assert res["verified"] is True
    assert res["final_answer_withheld"] is True


def test_uc3_missing_information():
    """Verify UC3 excised answer query abstains or escalates."""
    res = run_uc3_missing_information(provider="mock")
    assert res["verified"] is True


def test_uc4_cost_aware_routing():
    """Verify UC4 cost-aware routing reduces costs compared to Always-Tier-2."""
    res = run_uc4_cost_aware_routing(provider="mock")
    assert res["verified"] is True
    assert res["confiroute_total_equivalent_cost"] <= res["always_tier2_total_equivalent_cost"]


def test_uc5_high_risk_and_abnormal_inputs():
    """Verify UC5 handles dosage, emergency, empty, ultra-long, and out-of-domain inputs."""
    scenarios = run_uc5_high_risk_and_abnormal_inputs(provider="mock")
    assert len(scenarios) == 5
    for sc in scenarios:
        assert sc["verified"] is True, f"Failed sub-scenario: {sc['scenario']}"


def test_uc6_side_by_side():
    """Verify UC6 side-by-side demonstrates unrouted blind release vs ConfiRoute review."""
    res = run_uc6_side_by_side(provider="mock")
    assert res["verified"] is True
    assert res["confiroute_b3"]["route"] == "human"


def test_run_all_use_cases_artifacts():
    """Verify run_all_use_cases generates both JSON and Markdown artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results = run_all_use_cases(provider="mock", output_dir=Path(tmpdir))
        assert "UC1" in results
        assert "UC6" in results
        assert (Path(tmpdir) / "use_case_results.json").exists()
        assert (Path(tmpdir) / "USE_CASE_DEMONSTRATIONS.md").exists()
