"""Signal 3 (S3): Self-Rated Certainty Confidence.

Prompts the model to rate its confidence on a scale of 0-100 for its own answer
and parses the numerical rating into a normalized 0.0-1.0 score.
"""

from typing import Optional
import re


def build_self_rating_prompt(question: str, chosen_answer: str, options: dict) -> str:
    """Construct prompt asking LLM to self-evaluate certainty for its answer."""
    options_str = "\n".join([f"{k}: {v}" for k, v in options.items()])
    return (
        f"Question:\n{question}\n\n"
        f"Options:\n{options_str}\n\n"
        f"Proposed Answer: {chosen_answer}\n\n"
        "Please rate your confidence in this answer on a scale from 0 to 100, "
        "where 0 means completely uncertain and 100 means completely certain.\n"
        "Provide your rating in the format: 'Confidence: X/100'."
    )


def parse_self_rating(text: Optional[str]) -> Optional[float]:
    """Robustly parse 0-100 certainty score from text into a 0.0-1.0 float."""
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip()

    # Pattern 1: X/100 or X / 100
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*100", cleaned)
    if m:
        try:
            val = float(m.group(1))
            if 0.0 <= val <= 100.0:
                return round(val / 100.0, 4)
        except ValueError:
            pass

    # Pattern 2: Confidence: X% or X%
    m = re.search(r"(?:confidence|certainty)?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*%", cleaned, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            if 0.0 <= val <= 100.0:
                return round(val / 100.0, 4)
        except ValueError:
            pass

    # Pattern 3: Confidence: X (where X is a number up to 100)
    m = re.search(r"(?:confidence|certainty|score|rating)\s*[:=\-]?\s*(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            if 0.0 <= val <= 1.0:
                return round(val, 4)
            elif 1.0 < val <= 100.0:
                return round(val / 100.0, 4)
        except ValueError:
            pass

    # Pattern 4: Bare number on its own line or start of string
    m = re.search(r"^\s*(\d+(?:\.\d+)?)\s*$", cleaned)
    if m:
        try:
            val = float(m.group(1))
            if 0.0 <= val <= 1.0:
                return round(val, 4)
            elif 1.0 < val <= 100.0:
                return round(val / 100.0, 4)
        except ValueError:
            pass

    return None
