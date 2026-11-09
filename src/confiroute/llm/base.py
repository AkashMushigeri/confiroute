"""Provider-agnostic LLM interface for ConfiRoute."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from confiroute.config import get_config
from confiroute.llm.cache import LLMDiskCache
from confiroute.llm.pricing import compute_costs


@dataclass
class LLMResponse:
    """Standardized response container across all LLM providers (Mock, Ollama, Groq)."""

    text: str
    answers: List[str]
    logprobs: Optional[Dict[str, float]]
    mean_logprob: Optional[float]
    self_rated_certainty: Optional[float]
    tokens_prompt: int
    tokens_completion: int
    cost_real: float
    cost_equivalent: float
    is_mock: bool
    model: str
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponse":
        return cls(**data)


_disk_cache: Optional[LLMDiskCache] = None


def get_disk_cache() -> LLMDiskCache:
    global _disk_cache
    if _disk_cache is None:
        _disk_cache = LLMDiskCache()
    return _disk_cache


def ask_llm(
    model_key: str = "tier1",
    prompt: str = "",
    temperature: float = 0.0,
    n: int = 1,
    logprobs: bool = False,
    use_cache: bool = True,
    **kwargs: Any,
) -> LLMResponse:
    """Unified entry point for LLM interactions.

    Works across Mock, Ollama, and Groq providers while enforcing
    deterministic caching and equivalent-cost accounting.
    """
    cache = get_disk_cache()

    if use_cache:
        cached_data = cache.get(model_key, prompt, temperature, n, logprobs, **kwargs)
        if cached_data is not None:
            return LLMResponse.from_dict(cached_data)

    config = get_config()
    model_cfg = config.models.get(model_key, {})
    provider_name = model_cfg.get("provider", "mock")

    # In Milestone 1, we use mock_provider.
    # Future phases can seamlessly route to ollama_provider or groq_provider.
    from confiroute.llm.mock_provider import generate_mock_response

    raw_response = generate_mock_response(
        model_key=model_key,
        prompt=prompt,
        temperature=temperature,
        n=n,
        logprobs=logprobs,
        **kwargs,
    )

    # Compute reference pricing
    real_cost, eq_cost = compute_costs(
        model_key=model_key,
        tokens_prompt=raw_response["tokens_prompt"],
        tokens_completion=raw_response["tokens_completion"],
    )

    response = LLMResponse(
        text=raw_response["text"],
        answers=raw_response["answers"],
        logprobs=raw_response.get("logprobs"),
        mean_logprob=raw_response.get("mean_logprob"),
        self_rated_certainty=raw_response.get("self_rated_certainty"),
        tokens_prompt=raw_response["tokens_prompt"],
        tokens_completion=raw_response["tokens_completion"],
        cost_real=real_cost,
        cost_equivalent=eq_cost,
        is_mock=True,
        model=model_cfg.get("model_name", "mock-model"),
        cached=False,
    )

    if use_cache:
        cache.put(model_key, prompt, temperature, n, logprobs, response.to_dict(), **kwargs)

    return response
