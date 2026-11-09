"""LLM Providers interface: Mock, Local Ollama, and Cloud Groq.

Supports configurable model endpoints, deterministic MCQ answering,
token log-probabilities when available, latency tracking, retry backoff on 429,
and disk caching integration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import os
import time
import requests
from confiroute.config import get_config
from confiroute.llm.mock_provider import generate_mock_response


class ProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class MissingAPIKeyError(ProviderError):
    """Raised when an API key is missing from environment or config."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when the provider cannot be reached (e.g., service offline or connection refused)."""
    pass


class RateLimitExceededError(ProviderError):
    """Raised when rate limits (HTTP 429) persist after retries."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        n: int = 1,
        logprobs: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate one or more completions and return a standardized response dictionary."""
        raise NotImplementedError


class MockProvider(BaseLLMProvider):
    """Deterministic Mock LLM provider for zero-cost offline development and testing."""

    def __init__(self, model_key: str = "tier1"):
        self.model_key = model_key

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        n: int = 1,
        logprobs: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        resp = generate_mock_response(
            model_key=self.model_key,
            prompt=prompt,
            temperature=temperature,
            n=n,
            logprobs=logprobs,
            **kwargs,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        resp["latency_ms"] = round(latency_ms, 2)
        return resp


class OllamaProvider(BaseLLMProvider):
    """Local Tier 1 provider interfacing with Ollama API (http://localhost:11434)."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        config = get_config()
        t1_cfg = config.models.get("tier1", {})
        self.model_name = model_name or t1_cfg.get("model_name", "llama3.2:1b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or t1_cfg.get("base_url", "http://localhost:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _call_ollama_generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        logprobs: bool = False,
    ) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/generate"
        options: Dict[str, Any] = {
            "temperature": float(temperature),
        }
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if logprobs:
            # Some Ollama versions support logprobs / top_logprobs
            payload["logprobs"] = True

        try:
            resp = requests.post(endpoint, json=payload, timeout=self.timeout_seconds)
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                f"Cannot connect to local Ollama service at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`), or switch to Mock mode."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise ProviderUnavailableError(
                f"Ollama request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except Exception as exc:
            raise ProviderError(f"Unexpected error calling Ollama: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

        return resp.json()

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        n: int = 1,
        logprobs: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        answers: List[str] = []
        raw_logprobs: Optional[Dict[str, float]] = None
        mean_logprob: Optional[float] = None
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for _ in range(n):
            data = self._call_ollama_generate(prompt, temperature=temperature, logprobs=logprobs)
            text = data.get("response", "").strip()
            answers.append(text)

            prompt_toks = data.get("prompt_eval_count", 0)
            comp_toks = data.get("eval_count", 0)
            total_prompt_tokens += prompt_toks
            total_completion_tokens += comp_toks

            # Extract logprobs if returned by Ollama
            if logprobs and "logprobs" in data and raw_logprobs is None:
                lp_data = data.get("logprobs")
                if isinstance(lp_data, dict):
                    # Ollama logprobs structure parsing
                    raw_logprobs = {}
                    for token_info in lp_data.get("tokens", []):
                        tok = str(token_info.get("token", "")).strip().upper()
                        if tok in {"A", "B", "C", "D"} and tok not in raw_logprobs:
                            raw_logprobs[tok] = float(token_info.get("logprob", 0.0))
                    mean_logprob = lp_data.get("mean_logprob")

        latency_ms = (time.perf_counter() - start) * 1000.0

        primary_text = answers[0] if answers else ""

        return {
            "text": primary_text,
            "answers": answers,
            "logprobs": raw_logprobs,
            "mean_logprob": mean_logprob,
            "self_rated_certainty": None,
            "tokens_prompt": total_prompt_tokens or int(len(prompt.split()) * 1.3),
            "tokens_completion": total_completion_tokens or (len(answers) * 5),
            "is_mock": False,
            "latency_ms": round(latency_ms, 2),
        }


class GroqProvider(BaseLLMProvider):
    """Cloud Tier 2 provider interfacing with Groq Free-Tier API."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        config = get_config()
        t2_cfg = config.models.get("tier2", {})
        self.model_name = model_name or t2_cfg.get("model_name", "llama-3.3-70b-versatile")
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.base_url = (base_url or t2_cfg.get("base_url", "https://api.groq.com/openai/v1")).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _execute_chat_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        n: int = 1,
    ) -> Dict[str, Any]:
        if not self.api_key or not self.api_key.strip():
            raise MissingAPIKeyError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your .env file. "
                "You can obtain a free Groq API key with ₹0 budget at https://console.groq.com."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "ConfiRoute/0.2.0",
        }
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": 150,
            "n": int(n),
        }

        retries = 0
        while True:
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=self.timeout_seconds)
            except requests.exceptions.ConnectionError as exc:
                raise ProviderUnavailableError(f"Failed to connect to Groq API endpoint: {self.base_url}") from exc
            except requests.exceptions.Timeout as exc:
                raise ProviderUnavailableError(f"Groq API request timed out after {self.timeout_seconds} seconds.") from exc
            except Exception as exc:
                raise ProviderError(f"Unexpected error connecting to Groq API: {exc}") from exc

            # Handle 429 Rate Limits with exponential backoff
            if resp.status_code == 429:
                retries += 1
                if retries > self.max_retries:
                    raise RateLimitExceededError(
                        f"Groq free-tier rate limit exceeded after {self.max_retries} retries. "
                        "The daily or minute token limit on Groq free tier has been reached."
                    )
                # Exponential backoff sleep
                sleep_sec = self.backoff_factor * (2 ** (retries - 1))
                time.sleep(sleep_sec)
                continue

            if resp.status_code == 401:
                raise MissingAPIKeyError("Invalid Groq API key provided. Check GROQ_API_KEY in .env.")

            if resp.status_code != 200:
                raise ProviderError(f"Groq API returned HTTP {resp.status_code}: {resp.text}")

            return resp.json()

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        n: int = 1,
        logprobs: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        messages = [
            {"role": "user", "content": prompt}
        ]

        answers: List[str] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Note: If n > 1 and temperature > 0, make calls or use n parameter if supported
        for _ in range(n):
            data = self._execute_chat_request(messages, temperature=temperature, n=1)
            choices = data.get("choices", [])
            for c in choices:
                msg = c.get("message", {}).get("content", "")
                answers.append(msg.strip())

            usage = data.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)

        latency_ms = (time.perf_counter() - start) * 1000.0

        primary_text = answers[0] if answers else ""

        # Groq currently does not support normalized logprobs for this endpoint; return None gracefully
        return {
            "text": primary_text,
            "answers": answers,
            "logprobs": None,
            "mean_logprob": None,
            "self_rated_certainty": None,
            "tokens_prompt": total_prompt_tokens,
            "tokens_completion": total_completion_tokens,
            "is_mock": False,
            "latency_ms": round(latency_ms, 2),
        }


def get_provider(
    provider_name: str,
    model_key: str = "tier1",
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory to instantiate the appropriate provider."""
    p_lower = str(provider_name).strip().lower()

    if p_lower == "ollama":
        return OllamaProvider(model_name=model_name)
    elif p_lower == "groq":
        return GroqProvider(model_name=model_name)
    elif p_lower in {"mock", "simulated"}:
        return MockProvider(model_key=model_key)
    else:
        # Default fallback to mock
        return MockProvider(model_key=model_key)
