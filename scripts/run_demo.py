"""CLI Demo Pipeline runner for ConfiRoute.

Runs 20 questions from the DEV dataset through confidence estimation,
risk screening, and routing, persisting all steps to SQLite.
"""

import sys
import json
from pathlib import Path

# Ensure package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from confiroute.config import get_config
from confiroute.data.make_splits import build_splits
from confiroute.routing.router import route_query
from confiroute.db.database import save_pipeline_execution, init_db


def run_pipeline_demo(num_questions: int = 20):
    config = get_config()
    init_db()

    dev_file = config.processed_data_dir / "dev.jsonl"
    if not dev_file.exists():
        print(f"[DEMO] DEV split not found at {dev_file}. Building splits now...")
        build_splits()

    if not dev_file.exists():
        raise FileNotFoundError(f"Could not locate or generate DEV split at {dev_file}")

    # Read questions
    questions = []
    with open(dev_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
            if len(questions) >= num_questions:
                break

    print("\n" + "=" * 70)
    print(f"  CONFIROUTE PIPELINE DEMO — {len(questions)} QUESTIONS (MOCK LLM TIER 1)")
    print("=" * 70)
    print(f"Thresholds: High >= {config.threshold_high:.2f} (Direct), Low < {config.threshold_low:.2f} (Human)")
    print("Zero-Cost Architecture: Real cost is $0.00; tracking equivalent cost.")
    print("-" * 70)

    routes_count = {"direct": 0, "tier2": 0, "human": 0}
    high_risk_count = 0
    correct_count = 0
    total_eq_cost = 0.0

    header_fmt = "{:<4} | {:<25} | {:<7} | {:<6} | {:<8} | {:<10}"
    row_fmt = "{:<4} | {:<25} | {:<7} | {:<6.2f} | {:<8} | {:<10}"

    print(header_fmt.format("#", "Topic/Subject", "Answer", "Score", "Route", "Risk Flag"))
    print("-" * 70)

    for i, q in enumerate(questions, 1):
        decision = route_query(
            question=q["question"],
            options=q["options"],
            model_key="tier1",
        )

        # Save to SQLite
        save_pipeline_execution(
            question=q["question"],
            options=q["options"],
            decision=decision,
            query_id=q["id"],
            correct_letter=q.get("correct_letter"),
            subject=q.get("subject"),
            topic=q.get("topic"),
        )

        routes_count[decision.route] += 1
        if decision.is_high_risk:
            high_risk_count += 1

        is_correct = (decision.ai_draft_answer == q.get("correct_letter"))
        if is_correct:
            correct_count += 1

        total_eq_cost += decision.cost_metadata.get("equivalent_cost", 0.0)

        topic_disp = (q.get("topic") or q.get("subject") or "Medicine")[:23]
        risk_str = "YES" if decision.is_high_risk else "No"
        print(row_fmt.format(
            i,
            topic_disp,
            decision.ai_draft_answer or "-",
            decision.scores["combined"] or 0.0,
            decision.route.upper(),
            risk_str,
        ))

    print("-" * 70)
    print("PIPELINE SUMMARY:")
    print(f"  Total Processed:         {len(questions)}")
    print(f"  Direct Answers (Green):  {routes_count['direct']} ({routes_count['direct']/len(questions)*100:.1f}%)")
    print(f"  Tier 2 Escalated (Yellow): {routes_count['tier2']} ({routes_count['tier2']/len(questions)*100:.1f}%)")
    print(f"  Human Review (Red):      {routes_count['human']} ({routes_count['human']/len(questions)*100:.1f}%)")
    print(f"  High-Risk Overrides:     {high_risk_count}")
    print(f"  Mock Model Raw Accuracy: {correct_count}/{len(questions)} ({correct_count/len(questions)*100:.1f}%)")
    print(f"  Actual Money Spent:      $0.00 (Zero-cost setup)")
    print(f"  Equivalent API Cost:     ${total_eq_cost:.6f} USD")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_pipeline_demo(count)
