"""
Metric Explainer — LLM-powered layman explanations for financial ratios.

Uses a layered abstraction:
  1. LLMProvider (abstract) → VertexGeminiProvider (concrete)
  2. MetricExplainer consumes any LLMProvider
  3. @cached_property ensures one LLM call per process lifetime

Falls back to hardcoded explanations if LLM is unavailable.
"""

import json
import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Dict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  Layer 1: LLM Provider Abstraction
# ═══════════════════════════════════════════════════════════


class LLMProvider(ABC):
    """Abstract interface for any LLM backend."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Send a prompt and return the raw text response."""
        ...


class VertexGeminiProvider(LLMProvider):
    """Vertex AI Gemini provider — reads model from Settings.VERTEX_MODEL."""

    def __init__(self, model_name: str | None = None):
        if model_name:
            self._model_name = model_name
        else:
            from ..config import settings
            self._model_name = settings.VERTEX_MODEL

    def generate(self, prompt: str) -> str:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        # vertexai.init() picks up PROJECT_ID from env / metadata server
        vertexai.init()
        model = GenerativeModel(self._model_name)
        response = model.generate_content(prompt)
        return response.text


# ═══════════════════════════════════════════════════════════
#  Layer 2: Metric Definitions (data layer)
# ═══════════════════════════════════════════════════════════

# Canonical list of metric keys — single source of truth
METRIC_KEYS = [
    "pe_ratio",
    "pb_ratio",
    "ps_ratio",
    "ev_ebitda",
    "fcf_yield",
    "roe",
    "roa",
    "net_margin",
    "gross_margin",
    "operating_margin",
    "current_ratio",
    "debt_to_equity",
    "revenue_growth",
    "earnings_growth",
    "piotroski_score",
    "altman_z_score",
]

# Pre-written fallback — used when LLM is unavailable
FALLBACK_EXPLANATIONS: Dict[str, str] = {
    "pe_ratio": (
        "Price-to-Earnings (P/E): How many years of profits you're paying for. "
        "Like buying a coffee shop for $100K that earns $10K/year → P/E = 10. "
        "Lower = cheaper, but a high P/E can mean strong growth expectations."
    ),
    "pb_ratio": (
        "Price-to-Book (P/B): Price compared to what the company owns (net assets). "
        "If a house is worth $500K in materials but sells for $1M → P/B = 2. "
        "Below 1 could be a bargain (or a warning)."
    ),
    "ps_ratio": (
        "Price-to-Sales (P/S): Market value relative to total revenue. "
        "Think paying $200K for a lemonade stand that makes $100K in sales → P/S = 2. "
        "Useful for companies that aren't profitable yet."
    ),
    "ev_ebitda": (
        "Enterprise Value / EBITDA: Total company cost ÷ operating profits (before accounting tricks). "
        "Like buying a pizza franchise including its debt. "
        "Below 10 is generally attractive; above 20 is pricey."
    ),
    "fcf_yield": (
        "Free Cash Flow Yield: Actual cash the company generates relative to its price. "
        "Like a rental property earning $6K/year on a $100K investment → 6% yield. "
        "Higher = more cash returns for your money."
    ),
    "roe": (
        "Return on Equity (ROE): Profit generated per dollar shareholders invested. "
        "Like putting $100 into a business and getting $20 back in profit → 20% ROE. "
        "Above 15% is generally considered excellent."
    ),
    "roa": (
        "Return on Assets (ROA): Profit generated per dollar of total assets. "
        "Shows how efficiently a company uses everything it owns to make money. "
        "Higher is better; 5%+ is solid for most industries."
    ),
    "net_margin": (
        "Net Profit Margin: How much of each dollar in sales becomes actual profit. "
        "If a bakery sells $100 of cakes and keeps $15 after all costs → 15% margin. "
        "Higher = more efficient at turning revenue into profit."
    ),
    "gross_margin": (
        "Gross Margin: Revenue minus the direct cost of products. "
        "Like selling a $10 shirt that cost $3 to make → 70% gross margin. "
        "Shows pricing power before overhead expenses."
    ),
    "operating_margin": (
        "Operating Margin: Profit after all operating costs (rent, salaries, etc.) but before taxes. "
        "It reveals whether the day-to-day business is truly profitable. "
        "15%+ is typically strong."
    ),
    "current_ratio": (
        "Current Ratio: Can the company pay its short-term bills? "
        "Like having $2000 in your bank vs $1000 in bills due this month → ratio = 2. "
        "Above 1.5 is comfortable; below 1 is a red flag."
    ),
    "debt_to_equity": (
        "Debt-to-Equity: How much borrowed money vs. owner money funds the business. "
        "Like owning a house worth $500K with a $250K mortgage → D/E = 50%. "
        "Lower is safer; above 200% can be risky."
    ),
    "revenue_growth": (
        "Revenue Growth: Year-over-year increase in total sales. "
        "Like your lemonade stand going from $1000 to $1200 in sales → 20% growth. "
        "Positive growth means the business is expanding."
    ),
    "earnings_growth": (
        "Earnings Growth: Year-over-year increase in net profit. "
        "Even more important than revenue growth — shows the profit engine is scaling. "
        "Consistent double-digit growth is a strong signal."
    ),
    "piotroski_score": (
        "Piotroski F-Score (0–9): A financial health checklist — 9 pass/fail tests. "
        "Checks profitability, leverage, and efficiency improvement. "
        "8–9 = great financial health; below 3 = potential distress."
    ),
    "altman_z_score": (
        "Altman Z-Score: Bankruptcy risk predictor. "
        "Combines profitability, leverage, liquidity, and efficiency into one number. "
        "Above 3 = safe zone; 1.8–3 = grey zone; below 1.8 = danger zone."
    ),
}


# ═══════════════════════════════════════════════════════════
#  Layer 3: MetricExplainer — orchestration + caching
# ═══════════════════════════════════════════════════════════


class MetricExplainer:
    """
    Generates and caches layman explanations for fundamental financial metrics.

    Architecture:
        - Accepts any LLMProvider (dependency injection)
        - @cached_property ensures ONE LLM call per instance lifetime
        - Falls back to hardcoded explanations on any failure
    """

    def __init__(self, provider: LLMProvider | None = None):
        """
        Args:
            provider: LLM backend. Defaults to VertexGeminiProvider if None.
        """
        self._provider = provider or VertexGeminiProvider()

    @cached_property
    def explanations(self) -> Dict[str, str]:
        """
        Layman explanations for all metrics — cached after first call.

        Returns:
            Dict mapping metric_key → plain-English explanation string.
        """
        try:
            return self._fetch_from_llm()
        except Exception as e:
            logger.warning(f"⚠️ LLM explanation generation failed: {e}. Using fallback.")
            return dict(FALLBACK_EXPLANATIONS)

    def _fetch_from_llm(self) -> Dict[str, str]:
        """Call the LLM provider once to generate all metric explanations."""
        prompt = self._build_prompt()
        raw = self._provider.generate(prompt)
        parsed = self._parse_response(raw)

        # Merge with fallback to guarantee all 16 keys are present
        result = dict(FALLBACK_EXPLANATIONS)
        result.update(parsed)
        return result

    @staticmethod
    def _build_prompt() -> str:
        """Build the single LLM prompt for all metrics."""
        keys_str = ", ".join(METRIC_KEYS)
        return f"""You are a financial education expert. Explain each of these 
financial metrics in plain, everyday English that a non-finance person can understand.

For EACH metric, provide:
1. What it measures (one sentence)
2. A real-world analogy or example (one sentence)
3. What's considered good vs bad (one sentence)

Metrics: {keys_str}

IMPORTANT: Return your answer as a valid JSON object where each key is the metric 
name exactly as given, and the value is a single string combining all three points.
Example format:
{{"pe_ratio": "Your explanation here...", "pb_ratio": "Your explanation here..."}}

Return ONLY the JSON object, no markdown, no code fences, no extra text."""

    @staticmethod
    def _parse_response(raw: str) -> Dict[str, str]:
        """Parse LLM response into a metric→explanation dict."""
        # Strip common LLM artifacts (markdown fences, whitespace)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrapper
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        parsed = json.loads(cleaned)

        # Validate: only keep known metric keys with string values
        return {
            k: str(v)
            for k, v in parsed.items()
            if k in METRIC_KEYS and isinstance(v, str)
        }
