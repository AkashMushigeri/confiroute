"""Unit tests for Side-by-Side comparative demonstration logic."""

import importlib
import pytest
from confiroute.llm.base import ask_llm
from confiroute.routing.router import route_query
from confiroute.confidence.combiner import format_mcq_prompt


def test_comparison_presets_structure():
    """Verify comparison preset scenarios are well-formed."""
    sbs = importlib.import_module("app.pages.2_Side_by_Side")
    presets = sbs.COMPARISON_PRESETS

    assert len(presets) >= 4
    for name, data in presets.items():
        if data is None:
            continue
        assert "question" in data
        assert "options" in data
        assert isinstance(data["options"], dict)
        assert set(data["options"].keys()) == {"A", "B", "C", "D"}
        assert "description" in data


def test_unrouted_vs_routed_high_confidence():
    """Verify high-confidence scenario behaviour."""
    sbs = importlib.import_module("app.pages.2_Side_by_Side")
    scenario = sbs.COMPARISON_PRESETS["1. High-Confidence Factual Query (Safe to Answer)"]

    prompt = format_mcq_prompt(scenario["question"], scenario["options"])
    # Raw LLM responds directly
    unrouted_resp = ask_llm(model_key="tier1", prompt=prompt, simulated_level="high")
    assert unrouted_resp is not None
    assert len(unrouted_resp.text) > 0

    # Routed pipeline evaluates certainty
    decision = route_query(
        question=scenario["question"],
        options=scenario["options"],
        simulated_level="high",
    )
    assert decision.route in {"direct", "tier2"}
    assert decision.scores.get("combined", 0.0) >= 0.70


def test_unrouted_vs_routed_ambiguous_question():
    """Verify ambiguous scenario is held for escalation rather than unrouted blind answer."""
    sbs = importlib.import_module("app.pages.2_Side_by_Side")
    scenario = sbs.COMPARISON_PRESETS["2. Ambiguous / Hallucination-Prone Question"]

    # ConfiRoute flags low confidence and escalates
    decision = route_query(
        question=scenario["question"],
        options=scenario["options"],
        simulated_level="low",
    )
    # Low confidence should escalate away from direct release
    assert decision.route in {"tier2", "human"}


def test_unrouted_vs_routed_emergency_dosage():
    """Verify safety screening overrides high confidence in emergency scenarios."""
    sbs = importlib.import_module("app.pages.2_Side_by_Side")
    scenario = sbs.COMPARISON_PRESETS["4. High-Risk Emergency / Pediatric Dosage"]

    decision = route_query(
        question=scenario["question"],
        options=scenario["options"],
        simulated_level="high",
    )
    # High-risk queries MUST route to human review regardless of sim_level='high'
    assert decision.route == "human"
    assert decision.is_high_risk is True
