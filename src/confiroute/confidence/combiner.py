"""Signal Combiner and Main Confidence Estimation Engine for ConfiRoute.

Combines S1 (Token Probability), S2 (Self-Consistency), and S3 (Self-Rated Certainty)
into a single weighted confidence score with automatic weight redistribution.
"""

from typing import Any, Dict, List, Optional, Tuple
from confiroute.config import get_config
from confiroute.llm.base import ask_llm
from confiroute.confidence.token_prob import compute_s1_token_prob
from confiroute.confidence.consistency import compute_s2_consistency
from confiroute.confidence.self_rating import build_self_rating_prompt, parse_self_rating


def combine_signals(
    s1: Optional[float],
    s2: Optional[float],
    s3: Optional[float],
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """Compute weighted average of available signals with dynamic weight redistribution.

    Args:
        s1: Token probability score in [0, 1] or None.
        s2: Self-consistency score in [0, 1] or None.
        s3: Self-rated certainty score in [0, 1] or None.
        weights: Optional dict {'w_s1': float, 'w_s2': float, 'w_s3': float}.

    Returns:
        (combined_score, effective_weights)
    """
    config = get_config()
    if weights is None:
        w1 = config.weight_s1
        w2 = config.weight_s2
        w3 = config.weight_s3
    else:
        w1 = float(weights.get("w_s1", 0.40))
        w2 = float(weights.get("w_s2", 0.30))
        w3 = float(weights.get("w_s3", 0.30))

    signals = {"s1": s1, "s2": s2, "s3": s3}
    base_weights = {"s1": w1, "s2": w2, "s3": w3}

    # Filter available signals
    available = {k: v for k, v in signals.items() if v is not None}

    if not available:
        return 0.0, {"s1": 0.0, "s2": 0.0, "s3": 0.0}

    # Sum of base weights for available signals
    sum_avail_weights = sum(base_weights[k] for k in available)

    if sum_avail_weights <= 0.0:
        # Uniform fallback if all available weights were 0
        effective_weights = {k: 1.0 / len(available) for k in available}
    else:
        # Redistribute weights proportionally
        effective_weights = {
            k: base_weights[k] / sum_avail_weights for k in available
        }

    combined = sum(effective_weights[k] * available[k] for k in available)
    combined = max(0.0, min(1.0, float(combined)))

    # Return full weights mapping (0.0 for missing)
    full_effective = {
        "s1": effective_weights.get("s1", 0.0),
        "s2": effective_weights.get("s2", 0.0),
        "s3": effective_weights.get("s3", 0.0),
    }

    return round(combined, 4), full_effective


def format_mcq_prompt(question: str, options: Dict[str, str]) -> str:
    """Format multiple choice question for strict single-letter answer."""
    options_str = "\n".join([f"{k}: {v}" for k, v in sorted(options.items())])
    return (
        f"Answer the following medical multiple-choice question.\n"
        f"Output ONLY the single letter (A, B, C, or D) of the correct answer.\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Answer:"
    )


def get_confidence(
    question: str,
    options: Dict[str, str],
    model_key: str = "tier1",
    simulated_level: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Execute triple-signal confidence estimation for a medical question.

    Returns:
        Structured dictionary containing:
        - generated answer
        - s1, s2, s3 signal scores
        - combined confidence score
        - model & provider metadata
        - mock mode flag
        - token usage & reference costs
        - missing signals list
    """
    config = get_config()
    mcq_prompt = format_mcq_prompt(question, options)

    # 1. Primary answer call with logprobs (for S1)
    t1_resp = ask_llm(
        model_key=model_key,
        prompt=mcq_prompt,
        temperature=0.0,
        n=1,
        logprobs=True,
        simulated_level=simulated_level,
        use_cache=use_cache,
    )
    primary_answer = t1_resp.text.strip().upper()[:1]
    if primary_answer not in options:
        primary_answer = list(options.keys())[0]

    # Compute S1
    s1_score, norm_probs = compute_s1_token_prob(
        chosen_letter=primary_answer,
        logprobs=t1_resp.logprobs,
        candidate_letters=tuple(options.keys()),
    )

    # 2. Self-consistency call (S2)
    s2_resp = ask_llm(
        model_key=model_key,
        prompt=mcq_prompt,
        temperature=config.consistency_temperature,
        n=config.consistency_samples,
        logprobs=False,
        simulated_level=simulated_level,
        use_cache=use_cache,
    )
    s2_score, majority_ans, count_dist = compute_s2_consistency(s2_resp.answers)

    # 3. Self-rated certainty call (S3)
    s3_prompt = build_self_rating_prompt(question, primary_answer, options)
    s3_resp = ask_llm(
        model_key=model_key,
        prompt=s3_prompt,
        temperature=0.0,
        n=1,
        logprobs=False,
        simulated_level=simulated_level,
        use_cache=use_cache,
    )
    s3_score = parse_self_rating(s3_resp.text)

    # Combine signals
    combined_score, effective_weights = combine_signals(s1_score, s2_score, s3_score)

    missing_signals = []
    if s1_score is None:
        missing_signals.append("S1 (Token Probability)")
    if s2_score is None:
        missing_signals.append("S2 (Self-Consistency)")
    if s3_score is None:
        missing_signals.append("S3 (Self-Rated Certainty)")

    total_prompt_tokens = (
        t1_resp.tokens_prompt + s2_resp.tokens_prompt + s3_resp.tokens_prompt
    )
    total_completion_tokens = (
        t1_resp.tokens_completion + s2_resp.tokens_completion + s3_resp.tokens_completion
    )
    total_real_cost = t1_resp.cost_real + s2_resp.cost_real + s3_resp.cost_real
    total_eq_cost = round(
        t1_resp.cost_equivalent + s2_resp.cost_equivalent + s3_resp.cost_equivalent, 6
    )

    return {
        "answer": primary_answer,
        "s1": s1_score,
        "s2": s2_score,
        "s3": s3_score,
        "combined": combined_score,
        "effective_weights": effective_weights,
        "s1_details": {
            "mean_logprob": t1_resp.mean_logprob,
            "normalized_probs": norm_probs,
        },
        "s2_details": {
            "majority_answer": majority_ans,
            "sample_counts": count_dist,
            "samples": s2_resp.answers,
        },
        "s3_details": {
            "raw_response": s3_resp.text,
        },
        "model_info": {
            "model_key": model_key,
            "model_name": t1_resp.model,
            "provider": config.models.get(model_key, {}).get("provider", "mock"),
        },
        "is_mock": True,
        "tokens_used": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
        },
        "cost_metadata": {
            "real_cost": total_real_cost,
            "equivalent_cost": total_eq_cost,
            "currency": "USD",
        },
        "missing_signals": missing_signals,
    }
