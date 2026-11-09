"""Resumable confidence data collection script for ConfiRoute.

Runs questions from MedMCQA splits through the confidence estimation pipeline,
logging individual signals (S1, S2, S3), combined scores, correctness labels,
token counts, latency, and costs to CSV.

Safety Notice:
Strictly distinguishes simulated/mock data from genuine real model inference.
"""

import sys
import os
import argparse
import json
import csv
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from confiroute.config import get_config
from confiroute.confidence.combiner import get_confidence
from confiroute.data.medmcqa_loader import load_medmcqa_split


CSV_COLUMNS = [
    "question_id",
    "subject",
    "topic",
    "correct_option",
    "predicted_option",
    "is_correct",
    "s1_token_prob",
    "s2_consistency",
    "s3_self_rated",
    "combined_score",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_ms",
    "model_name",
    "provider",
    "is_mock",
    "real_cost",
    "equivalent_cost",
    "timestamp",
]


def get_completed_ids(csv_path: Path) -> Set[str]:
    """Read previously completed question IDs from CSV to enable safe resuming."""
    if not csv_path.exists():
        return set()
    completed = set()
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("question_id")
            if qid:
                completed.add(qid)
    return completed


def estimate_run_resources(
    num_questions: int,
    provider: str,
    samples_s2: int = 3,
) -> Dict[str, Any]:
    """Estimate model calls, estimated time, and daily free quota usage."""
    # Each question makes:
    # 1 call for S1 (answer + logprobs)
    # samples_s2 calls for S2 (consistency)
    # 1 call for S3 (self-rating)
    calls_per_question = 1 + samples_s2 + 1
    total_calls = num_questions * calls_per_question

    if provider == "groq":
        # Groq free tier limit is ~1,000 requests/day, 30 RPM
        quota_pct = (total_calls / 1000.0) * 100.0
        est_sec = total_calls * 1.5  # ~1.5s per API call
        return {
            "total_calls": total_calls,
            "estimated_minutes": round(est_sec / 60.0, 1),
            "quota_description": f"Groq free tier: ~{total_calls}/1,000 daily requests ({quota_pct:.1f}% of daily limit)",
        }
    elif provider == "ollama":
        # Local CPU inference ~3-5s per call
        est_sec = total_calls * 4.0
        return {
            "total_calls": total_calls,
            "estimated_minutes": round(est_sec / 60.0, 1),
            "quota_description": "Local Ollama: Unlimited (Zero cost, CPU bound)",
        }
    else:
        # Mock mode
        return {
            "total_calls": total_calls,
            "estimated_minutes": 0.1,
            "quota_description": "Mock Mode: 0 API calls (Offline zero-cost simulation)",
        }


def collect_confidence_dataset(
    split_name: str = "val",
    provider: str = "mock",
    model_key: str = "tier1",
    limit: int = 20,
    output_csv: Optional[Path] = None,
    force_confirm: bool = False,
) -> Path:
    """Evaluate questions and append results to a persistent CSV."""
    config = get_config()
    split_file = config.processed_data_dir / f"{split_name}.jsonl"

    if not split_file.exists():
        raise FileNotFoundError(f"Split file not found: {split_file}")

    if output_csv is None:
        prefix = "mock" if provider == "mock" else "real"
        output_csv = config.root_dir / "reports" / "tables" / f"{prefix}_{split_name}_confidence.csv"

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Load questions
    questions: List[Dict[str, Any]] = []
    with open(split_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    # Resume capability: filter out already completed
    completed_ids = get_completed_ids(output_csv)
    pending_questions = [q for q in questions if str(q["id"]) not in completed_ids]

    if limit and limit > 0:
        pending_questions = pending_questions[:limit]

    # Quota & runtime check for large runs
    if len(pending_questions) > 20 and not force_confirm:
        estimates = estimate_run_resources(len(pending_questions), provider)
        print("\n" + "=" * 65)
        print("  CONFIROUTE BATCH EVALUATION SAFETY CHECK")
        print("=" * 65)
        print(f"Dataset split:         {split_name} ({len(pending_questions)} pending items)")
        print(f"Provider:              {provider.upper()}")
        print(f"Estimated total calls: {estimates['total_calls']}")
        print(f"Estimated runtime:     {estimates['estimated_minutes']} minutes")
        print(f"Quota usage:           {estimates['quota_description']}")
        print("=" * 65)
        print("To proceed with more than 20 items, rerun with the --confirm flag.\n")
        return output_csv

    # Initialize CSV header if newly created
    file_exists = output_csv.exists() and output_csv.stat().st_size > 0
    with open(output_csv, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()

        print(f"[COLLECT] Processing {len(pending_questions)} questions ({provider}) -> {output_csv.name}")

        for i, q in enumerate(pending_questions, 1):
            qid = str(q["id"])
            correct_letter = q.get("correct_letter", "")

            start_t = time.perf_counter()
            conf_res = get_confidence(
                question=q["question"],
                options=q["options"],
                model_key=model_key,
                provider=provider,
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            pred = conf_res["answer"]
            is_corr = 1 if (correct_letter and pred == correct_letter) else 0

            row = {
                "question_id": qid,
                "subject": q.get("subject", "General"),
                "topic": q.get("topic", "General"),
                "correct_option": correct_letter,
                "predicted_option": pred,
                "is_correct": is_corr,
                "s1_token_prob": conf_res["s1"] if conf_res["s1"] is not None else "",
                "s2_consistency": conf_res["s2"] if conf_res["s2"] is not None else "",
                "s3_self_rated": conf_res["s3"] if conf_res["s3"] is not None else "",
                "combined_score": conf_res["combined"],
                "prompt_tokens": conf_res["tokens_used"]["prompt_tokens"],
                "completion_tokens": conf_res["tokens_used"]["completion_tokens"],
                "total_tokens": conf_res["tokens_used"]["total_tokens"],
                "latency_ms": round(elapsed_ms, 2),
                "model_name": conf_res["model_info"]["model_name"],
                "provider": provider,
                "is_mock": conf_res["is_mock"],
                "real_cost": conf_res["cost_metadata"]["real_cost"],
                "equivalent_cost": conf_res["cost_metadata"]["equivalent_cost"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            writer.writerow(row)
            f.flush()  # Ensure data is flushed to disk immediately

            if i % 5 == 0 or i == len(pending_questions):
                print(f"  [{i}/{len(pending_questions)}] Evaluated {qid} | Score: {conf_res['combined']:.2f} | Correct: {is_corr}")

    print(f"[SUCCESS] Finished collection. Results saved to {output_csv}")
    return output_csv


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect confidence evaluation records.")
    parser.add_argument("--split", default="dev", choices=["dev", "val", "test", "test_removed"])
    parser.add_argument("--provider", default="mock", choices=["mock", "ollama", "groq"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--confirm", action="store_true", help="Confirm execution for batches > 20 questions")
    args = parser.parse_args()

    collect_confidence_dataset(
        split_name=args.split,
        provider=args.provider,
        limit=args.limit,
        force_confirm=args.confirm,
    )
