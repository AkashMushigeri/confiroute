"""Answer-Removal Evaluation Module for ConfiRoute.

Evaluates model hallucination and refusal behavior when the correct answer
is intentionally excised from the question choices (data/processed/test_removed.jsonl).

Measures:
1. Human Escalation Rate (under ConfiRoute routing)
2. Guess Rate (selecting one of the remaining incorrect clinical options A, B, or C)
3. Explicit Abstention Rate (selecting Option D: 'None of the above / Insufficient clinical information')
4. Incorrect Automatic-Answer Rate (UCER) with vs without routing
5. UCER reduction percentage achieved by ConfiRoute safety gating
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import argparse
import json
import numpy as np
import pandas as pd

from confiroute.config import get_config
from confiroute.eval.run_baselines import load_dataset_split
from confiroute.eval.metrics import compute_ucer, compute_escalation_rate
from confiroute.llm.base import ask_llm
from confiroute.confidence.combiner import format_mcq_prompt, extract_option_letter
from confiroute.routing.router import route_query


def format_removed_options(raw_options: Dict[str, str]) -> Dict[str, str]:
    """Ensure options dictionary contains explicit abstention choice as Option D."""
    opts = dict(raw_options)
    if "D" not in opts:
        opts["D"] = "None of the above / Insufficient clinical information"
    return opts


def evaluate_answer_removal_experiment(
    dataset: List[Dict[str, Any]],
    provider: str = "mock",
    simulated_level: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run comparative answer-removal experiment: Unrouted LLM (B0) vs ConfiRoute (B3)."""
    config = get_config()
    target_dir = output_dir or (config.root_dir / "reports" / "tables")
    target_dir.mkdir(parents=True, exist_ok=True)

    N = len(dataset)
    if N == 0:
        return {}

    # Records for tracking
    unrouted_preds: List[str] = []
    routed_decisions: List[str] = []
    routed_drafts: List[str] = []

    for item in dataset:
        options = format_removed_options(item["options"])
        prompt = format_mcq_prompt(item["question"], options)

        # 1. Unrouted LLM (Baseline B0)
        resp_b0 = ask_llm(
            model_key="tier1",
            prompt=prompt,
            provider=provider,
            simulated_level=simulated_level or "low",
        )
        pred_b0 = extract_option_letter(resp_b0.text, options)
        unrouted_preds.append(pred_b0)

        # 2. ConfiRoute (Baseline B3)
        # Note: In mock mode, missing correct answer produces low confidence or escalation
        decision = route_query(
            question=item["question"],
            options=options,
            model_key="tier1",
            provider=provider,
            simulated_level=simulated_level or "low",
        )
        routed_decisions.append(decision.route)
        routed_drafts.append(decision.ai_draft_answer)

    # 1. Unrouted Metrics (B0)
    # Correct action in test_removed is either abstaining (Option D) or escalating
    unrouted_abstained = sum(1 for p in unrouted_preds if p == "D")
    unrouted_guesses = sum(1 for p in unrouted_preds if p in {"A", "B", "C"})
    unrouted_auto = [True] * N
    # Since original answer was removed, any guess among A, B, C is clinically WRONG (is_correct=0)
    unrouted_is_correct = [1 if p == "D" else 0 for p in unrouted_preds]
    unrouted_ucer = compute_ucer(unrouted_is_correct, unrouted_auto)

    # 2. Routed Metrics (B3)
    routed_auto = [r == "direct" for r in routed_decisions]
    routed_human = [r == "human" for r in routed_decisions]
    routed_is_correct = [1 if (d == "D" and r == "direct") else 0 for d, r in zip(routed_drafts, routed_decisions)]
    routed_ucer = compute_ucer(routed_is_correct, routed_auto)
    routed_esc_rate = compute_escalation_rate(routed_human)

    # Routed guesses directly released
    routed_direct_guesses = sum(
        1 for d, r in zip(routed_drafts, routed_decisions) if r == "direct" and d in {"A", "B", "C"}
    )
    routed_direct_abstains = sum(
        1 for d, r in zip(routed_drafts, routed_decisions) if r == "direct" and d == "D"
    )

    ucer_reduction = 0.0
    if unrouted_ucer > 0:
        ucer_reduction = round(float((unrouted_ucer - routed_ucer) / unrouted_ucer * 100.0), 2)

    results = {
        "dataset_split": "TEST_REMOVED (200 Questions)",
        "total_queries": N,
        "unrouted_guesses_count": unrouted_guesses,
        "unrouted_guess_rate": round(float(unrouted_guesses / N), 4),
        "unrouted_abstention_count": unrouted_abstained,
        "unrouted_abstention_rate": round(float(unrouted_abstained / N), 4),
        "unrouted_ucer": unrouted_ucer,
        "routed_human_escalation_count": sum(routed_human),
        "routed_human_escalation_rate": routed_esc_rate,
        "routed_direct_guesses_count": routed_direct_guesses,
        "routed_direct_guess_rate": round(float(routed_direct_guesses / N), 4),
        "routed_direct_abstention_count": routed_direct_abstains,
        "routed_direct_abstention_rate": round(float(routed_direct_abstains / N), 4),
        "routed_ucer": routed_ucer,
        "ucer_reduction_percent": ucer_reduction,
    }

    # Save to CSV and JSON
    df = pd.DataFrame([results])
    csv_path = target_dir / "answer_removal_results.csv"
    json_path = target_dir / "answer_removal_results.json"
    df.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate answer-removal experiment (test_removed.jsonl).")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--provider", choices=["mock", "ollama", "groq"], default="mock")

    args = parser.parse_args()

    print(f"[ANSWER-REMOVAL] Loading test_removed split (limit={args.limit}, provider={args.provider})...")
    dataset = load_dataset_split("test_removed")
    if args.limit:
        dataset = dataset[:args.limit]

    print(f"[ANSWER-REMOVAL] Evaluating {len(dataset)} answer-removed questions...")
    results = evaluate_answer_removal_experiment(dataset, provider=args.provider)

    print("\n--- Answer-Removal Experimental Results ---")
    print(f"Total Evaluated Questions: {results['total_queries']}")
    print(f"Unrouted LLM Guess Rate (Hallucinations): {results['unrouted_guess_rate']:.1%}")
    print(f"Unrouted LLM UCER: {results['unrouted_ucer']:.1%}")
    print(f"ConfiRoute Human Escalation Rate: {results['routed_human_escalation_rate']:.1%}")
    print(f"ConfiRoute UCER: {results['routed_ucer']:.1%}")
    print(f"Safety UCER Reduction: {results['ucer_reduction_percent']}%\n")
    print("[SUCCESS] Results saved to reports/tables/answer_removal_results.csv")


if __name__ == "__main__":
    main()
