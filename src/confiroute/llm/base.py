"""Provider-agnostic LLM interface for ConfiRoute."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from confiroute.config import get_config
from confiroute.llm.cache import LLMDiskCache
from confiroute.llm.pricing import compute_costs
from confiroute.llm.providers import get_provider


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
    latency_ms: float = 0.0
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
    provider: Optional[str] = None,
    **kwargs: Any,
) -> LLMResponse:
    """Unified entry point for LLM interactions.

    Works seamlessly across Mock, Ollama, and Groq providers while enforcing
    deterministic caching and equivalent-cost accounting.
    """
    config = get_config()
    model_cfg = config.models.get(model_key, {})

    # Determine provider: parameter override -> config model provider -> mock fallback
    chosen_provider = provider or model_cfg.get("provider", "mock")
    if config.is_mock_mode and provider is None:
        chosen_provider = "mock"

    cache = get_disk_cache()

    cache_params = {
        "provider": chosen_provider,
        **kwargs,
    }

    if use_cache:
        cached_data = cache.get(model_key, prompt, temperature, n, logprobs, **cache_params)
        if cached_data is not None:
            return LLMResponse.from_dict(cached_data)

    provider_instance = get_provider(
        provider_name=chosen_provider,
        model_key=model_key,
        model_name=model_cfg.get("model_name"),
    )

    raw_response = provider_instance.generate(
        prompt=prompt,
        temperature=temperature,
        n=n,
        logprobs=logprobs,
        **kwargs,
    )

    # Compute reference pricing
    real_cost, eq_cost = compute_costs(
        model_key=model_key,
        tokens_prompt=raw_response.get("tokens_prompt", 0),
        tokens_completion=raw_response.get("tokens_completion", 0),
    )

    is_mock = raw_response.get("is_mock", chosen_provider == "mock")
    model_display = model_cfg.get("model_name", chosen_provider)

    response = LLMResponse(
        text=raw_response["text"],
        answers=raw_response.get("answers", [raw_response["text"]]),
        logprobs=raw_response.get("logprobs"),
        mean_logprob=raw_response.get("mean_logprob"),
        self_rated_certainty=raw_response.get("self_rated_certainty"),
        tokens_prompt=raw_response.get("tokens_prompt", 0),
        tokens_completion=raw_response.get("tokens_completion", 0),
        cost_real=real_cost,
        cost_equivalent=eq_cost,
        is_mock=is_mock,
        model=model_display,
        latency_ms=raw_response.get("latency_ms", 0.0),
        cached=False,
    )

    if use_cache:
        cache.put(model_key, prompt, temperature, n, logprobs, response.to_dict(), **cache_params)

    return response
