"""Signal 2 (S2): Self-Consistency Confidence.

Evaluates model certainty by sampling N responses to the same question at
a non-zero temperature (default 0.7) and measuring agreement with the majority.
"""

from typing import Dict, List, Optional, Tuple
from collections import Counter


def compute_s2_consistency(
    answers: List[str],
) -> Tuple[float, str, Dict[str, int]]:
    """Compute self-consistency score from sampled answers.

    Args:
        answers: List of sampled answer letters (e.g. ['A', 'A', 'B']).

    Returns:
        (consistency_score, majority_answer, count_distribution)
    """
    if not answers:
        return 0.0, "", {}

    # Clean and uppercase letters
    cleaned = [str(a).strip().upper()[:1] for a in answers if str(a).strip()]
    if not cleaned:
        return 0.0, "", {}

    counts = Counter(cleaned)
    majority_letter, top_count = counts.most_common(1)[0]
    total_samples = len(cleaned)

    score = top_count / float(total_samples)
    score = max(0.0, min(1.0, score))

    return round(score, 4), majority_letter, dict(counts)
