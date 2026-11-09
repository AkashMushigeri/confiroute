"""Create the TEST_REMOVED split for ConfiRoute.

TEST_REMOVED takes 200 questions from the TEST split, deletes the correct option,
and re-letters the remaining three options to A, B, and C.
In this setting, any direct guess (A, B, or C) is wrong by construction;
the correct behavior of a safe confidence-aware system is to escalate to a human.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import random

from confiroute.config import get_config


def create_answer_removed_dataset(
    test_jsonl_path: Path,
    output_path: Path,
    sample_size: int = 200,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Derive TEST_REMOVED split by removing correct options from TEST questions."""
    if not test_jsonl_path.exists():
        raise FileNotFoundError(f"Source TEST split not found at: {test_jsonl_path}")

    records: List[Dict[str, Any]] = []
    with open(test_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if len(records) < sample_size:
        # If test split is smaller than requested sample size, use all
        selected_records = records
    else:
        rng = random.Random(seed)
        selected_records = rng.sample(records, sample_size)

    removed_records: List[Dict[str, Any]] = []
    new_letters = ["A", "B", "C"]

    for rec in selected_records:
        orig_options = rec["options"]
        correct_letter = rec["correct_letter"]
        removed_text = orig_options.get(correct_letter, "")

        # Collect options that were NOT the correct answer
        remaining_options_text = [
            text for letter, text in orig_options.items() if letter != correct_letter
        ]

        # Re-letter the remaining options as A, B, C
        relettered_options = {
            new_letter: remaining_options_text[i]
            for i, new_letter in enumerate(new_letters[: len(remaining_options_text)])
        }

        removed_entry = {
            "id": f"{rec['id']}_removed",
            "original_id": rec["id"],
            "question": rec["question"],
            "options": relettered_options,
            "removed_option_letter": correct_letter,
            "removed_option_text": removed_text,
            "correct_action": "escalate",
            "subject": rec.get("subject", "General Medicine"),
            "topic": rec.get("topic", "General"),
        }
        removed_records.append(removed_entry)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in removed_records:
            f.write(json.dumps(r) + "\n")

    print(
        f"[DATA] Created TEST_REMOVED split: {len(removed_records)} questions -> {output_path}"
    )
    return removed_records


def build_removed_split() -> Path:
    """Build TEST_REMOVED from the configured test split."""
    config = get_config()
    test_path = config.processed_data_dir / "test.jsonl"
    removed_path = config.processed_data_dir / "test_removed.jsonl"
    create_answer_removed_dataset(
        test_jsonl_path=test_path,
        output_path=removed_path,
        sample_size=config.split_sizes["test_removed"],
        seed=config.seed,
    )
    return removed_path


if __name__ == "__main__":
    build_removed_split()
