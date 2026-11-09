"""Confidence estimation modules for ConfiRoute."""

from confiroute.confidence.token_prob import compute_s1_token_prob
from confiroute.confidence.consistency import compute_s2_consistency
from confiroute.confidence.self_rating import (
    build_self_rating_prompt,
    parse_self_rating,
)
from confiroute.confidence.combiner import (
    combine_signals,
    get_confidence,
    format_mcq_prompt,
)

__all__ = [
    "compute_s1_token_prob",
    "compute_s2_consistency",
    "build_self_rating_prompt",
    "parse_self_rating",
    "combine_signals",
    "get_confidence",
    "format_mcq_prompt",
]
