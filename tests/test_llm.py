"""Tests for Mock LLM, disk caching, and reference pricing."""

import tempfile
from pathlib import Path
from confiroute.llm.base import ask_llm
from confiroute.llm.cache import LLMDiskCache
from confiroute.llm.pricing import compute_costs
from confiroute.llm.mock_provider import generate_mock_response


def test_mock_response_deterministic():
    prompt = "Which antibiotic is first line for syphilis?"
    r1 = generate_mock_response("tier1", prompt, temperature=0.0)
    r2 = generate_mock_response("tier1", prompt, temperature=0.0)
    assert r1["text"] == r2["text"]
    assert r1["is_mock"] is True


def test_mock_sampling_and_logprobs():
    prompt = "Question about pharmacology"
    r = generate_mock_response("tier1", prompt, temperature=0.7, n=3, logprobs=True)
    assert len(r["answers"]) == 3
    assert r["logprobs"] is not None
    assert set(r["logprobs"].keys()) == {"A", "B", "C", "D"}


def test_disk_cache_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LLMDiskCache(cache_dir=Path(tmpdir))
        model_key = "test_model"
        prompt = "Hello medical world"
        temp = 0.0

        # Empty cache
        assert cache.get(model_key, prompt, temp, 1, False) is None

        # Put and retrieve
        test_payload = {"text": "A", "tokens_prompt": 10, "tokens_completion": 2}
        cache.put(model_key, prompt, temp, 1, False, test_payload)

        cached = cache.get(model_key, prompt, temp, 1, False)
        assert cached is not None
        assert cached["text"] == "A"
        assert cached["cached"] is True


def test_compute_costs():
    real, eq = compute_costs("tier1", tokens_prompt=1000, tokens_completion=500)
    assert real == 0.0  # Zero-cost rule
    assert eq > 0.0     # Reference cost is positive
