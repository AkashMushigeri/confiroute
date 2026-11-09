"""Tests for MedMCQA data loading, validation, and split generation."""

import pytest
import tempfile
from pathlib import Path

from confiroute.data.medmcqa_loader import (
    index_to_letter,
    validate_record,
    format_standard_record,
    create_synthetic_fixture,
)
from confiroute.data.make_removed import create_answer_removed_dataset


def test_index_to_letter_conversions():
    # 0-indexed integer
    assert index_to_letter(0) == "A"
    assert index_to_letter(1) == "B"
    assert index_to_letter(2) == "C"
    assert index_to_letter(3) == "D"

    # String digits
    assert index_to_letter("0") == "A"
    assert index_to_letter("1") == "B"
    assert index_to_letter("2") == "C"
    assert index_to_letter("3") == "D"

    # Already letters
    assert index_to_letter("a") == "A"
    assert index_to_letter("B") == "B"

    # Invalid indices
    with pytest.raises(ValueError):
        index_to_letter(5)

    with pytest.raises(ValueError):
        index_to_letter(-1)

    with pytest.raises(ValueError):
        index_to_letter(None)


def test_validate_record():
    valid = {
        "id": "q1",
        "question": "What is the capital of France?",
        "opa": "Paris",
        "opb": "London",
        "opc": "Berlin",
        "opd": "Rome",
        "cop": 0,
        "choice_type": "single",
    }
    assert validate_record(valid) is True

    # Missing question
    invalid_q = valid.copy()
    invalid_q["question"] = ""
    assert validate_record(invalid_q) is False

    # Missing option
    invalid_opt = valid.copy()
    invalid_opt["opa"] = None
    assert validate_record(invalid_opt) is False

    # Multi choice type
    invalid_multi = valid.copy()
    invalid_multi["choice_type"] = "multi"
    assert validate_record(invalid_multi) is False


def test_format_standard_record():
    raw = {
        "id": "med-123",
        "question": "Diagnostic test for diabetes?",
        "opa": "HbA1c",
        "opb": "ECG",
        "opc": "Chest X-ray",
        "opd": "CBC",
        "cop": 0,
        "subject_name": "Biochemistry",
        "topic_name": "Carbohydrates",
    }
    formatted = format_standard_record(raw)
    assert formatted["id"] == "med-123"
    assert formatted["correct_letter"] == "A"
    assert formatted["options"]["A"] == "HbA1c"
    assert formatted["subject"] == "Biochemistry"


def test_create_synthetic_fixture():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "synth.jsonl"
        records = create_synthetic_fixture(tmp_path, count=10)
        assert len(records) == 10
        assert tmp_path.exists()
        assert records[0]["id"] == "syn-001"
        assert set(records[0]["options"].keys()) == {"A", "B", "C", "D"}


def test_create_answer_removed_dataset():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test.jsonl"
        removed_path = Path(tmpdir) / "test_removed.jsonl"

        create_synthetic_fixture(test_path, count=15)
        removed = create_answer_removed_dataset(
            test_jsonl_path=test_path,
            output_path=removed_path,
            sample_size=10,
            seed=42,
        )

        assert len(removed) == 10
        for item in removed:
            assert len(item["options"]) == 3  # A, B, C only
            assert item["correct_action"] == "escalate"
            assert "removed_option_letter" in item
            assert item["removed_option_letter"] in {"A", "B", "C", "D"}
