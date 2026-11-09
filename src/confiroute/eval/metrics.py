"""Evaluation metrics for confidence-aware routing.

Implements standard benchmark metrics defined in the ConfiRoute specification:
- Accuracy among auto-answered queries
- Unsafe Confident Error Rate (UCER)
- UCER for high-confidence queries (UCER_high)
- Expected Calibration Error (ECE, 10 equal-width bins)
- Escalation rate (queries routed to human clinician)
- Area Under the ROC Curve (AUROC)
- Latency and cost accounting
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.metrics import roc_auc_score


def compute_auto_accuracy(
    is_correct: Union[np.ndarray, List[int]],
    is_auto: Union[np.ndarray, List[bool]],
) -> float:
    """Compute accuracy strictly among automatically answered questions."""
    corr = np.array(is_correct, dtype=np.int32)
    auto = np.array(is_auto, dtype=bool)

    auto_count = np.sum(auto)
    if auto_count == 0:
        return 0.0

    correct_auto = np.sum(corr[auto] == 1)
    return round(float(correct_auto / auto_count), 4)


def compute_ucer(
    is_correct: Union[np.ndarray, List[int]],
    is_auto: Union[np.ndarray, List[bool]],
) -> float:
    """Compute Unsafe Confident Error Rate (UCER).

    UCER = (auto_answered AND wrong) / total_queries
    Measures the frequency of erroneous answers silently shown to users.
    """
    corr = np.array(is_correct, dtype=np.int32)
    auto = np.array(is_auto, dtype=bool)
    total = len(corr)

    if total == 0:
        return 0.0

    unsafe_errors = np.sum((auto == True) & (corr == 0))
    return round(float(unsafe_errors / total), 4)


def compute_ucer_high(
    is_correct: Union[np.ndarray, List[int]],
    is_auto: Union[np.ndarray, List[bool]],
    scores: Union[np.ndarray, List[float]],
    high_threshold: float = 0.80,
) -> float:
    """Compute UCER among queries with confidence >= high_threshold."""
    corr = np.array(is_correct, dtype=np.int32)
    auto = np.array(is_auto, dtype=bool)
    s = np.array(scores, dtype=np.float64)

    high_mask = (auto == True) & (s >= high_threshold)
    high_count = np.sum(high_mask)

    if high_count == 0:
        return 0.0

    wrong_high = np.sum(high_mask & (corr == 0))
    return round(float(wrong_high / high_count), 4)


def compute_ece(
    confidence_scores: Union[np.ndarray, List[float]],
    is_correct: Union[np.ndarray, List[int]],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE) across 10 equal-width bins.

    Formula:
    ECE = sum_{b=1}^M (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    conf = np.array(confidence_scores, dtype=np.float64)
    corr = np.array(is_correct, dtype=np.int32)
    N = len(conf)

    if N == 0:
        return 0.0

    # Clean any NaNs or out of bounds
    conf = np.clip(np.nan_to_num(conf, nan=0.5), 0.0, 1.0)

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for b in range(n_bins):
        low, high = bin_boundaries[b], bin_boundaries[b + 1]
        if b == n_bins - 1:
            in_bin = (conf >= low) & (conf <= high)
        else:
            in_bin = (conf >= low) & (conf < high)

        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(corr[in_bin])
            bin_conf = np.mean(conf[in_bin])
            ece += (bin_size / N) * abs(bin_acc - bin_conf)

    return round(float(ece), 4)


def compute_escalation_rate(
    is_escalated: Union[np.ndarray, List[bool]],
) -> float:
    """Calculate fraction of total queries escalated to human review."""
    esc = np.array(is_escalated, dtype=bool)
    if len(esc) == 0:
        return 0.0
    return round(float(np.mean(esc)), 4)


def compute_auroc(
    confidence_scores: Union[np.ndarray, List[float]],
    is_correct: Union[np.ndarray, List[int]],
) -> Optional[float]:
    """Calculate Area Under the ROC Curve (AUROC) for distinguishing correct from wrong answers."""
    conf = np.array(confidence_scores, dtype=np.float64)
    corr = np.array(is_correct, dtype=np.int32)

    if len(conf) == 0 or len(np.unique(corr)) < 2:
        # Both positive (correct) and negative (incorrect) instances are required for AUROC
        return None

    conf_clean = np.clip(np.nan_to_num(conf, nan=0.5), 0.0, 1.0)
    try:
        score = roc_auc_score(corr, conf_clean)
        return round(float(score), 4)
    except Exception:
        return None


def compute_all_metrics(
    is_correct: List[int],
    routes: List[str],
    confidence_scores: List[float],
    high_threshold: float = 0.80,
    latencies: Optional[List[float]] = None,
    costs: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Calculate a complete suite of ConfiRoute benchmark metrics."""
    total = len(is_correct)
    if total == 0:
        return {}

    is_auto = [r == "direct" for r in routes]
    direct_c = sum(1 for r in routes if r == "direct")
    tier2_c = sum(1 for r in routes if r == "tier2")
    human_c = sum(1 for r in routes if r == "human")
    is_esc = [r in {"human", "tier2"} for r in routes]

    auto_acc = compute_auto_accuracy(is_correct, is_auto)
    ucer = compute_ucer(is_correct, is_auto)
    ucer_high = compute_ucer_high(is_correct, is_auto, confidence_scores, high_threshold=high_threshold)
    ece = compute_ece(confidence_scores, is_correct)
    esc_rate = compute_escalation_rate(is_esc)
    auroc = compute_auroc(confidence_scores, is_correct)

    mean_lat = round(float(np.mean(latencies)), 2) if latencies else 0.0
    mean_cost = round(float(np.mean(costs)), 6) if costs else 0.0
    total_cost = round(float(np.sum(costs)), 6) if costs else 0.0

    return {
        "total_queries": total,
        "auto_count": direct_c,
        "auto_answered": direct_c,
        "direct_count": direct_c,
        "tier2_count": tier2_c,
        "human_count": human_c,
        "auto_accuracy": auto_acc,
        "ucer": ucer,
        "ucer_high": ucer_high,
        "ece": ece,
        "escalation_rate": esc_rate,
        "auroc": auroc,
        "mean_latency_ms": mean_lat,
        "mean_equivalent_cost": mean_cost,
        "total_equivalent_cost_usd": total_cost,
    }
