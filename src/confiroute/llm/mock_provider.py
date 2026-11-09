"""Mock LLM provider for ConfiRoute Milestone 1.

Simulates Tier 1 (and Tier 2) responses, token log-probabilities,
self-consistency sampling, and self-rated certainty deterministically.
"""

from typing import Any, Dict, List, Optional
import hashlib
import random
from confiroute.config import get_config


def _prompt_hash(prompt: str, seed: int) -> int:
    """Create a 32-bit deterministic integer hash from prompt and seed."""
    digest = hashlib.sha256(f"{seed}:{prompt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def generate_mock_response(
    model_key: str,
    prompt: str,
    temperature: float = 0.0,
    n: int = 1,
    logprobs: bool = False,
    options: Optional[List[str]] = None,
    simulated_level: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Generate a realistic, deterministic simulated LLM output."""
    config = get_config()
    seed = config.seed
    h = _prompt_hash(prompt, seed)
    rng = random.Random(h + int(temperature * 100) + n)

    letters = ["A", "B", "C", "D"]

    # Detect if prompt is asking for self-rated confidence (S3 prompt)
    is_self_rating_prompt = any(
        kw in prompt.lower()
        for kw in ["rate your confidence", "confidence 0-100", "scale 0-100", "how certain are you"]
    )

    # Estimate token counts
    prompt_tokens = max(15, int(len(prompt.split()) * 1.35))
    completion_tokens = 5 if not is_self_rating_prompt else 20

    if is_self_rating_prompt:
        # Determine certainty score based on simulated level or hash
        if simulated_level == "high":
            score = rng.randint(85, 98)
        elif simulated_level == "medium":
            score = rng.randint(55, 75)
        elif simulated_level == "low":
            score = rng.randint(20, 45)
        else:
            # Deterministic pseudo-random score
            score = 30 + (h % 66)  # Range 30 to 95

        text = f"Confidence Rating: {score}/100. Based on standard clinical guidelines."
        return {
            "text": text,
            "answers": [text],
            "logprobs": None,
            "mean_logprob": None,
            "self_rated_certainty": float(score),
            "tokens_prompt": prompt_tokens,
            "tokens_completion": completion_tokens,
            "is_mock": True,
        }

    # Standard MCQ answer generation
    # Primary answer choice
    primary_letter = letters[h % 4]

    # Sampled answers for S2 (self-consistency)
    if n > 1:
        if simulated_level == "high" or (h % 3 == 0):
            # Perfect agreement: e.g. ["A", "A", "A"]
            answers = [primary_letter] * n
        elif simulated_level == "medium" or (h % 3 == 1):
            # Majority agreement: e.g. ["A", "A", "B"]
            alt_letter = letters[(letters.index(primary_letter) + 1) % 4]
            answers = [primary_letter] * (n - 1) + [alt_letter]
        else:
            # Low agreement / conflict: e.g. ["A", "B", "C"]
            answers = [primary_letter]
            for i in range(1, n):
                answers.append(letters[(letters.index(primary_letter) + i) % 4])
    else:
        answers = [primary_letter]

    # Token log-probabilities for S1
    logprobs_dict = None
    mean_logprob = None

    if logprobs:
        if simulated_level == "high" or (h % 3 == 0):
            # High certainty logprobs
            logprobs_dict = {
                primary_letter: -0.12,  # ~88% prob
            }
            for l in letters:
                if l != primary_letter:
                    logprobs_dict[l] = -2.8 - (rng.random() * 0.5)
            mean_logprob = -0.15
        elif simulated_level == "medium" or (h % 3 == 1):
            # Moderate certainty logprobs
            logprobs_dict = {
                primary_letter: -0.45,  # ~63% prob
            }
            alt = letters[(letters.index(primary_letter) + 1) % 4]
            logprobs_dict[alt] = -1.1
            for l in letters:
                if l not in logprobs_dict:
                    logprobs_dict[l] = -3.2 - (rng.random() * 0.4)
            mean_logprob = -0.55
        else:
            # Low certainty / flat distribution
            logprobs_dict = {
                "A": -1.35,
                "B": -1.40,
                "C": -1.42,
                "D": -1.39,
            }
            mean_logprob = -1.38

    return {
        "text": primary_letter,
        "answers": answers,
        "logprobs": logprobs_dict,
        "mean_logprob": mean_logprob,
        "self_rated_certainty": None,
        "tokens_prompt": prompt_tokens,
        "tokens_completion": completion_tokens * n,
        "is_mock": True,
    }
