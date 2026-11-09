"""Signal 1 (S1): Token Probability Confidence.

Computes the normalized probability of the selected option letter
across candidate options (A, B, C, D) using numerically stable softmax.
"""

from typing import Dict, Optional, Tuple
import math


def compute_s1_token_prob(
    chosen_letter: str,
    logprobs: Optional[Dict[str, float]],
    candidate_letters: Optional[Tuple[str, ...]] = ("A", "B", "C", "D"),
) -> Tuple[Optional[float], Optional[Dict[str, float]]]:
    """Calculate normalized token probability for chosen letter.

    Args:
        chosen_letter: Selected option letter (e.g. 'A').
        logprobs: Dictionary mapping candidate letters to log-probabilities.
        candidate_letters: Tuple of valid candidate letters.

    Returns:
        (s1_score, normalized_probs_dict) or (None, None) if logprobs unavailable.
    """
    if not logprobs or not isinstance(logprobs, dict):
        return None, None

    # Filter available candidate logprobs
    valid_logprobs = {
        letter: logprobs[letter]
        for letter in candidate_letters
        if letter in logprobs and logprobs[letter] is not None
    }

    if not valid_logprobs or chosen_letter not in valid_logprobs:
        return None, None

    # Numerically stable softmax: subtract max logprob
    max_lp = max(valid_logprobs.values())
    exp_terms = {letter: math.exp(lp - max_lp) for letter, lp in valid_logprobs.items()}
    sum_exp = sum(exp_terms.values())

    if sum_exp <= 0.0:
        return None, None

    normalized_probs = {letter: exp_terms[letter] / sum_exp for letter in valid_logprobs}
    s1_score = normalized_probs.get(chosen_letter)

    if s1_score is not None:
        s1_score = max(0.0, min(1.0, float(s1_score)))

    return s1_score, normalized_probs
