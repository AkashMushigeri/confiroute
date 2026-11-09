"""Tests for Ollama and Groq providers using mocked HTTP responses."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from confiroute.llm.providers import (
    OllamaProvider,
    GroqProvider,
    MissingAPIKeyError,
    ProviderUnavailableError,
    RateLimitExceededError,
    ProviderError,
    get_provider,
)


def test_ollama_provider_success_with_logprobs():
    provider = OllamaProvider(model_name="llama3.2:1b", base_url="http://localhost:11434")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "llama3.2:1b",
        "response": "A",
        "prompt_eval_count": 45,
        "eval_count": 4,
        "logprobs": {
            "tokens": [
                {"token": "A", "logprob": -0.15},
                {"token": "B", "logprob": -2.50},
                {"token": "C", "logprob": -3.20},
                {"token": "D", "logprob": -4.10},
            ],
            "mean_logprob": -0.22,
        },
    }

    with patch("requests.post", return_value=mock_resp):
        res = provider.generate("Medical question prompt", logprobs=True)

    assert res["text"] == "A"
    assert res["is_mock"] is False
    assert res["logprobs"] is not None
    assert "A" in res["logprobs"]
    assert pytest.approx(res["logprobs"]["A"]) == -0.15
    assert res["tokens_prompt"] == 45
    assert res["tokens_completion"] == 4
    assert res["latency_ms"] >= 0.0


def test_ollama_provider_connection_offline():
    provider = OllamaProvider(base_url="http://localhost:11434")

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        with pytest.raises(ProviderUnavailableError) as exc_info:
            provider.generate("Test prompt")
        assert "Cannot connect to local Ollama service" in str(exc_info.value)


def test_groq_provider_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        provider = GroqProvider(api_key="")
        with pytest.raises(MissingAPIKeyError) as exc_info:
            provider.generate("Test prompt")
        assert "GROQ_API_KEY is not configured" in str(exc_info.value)


def test_groq_provider_success():
    provider = GroqProvider(api_key="gsk_test_fake_key_123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {"role": "assistant", "content": "B"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 60,
            "completion_tokens": 5,
            "total_tokens": 65,
        },
    }

    with patch("requests.post", return_value=mock_resp):
        res = provider.generate("What is the first-line medication?", n=1)

    assert res["text"] == "B"
    assert res["is_mock"] is False
    assert res["logprobs"] is None  # Groq returns None for logprobs
    assert res["tokens_prompt"] == 60
    assert res["tokens_completion"] == 5


def test_groq_provider_rate_limit_backoff_and_exhaustion():
    provider = GroqProvider(
        api_key="gsk_test_fake_key_123",
        max_retries=2,
        backoff_factor=0.01,  # Fast sleep for unit tests
    )

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate limit reached"

    with patch("requests.post", return_value=mock_429), patch("time.sleep") as mock_sleep:
        with pytest.raises(RateLimitExceededError) as exc_info:
            provider.generate("Prompt")
        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert mock_sleep.call_count == 2


def test_get_provider_factory():
    p_mock = get_provider("mock")
    p_ollama = get_provider("ollama")
    p_groq = get_provider("groq")

    assert p_mock.__class__.__name__ == "MockProvider"
    assert p_ollama.__class__.__name__ == "OllamaProvider"
    assert p_groq.__class__.__name__ == "GroqProvider"
