"""
Automated tests for MetricExplainer and FundamentalAgent integration.

Run: python -m pytest tests/test_metric_explainer.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.agents.metric_explainer import (
    LLMProvider,
    MetricExplainer,
    METRIC_KEYS,
    FALLBACK_EXPLANATIONS,
)


# ═══════════════════════════════════════════════════════════
#  Test Doubles
# ═══════════════════════════════════════════════════════════


class FakeLLMProvider(LLMProvider):
    """Controllable fake for testing — returns a preset JSON response."""

    def __init__(self, response: str | None = None, should_fail: bool = False):
        self._response = response
        self._should_fail = should_fail
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        if self._should_fail:
            raise ConnectionError("Simulated LLM failure")
        if self._response:
            return self._response
        # Default: generate a valid JSON response for all metrics
        return json.dumps({k: f"Explanation for {k}" for k in METRIC_KEYS})


# ═══════════════════════════════════════════════════════════
#  MetricExplainer Unit Tests
# ═══════════════════════════════════════════════════════════


class TestMetricExplainer:
    """Tests for the MetricExplainer caching and fallback logic."""

    def test_returns_all_16_metric_keys(self):
        """LLM response should populate all 16 metric keys."""
        provider = FakeLLMProvider()
        explainer = MetricExplainer(provider=provider)
        result = explainer.explanations

        for key in METRIC_KEYS:
            assert key in result, f"Missing metric key: {key}"
        assert len(result) >= len(METRIC_KEYS)

    def test_cached_property_only_calls_llm_once(self):
        """@cached_property should ensure the LLM is called exactly once."""
        provider = FakeLLMProvider()
        explainer = MetricExplainer(provider=provider)

        # Access the property multiple times
        _ = explainer.explanations
        _ = explainer.explanations
        _ = explainer.explanations

        assert provider.call_count == 1, (
            f"LLM was called {provider.call_count} times, expected exactly 1"
        )

    def test_fallback_on_llm_failure(self):
        """When LLM fails, should gracefully return fallback explanations."""
        provider = FakeLLMProvider(should_fail=True)
        explainer = MetricExplainer(provider=provider)

        result = explainer.explanations

        # Should return fallback without raising
        assert result == FALLBACK_EXPLANATIONS
        for key in METRIC_KEYS:
            assert key in result

    def test_fallback_explanations_cover_all_metrics(self):
        """Hardcoded fallback dict must cover every metric in METRIC_KEYS."""
        for key in METRIC_KEYS:
            assert key in FALLBACK_EXPLANATIONS, (
                f"Fallback missing explanation for: {key}"
            )
            assert len(FALLBACK_EXPLANATIONS[key]) > 20, (
                f"Fallback for {key} is suspiciously short"
            )

    def test_handles_json_with_markdown_fences(self):
        """LLM sometimes wraps JSON in ```json ... ``` — parser should handle it."""
        wrapped = "```json\n" + json.dumps({k: f"Test {k}" for k in METRIC_KEYS}) + "\n```"
        provider = FakeLLMProvider(response=wrapped)
        explainer = MetricExplainer(provider=provider)

        result = explainer.explanations
        for key in METRIC_KEYS:
            assert key in result

    def test_ignores_unknown_keys_from_llm(self):
        """LLM might return extra keys — they should be filtered out."""
        data = {k: f"Explanation for {k}" for k in METRIC_KEYS}
        data["unknown_metric"] = "Should be ignored"
        data["another_fake"] = "Also ignored"
        provider = FakeLLMProvider(response=json.dumps(data))
        explainer = MetricExplainer(provider=provider)

        result = explainer.explanations
        assert "unknown_metric" not in result
        assert "another_fake" not in result

    def test_merges_partial_llm_response_with_fallback(self):
        """If LLM returns only some keys, fallback fills the rest."""
        partial = {"pe_ratio": "Custom PE explanation", "roe": "Custom ROE explanation"}
        provider = FakeLLMProvider(response=json.dumps(partial))
        explainer = MetricExplainer(provider=provider)

        result = explainer.explanations

        # Custom ones should override fallback
        assert result["pe_ratio"] == "Custom PE explanation"
        assert result["roe"] == "Custom ROE explanation"
        # Others should come from fallback
        assert result["pb_ratio"] == FALLBACK_EXPLANATIONS["pb_ratio"]
        assert result["altman_z_score"] == FALLBACK_EXPLANATIONS["altman_z_score"]

    def test_handles_invalid_json_from_llm(self):
        """Malformed JSON should trigger fallback, not crash."""
        provider = FakeLLMProvider(response="This is not JSON at all!")
        explainer = MetricExplainer(provider=provider)

        result = explainer.explanations
        assert result == FALLBACK_EXPLANATIONS

    def test_dependency_injection_with_custom_provider(self):
        """MetricExplainer should accept any LLMProvider implementation."""
        custom = MagicMock(spec=LLMProvider)
        custom.generate.return_value = json.dumps(
            {k: f"Mock {k}" for k in METRIC_KEYS}
        )

        explainer = MetricExplainer(provider=custom)
        result = explainer.explanations

        custom.generate.assert_called_once()
        assert result["pe_ratio"] == "Mock pe_ratio"


# ═══════════════════════════════════════════════════════════
#  FundamentalAgent Integration Tests
# ═══════════════════════════════════════════════════════════


class TestFundamentalAgentIntegration:
    """Verify MetricExplainer is properly wired into FundamentalAgent."""

    def _make_agent_with_fake_provider(self):
        """Create a FundamentalAgent with a fake LLM provider."""
        from app.agents.fundamental_agent import FundamentalAgent

        agent = FundamentalAgent()
        # Replace the explainer's provider with our fake
        fake_provider = FakeLLMProvider()
        agent._explainer = MetricExplainer(provider=fake_provider)
        return agent, fake_provider

    def test_extract_metrics_includes_explanations(self):
        """_extract_metrics dict should contain 'metric_explanations' key."""
        agent, _ = self._make_agent_with_fake_provider()

        # Minimal yfinance-style info dict
        mock_info = {
            "trailingPE": 25.5,
            "priceToBook": 3.2,
            "returnOnEquity": 0.18,
            "profitMargins": 0.12,
            "currentRatio": 1.8,
        }

        result = agent._extract_metrics(mock_info)

        assert "metric_explanations" in result
        assert isinstance(result["metric_explanations"], dict)
        for key in METRIC_KEYS:
            assert key in result["metric_explanations"]

    def test_explanations_are_same_object_across_calls(self):
        """Cached property means same dict object for all stocks."""
        agent, provider = self._make_agent_with_fake_provider()

        result1 = agent._extract_metrics({"trailingPE": 20})
        result2 = agent._extract_metrics({"trailingPE": 30})

        # Same cached object
        assert result1["metric_explanations"] is result2["metric_explanations"]
        # LLM called only once
        assert provider.call_count == 1

    def test_numeric_metrics_still_present(self):
        """Adding explanations should not break existing numeric metrics."""
        agent, _ = self._make_agent_with_fake_provider()

        mock_info = {
            "trailingPE": 25.5,
            "priceToBook": 3.2,
            "returnOnEquity": 0.18,
            "profitMargins": 0.12,
            "currentRatio": 1.8,
            "debtToEquity": 45.0,
        }

        result = agent._extract_metrics(mock_info)

        assert result["pe_ratio"] == 25.5
        assert result["pb_ratio"] == 3.2
        assert result["roe"] == 0.18
        assert result["net_margin"] == 0.12
        assert result["current_ratio"] == 1.8
