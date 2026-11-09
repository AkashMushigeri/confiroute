"""Pricing and token cost computation for ConfiRoute.

Zero-cost rule:
Real cost is always ₹0 / $0.00 (local Ollama or free Groq tier / mock).
Equivalent cost is computed using reference per-token prices from config.yaml
so that cost comparisons between model tiers remain meaningful.
"""

from typing import Dict, Tuple
from confiroute.config import get_config


def compute_costs(
    model_key: str,
    tokens_prompt: int,
    tokens_completion: int,
) -> Tuple[float, float]:
    """Calculate (real_cost, equivalent_cost) in USD."""
    config = get_config()
    pricing = config.get_reference_pricing(model_key)

    input_rate = pricing.get("input_per_1k_tokens", 0.0)
    output_rate = pricing.get("output_per_1k_tokens", 0.0)

    # Real cost is always zero on local / free-tier / mock
    real_cost = 0.0

    # Equivalent cost per 1K tokens
    equivalent_cost = (
        (tokens_prompt * input_rate / 1000.0)
        + (tokens_completion * output_rate / 1000.0)
    )

    return real_cost, round(equivalent_cost, 6)
