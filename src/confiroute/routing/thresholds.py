"""Threshold tuning and Pareto trade-off optimization for ConfiRoute.

Conducts grid search over validation split predictions to optimize
confidence thresholds balancing accuracy, UCER, and human escalation rate.

Rule:
Threshold tuning must occur STRICTLY on the VALIDATION split, never on the TEST split.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import numpy as np
import pandas as pd

from confiroute.config import get_config
from confiroute.eval.metrics import (
    compute_auto_accuracy,
    compute_ucer,
    compute_ucer_high,
    compute_escalation_rate,
)


def simulate_routing_for_thresholds(
    confidence_scores: List[float],
    is_correct: List[int],
    is_high_risk: List[bool],
    low_threshold: float,
    high_threshold: float,
) -> Dict[str, float]:
    """Simulate routing decisions across a dataset for specific (low, high) thresholds."""
    routes: List[str] = []

    for s, risk in zip(confidence_scores, is_high_risk):
        if risk:
            routes.append("human")
        elif s >= high_threshold:
            routes.append("direct")
        elif s >= low_threshold:
            routes.append("tier2")
        else:
            routes.append("human")

    is_auto = [r == "direct" for r in routes]
    is_esc = [r in {"human", "tier2"} for r in routes]

    auto_acc = compute_auto_accuracy(is_correct, is_auto)
    ucer = compute_ucer(is_correct, is_auto)
    ucer_high = compute_ucer_high(is_correct, is_auto, confidence_scores, high_threshold=high_threshold)
    esc_rate = compute_escalation_rate(is_esc)

    return {
        "low_threshold": round(low_threshold, 2),
        "high_threshold": round(high_threshold, 2),
        "auto_accuracy": auto_acc,
        "ucer": ucer,
        "ucer_high": ucer_high,
        "escalation_rate": esc_rate,
        "auto_count": sum(is_auto),
        "total_count": len(confidence_scores),
    }


def grid_search_thresholds(
    confidence_scores: List[float],
    is_correct: List[int],
    is_high_risk: List[bool],
    low_range: Tuple[float, float, float] = (0.30, 0.70, 0.05),
    high_range: Tuple[float, float, float] = (0.60, 0.95, 0.05),
    objective: str = "min_ucer",  # "min_ucer", "max_utility"
    max_escalation: float = 0.40,
    tradeoff_lambda: float = 0.5,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Execute grid search across thresholds and select optimal Pareto configuration."""
    low_min, low_max, low_step = low_range
    high_min, high_max, high_step = high_range

    low_candidates = np.arange(low_min, low_max + 1e-5, low_step)
    high_candidates = np.arange(high_min, high_max + 1e-5, high_step)

    results: List[Dict[str, float]] = []

    for low_t in low_candidates:
        for high_t in high_candidates:
            if high_t <= low_t:
                continue

            metrics = simulate_routing_for_thresholds(
                confidence_scores=confidence_scores,
                is_correct=is_correct,
                is_high_risk=is_high_risk,
                low_threshold=float(low_t),
                high_threshold=float(high_t),
            )

            # Compute composite utility: accuracy - lambda * escalation
            utility = metrics["auto_accuracy"] - (tradeoff_lambda * metrics["escalation_rate"])
            metrics["utility"] = round(float(utility), 4)

            results.append(metrics)

    df_results = pd.DataFrame(results)

    if df_results.empty:
        # Default fallback
        config = get_config()
        fallback = {
            "low_threshold": config.threshold_low,
            "high_threshold": config.threshold_high,
            "auto_accuracy": 0.0,
            "ucer": 0.0,
            "escalation_rate": 0.0,
            "utility": 0.0,
        }
        return fallback, df_results

    # Select best configuration based on objective
    if objective == "min_ucer":
        # Minimize UCER subject to escalation_rate <= max_escalation
        filtered = df_results[df_results["escalation_rate"] <= max_escalation]
        if not filtered.empty:
            best_row = filtered.sort_values(by=["ucer", "auto_accuracy"], ascending=[True, False]).iloc[0]
        else:
            best_row = df_results.sort_values(by=["ucer", "auto_accuracy"], ascending=[True, False]).iloc[0]
    elif objective == "max_utility":
        best_row = df_results.sort_values(by=["utility", "auto_accuracy"], ascending=[False, False]).iloc[0]
    else:
        best_row = df_results.sort_values(by=["utility"], ascending=[False]).iloc[0]

    chosen = dict(best_row)
    return chosen, df_results


def save_thresholds(
    low_threshold: Union[float, Dict[str, Any]],
    high_threshold: Optional[Union[float, Path, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    file_path: Optional[Union[Path, str]] = None,
) -> Path:
    """Save tuned threshold configuration to JSON.

    Supports both:
    1. save_thresholds(optimal_dict, file_path=..., metadata=...)
    2. save_thresholds(low_threshold, high_threshold, metadata, file_path=...)
    """
    if isinstance(low_threshold, dict):
        d = low_threshold
        t_low = float(d.get("low_threshold", d.get("threshold_low", 0.50)))
        t_high = float(d.get("high_threshold", d.get("threshold_high", 0.80)))
        meta = metadata or {}
        # If second arg is a path
        if isinstance(high_threshold, (str, Path)):
            target_path = Path(high_threshold)
        elif file_path is not None:
            target_path = Path(file_path)
        else:
            config = get_config()
            target_path = config.root_dir / "reports" / "tables" / "tuned_thresholds.json"
    else:
        t_low = float(low_threshold)
        t_high = float(high_threshold) if high_threshold is not None else 0.80
        meta = metadata or {}
        target_path = Path(file_path) if file_path is not None else (get_config().root_dir / "reports" / "tables" / "tuned_thresholds.json")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "threshold_low": round(t_low, 4),
        "threshold_high": round(t_high, 4),
        "low_threshold": round(t_low, 4),
        "high_threshold": round(t_high, 4),
        "metadata": meta,
    }
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return target_path
