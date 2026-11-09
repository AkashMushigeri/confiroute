"""Signal and Calibration Ablation Study for ConfiRoute.

Compares:
1. S1 alone (Token probability)
2. S2 alone (Self-consistency)
3. S3 alone (Self-rated certainty)
4. S1 + S2
5. S1 + S3
6. S2 + S3
7. Full S1 + S2 + S3 (Dynamic weighted average)
8. Logistic Regression Meta-Model (Platt Scaling)
9. Isotonic Regression Calibration

Measures:
- Expected Calibration Error (ECE, 10 bins)
- AUROC
- Brier Score
- Accuracy at fixed threshold (tau = 0.70)
- UCER at fixed threshold
- Escalation rate at fixed threshold
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import argparse
import json
import numpy as np
import pandas as pd

from confiroute.config import get_config
from confiroute.confidence.combiner import combine_signals
from confiroute.confidence.calibration import ConfidenceCalibrator
from confiroute.eval.metrics import (
    compute_ece,
    compute_auroc,
    compute_auto_accuracy,
    compute_ucer,
    compute_escalation_rate,
)
from confiroute.eval.run_baselines import load_dataset_split
from confiroute.confidence.combiner import get_confidence


def compute_brier_score(
    probs: Union[np.ndarray, List[float]],
    labels: Union[np.ndarray, List[int]],
) -> float:
    """Compute Brier Score: mean squared error between probabilities and binary labels."""
    p = np.array(probs, dtype=np.float64)
    y = np.array(labels, dtype=np.float64)
    if len(p) == 0:
        return 0.0
    return round(float(np.mean((p - y) ** 2)), 4)


def run_ablation_study(
    records: List[Dict[str, Any]],
    eval_threshold: float = 0.70,
    output_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Evaluate confidence and calibration metrics across all signal combinations."""
    config = get_config()
    target_dir = output_dir or (config.root_dir / "reports" / "tables")
    target_dir.mkdir(parents=True, exist_ok=True)

    y_true = np.array([r["is_correct"] for r in records], dtype=np.int32)
    N = len(y_true)
    if N == 0:
        return pd.DataFrame()

    s1_vals = np.array([r.get("s1") if r.get("s1") is not None else 0.50 for r in records], dtype=np.float64)
    s2_vals = np.array([r.get("s2") if r.get("s2") is not None else 0.50 for r in records], dtype=np.float64)
    s3_vals = np.array([r.get("s3") if r.get("s3") is not None else 0.50 for r in records], dtype=np.float64)

    # 1. Prepare combinations
    comb_dict: Dict[str, np.ndarray] = {
        "S1 Alone (Token Prob)": s1_vals,
        "S2 Alone (Consistency)": s2_vals,
        "S3 Alone (Self-Rated)": s3_vals,
        "S1 + S2 (Dual Signal)": np.mean([s1_vals, s2_vals], axis=0),
        "S1 + S3 (Dual Signal)": np.mean([s1_vals, s3_vals], axis=0),
        "S2 + S3 (Dual Signal)": np.mean([s2_vals, s3_vals], axis=0),
        "S1 + S2 + S3 (Weighted Avg)": np.array([
            combine_signals(s1_vals[i], s2_vals[i], s3_vals[i])[0] for i in range(N)
        ]),
    }

    # 2. Add Platt scaling (Logistic Regression) & Isotonic Regression via cross-fitting
    X_features = np.column_stack([s1_vals, s2_vals, s3_vals])
    if len(np.unique(y_true)) >= 2 and N >= 10:
        cal_platt = ConfidenceCalibrator(method="platt")
        platt_preds = cal_platt.cross_fit_predict(X_features, y_true, n_splits=min(5, N // 2))
        comb_dict["Logistic Meta-Model (Platt)"] = platt_preds

        cal_iso = ConfidenceCalibrator(method="isotonic")
        iso_preds = cal_iso.cross_fit_predict(X_features, y_true, n_splits=min(5, N // 2))
        comb_dict["Calibrated (Isotonic)"] = iso_preds
    else:
        comb_dict["Logistic Meta-Model (Platt)"] = comb_dict["S1 + S2 + S3 (Weighted Avg)"]
        comb_dict["Calibrated (Isotonic)"] = comb_dict["S1 + S2 + S3 (Weighted Avg)"]

    # 3. Compute metrics for each variant
    ablation_rows = []
    for name, scores in comb_dict.items():
        is_auto = [s >= eval_threshold for s in scores]
        is_esc = [not a for a in is_auto]

        ece = compute_ece(scores, y_true)
        auroc = compute_auroc(scores, y_true)
        brier = compute_brier_score(scores, y_true)
        auto_acc = compute_auto_accuracy(y_true, is_auto)
        ucer = compute_ucer(y_true, is_auto)
        esc_rate = compute_escalation_rate(is_esc)

        ablation_rows.append({
            "configuration": name,
            "ece_10_bin": ece,
            "auroc": auroc if auroc is not None else 0.50,
            "brier_score": brier,
            "auto_accuracy": auto_acc,
            "ucer": ucer,
            "escalation_rate": esc_rate,
            "eval_threshold": eval_threshold,
        })

    df = pd.DataFrame(ablation_rows)

    # Save to disk
    csv_path = target_dir / "ablation_results.csv"
    json_path = target_dir / "ablation_results.json"
    df.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ablation_rows, f, indent=2)

    return df


def collect_ablation_records(
    split_name: str = "val",
    limit: int = 20,
    provider: str = "mock",
) -> List[Dict[str, Any]]:
    """Helper to collect confidence records on a split for ablation analysis."""
    dataset = load_dataset_split(split_name)
    if limit:
        dataset = dataset[:limit]

    records = []
    for item in dataset:
        conf_res = get_confidence(
            question=item["question"],
            options=item["options"],
            model_key="tier1",
            provider=provider,
        )
        corr = 1 if conf_res.get("answer") == item.get("correct_option") else 0
        records.append({
            "id": item["id"],
            "s1": conf_res.get("s1"),
            "s2": conf_res.get("s2"),
            "s3": conf_res.get("s3"),
            "combined": conf_res.get("combined"),
            "is_correct": corr,
        })
    return records


def main():
    parser = argparse.ArgumentParser(description="Run ConfiRoute signal and calibration ablation.")
    parser.add_argument("--split", choices=["dev", "val", "test"], default="val")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--provider", choices=["mock", "ollama", "groq"], default="mock")

    args = parser.parse_args()

    print(f"[ABLATION] Collecting {args.limit} records on {args.split} ({args.provider})...")
    records = collect_ablation_records(split_name=args.split, limit=args.limit, provider=args.provider)

    print(f"[ABLATION] Running ablation study across {len(records)} records...")
    df = run_ablation_study(records, eval_threshold=args.threshold)
    print("\n" + df[["configuration", "ece_10_bin", "auroc", "brier_score", "auto_accuracy", "ucer"]].to_string())
    print("\n[SUCCESS] Ablation results saved to reports/tables/ablation_results.csv")


if __name__ == "__main__":
    main()
