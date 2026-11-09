"""Unit tests for the answer-removal hallucination evaluation module."""

import tempfile
from pathlib import Path
import pytest

from confiroute.eval.answer_removal import (
    format_removed_options,
    evaluate_answer_removal_experiment,
)


def test_format_removed_options():
    """Verify Option D is added as explicit abstention option."""
    opts_3 = {"A": "Aspirin", "B": "Paracetamol", "C": "Ibuprofen"}
    formatted = format_removed_options(opts_3)

    assert set(formatted.keys()) == {"A", "B", "C", "D"}
    assert "None of the above" in formatted["D"]

    # If D already exists, it is preserved
    opts_4 = {"A": "A", "B": "B", "C": "C", "D": "Existing D"}
    assert format_removed_options(opts_4)["D"] == "Existing D"


def test_evaluate_answer_removal_experiment():
    """Verify answer-removal experiment compares Unrouted vs ConfiRoute."""
    dataset = [
        {
            "id": f"rem-{i}",
            "question": f"Question {i} with correct answer removed",
            "options": {"A": "Wrong A", "B": "Wrong B", "C": "Wrong C"},
            "correct_action": "escalate",
        }
        for i in range(4)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        res = evaluate_answer_removal_experiment(dataset, provider="mock", output_dir=Path(tmpdir))

        assert res["total_queries"] == 4
        assert "unrouted_guess_rate" in res
        assert "unrouted_ucer" in res
        assert "routed_human_escalation_rate" in res
        assert "routed_ucer" in res
        assert "ucer_reduction_percent" in res

        assert (Path(tmpdir) / "answer_removal_results.csv").exists()
        assert (Path(tmpdir) / "answer_removal_results.json").exists()
