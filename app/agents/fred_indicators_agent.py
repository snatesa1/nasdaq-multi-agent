"""
FRED Indicators Agent — Tier 1: Leading & Lagging Economic Indicators.

Fetches FRED data series (yield curve, GDP, CPI, unemployment, etc.)
and uses Gemini Flash to interpret trends into a macro score + narrative.
"""

import logging
from typing import Dict, List, Optional

from ..config import settings
from .base_agent import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


# ── FRED Series Definitions ─────────────────────────────
LEADING_INDICATORS = {
    "T5YIFR": {
        "name": "5-Year Forward Inflation Expectation",
        "why": "Fed policy direction — rising = hawkish, falling = dovish",
    },
    "T10Y2Y": {
        "name": "10Y-2Y Treasury Spread (Yield Curve)",
        "why": "Recession signal — inverted (negative) = danger",
    },
    "PERMIT": {
        "name": "Building Permits",
        "why": "Housing/construction outlook — leading GDP indicator",
    },
    "UMCSENT": {
        "name": "Consumer Sentiment (UMich)",
        "why": "Consumer spending outlook — drives 70% of GDP",
    },
    "INDPRO": {
        "name": "Industrial Production Index",
        "why": "Manufacturing output — rising = expansion, falling = contraction",
    },
    "USALOLITONOSTSAM": {
        "name": "OECD Composite Leading Indicator (CLI)",
        "why": "Broad recession predictor — below 100 = contraction risk",
    },
}

LAGGING_INDICATORS = {
    "GDPCA": {
        "name": "Real GDP (Annual)",
        "why": "Economic health baseline",
    },
    "UNRATE": {
        "name": "Unemployment Rate",
        "why": "Labor market health — rising = weakening economy",
    },
    "CPIAUCSL": {
        "name": "CPI (All Urban Consumers)",
        "why": "Inflation reality vs Fed target (2%)",
    },
    "CP": {
        "name": "Corporate Profits",
        "why": "Earnings power of the economy — drives equity valuations",
    },
    "FEDFUNDS": {
        "name": "Federal Funds Rate",
        "why": "Cost of capital — higher = tighter conditions",
    },
}


class FredIndicatorsAgent(BaseAgent):
    """
    Fetches FRED leading and lagging economic indicators.
    Computes a macro score and generates a narrative interpretation.
    """

    def __init__(self):
        self._fred_client = None

    @property
    def name(self) -> str:
        return "FredIndicatorsAgent"

    def _get_fred(self):
        """Lazy-load fredapi client."""
        if self._fred_client is None:
            from fredapi import Fred
            self._fred_client = Fred(api_key=settings.FRED_API_KEY)
        return self._fred_client

    async def analyze(self, lookback_months: int = 12, **kwargs) -> AgentResult:
        """
        Fetch all leading/lagging indicators, score them, build narrative.

        Args:
            lookback_months: How many months of history to fetch (default 12).
        """
        self._log_start(f"({lookback_months}-month lookback)")
        fred = self._get_fred()

        leading_data = self._fetch_indicators(fred, LEADING_INDICATORS, lookback_months)
        lagging_data = self._fetch_indicators(fred, LAGGING_INDICATORS, lookback_months)

        leading_score = self._score_leading(leading_data)
        lagging_score = self._score_lagging(lagging_data)

        # Composite: leading indicators matter more for forward-looking analysis
        composite = round(leading_score * 0.65 + lagging_score * 0.35, 3)

        result = AgentResult(
            agent_name=self.name,
            score=composite,
            confidence=0.75,
            rationale=self._build_narrative(leading_data, lagging_data, leading_score, lagging_score),
            data={
                "leading_score": leading_score,
                "lagging_score": lagging_score,
                "leading_indicators": leading_data,
                "lagging_indicators": lagging_data,
            },
        )
        self._log_done(result)
        return result

    # ── Fetching ─────────────────────────────────────────

    def _fetch_indicators(
        self, fred, definitions: Dict, lookback_months: int
    ) -> Dict[str, Dict]:
        """Fetch each FRED series and compute latest value + trend."""
        results = {}
        for series_id, meta in definitions.items():
            try:
                data = fred.get_series(series_id)
                if data is not None and len(data) > 0:
                    # Get recent data
                    recent = data.tail(lookback_months * 2)  # Rough: ~2 data points/month
                    latest = float(recent.iloc[-1])
                    prev = float(recent.iloc[-2]) if len(recent) > 1 else latest
                    first = float(recent.iloc[0]) if len(recent) > 0 else latest

                    trend = "rising" if latest > prev else "falling" if latest < prev else "flat"
                    pct_change = round(((latest - first) / abs(first)) * 100, 2) if first != 0 else 0

                    results[series_id] = {
                        "name": meta["name"],
                        "why": meta["why"],
                        "latest": round(latest, 4),
                        "previous": round(prev, 4),
                        "trend": trend,
                        "pct_change_period": pct_change,
                    }
                    logger.info(f"  📈 {meta['name']}: {latest:.4f} ({trend})")
                else:
                    logger.warning(f"  ⚠️ No data for {series_id} ({meta['name']})")
            except Exception as e:
                logger.error(f"  ❌ Failed to fetch {series_id}: {e}")

        return results

    # ── Scoring ──────────────────────────────────────────

    def _score_leading(self, data: Dict[str, Dict]) -> float:
        """
        Score leading indicators 0→1 (higher = more bullish).
        Each indicator has its own scoring logic.
        """
        scores = []

        # Yield Curve: positive = good, inverted = bad
        yc = data.get("T10Y2Y", {})
        if yc:
            val = yc["latest"]
            if val > 0.5:
                scores.append(0.8)
            elif val > 0:
                scores.append(0.6)
            elif val > -0.5:
                scores.append(0.3)
            else:
                scores.append(0.1)

        # Industrial Production: rising trend = expansion
        indpro = data.get("INDPRO", {})
        if indpro:
            pct = indpro.get("pct_change_period", 0)
            if pct > 2:
                scores.append(0.8)
            elif pct > 0:
                scores.append(0.6)
            elif pct > -2:
                scores.append(0.4)
            else:
                scores.append(0.2)

        # Consumer Sentiment: higher = better
        cs = data.get("UMCSENT", {})
        if cs:
            val = cs["latest"]
            scores.append(min(1.0, max(0.0, (val - 50) / 50)))  # Map 50-100 → 0-1

        # Inflation expectations: moderate (2-3%) = good, extremes = bad
        ie = data.get("T5YIFR", {})
        if ie:
            val = ie["latest"]
            if 1.5 <= val <= 3.0:
                scores.append(0.8)
            elif 1.0 <= val <= 3.5:
                scores.append(0.5)
            else:
                scores.append(0.2)

        # Building Permits: trend matters more than absolute
        bp = data.get("PERMIT", {})
        if bp:
            scores.append(0.7 if bp["trend"] == "rising" else 0.4 if bp["trend"] == "flat" else 0.2)

        # CLI: above 100 = expansion
        cli = data.get("USALOLITONOSTSAM", {})
        if cli:
            val = cli["latest"]
            scores.append(min(1.0, max(0.0, (val - 97) / 6)))  # Map 97-103 → 0-1

        return round(sum(scores) / max(len(scores), 1), 3)

    def _score_lagging(self, data: Dict[str, Dict]) -> float:
        """Score lagging indicators 0→1."""
        scores = []

        # Unemployment: lower = better
        ur = data.get("UNRATE", {})
        if ur:
            val = ur["latest"]
            scores.append(min(1.0, max(0.0, (10 - val) / 7)))  # Map 3-10 → 1-0

        # Fed Funds: moderate = ok, too high or too low = caution
        ff = data.get("FEDFUNDS", {})
        if ff:
            val = ff["latest"]
            if 2.0 <= val <= 4.0:
                scores.append(0.7)
            elif val < 1.0 or val > 5.5:
                scores.append(0.3)
            else:
                scores.append(0.5)

        # GDP: positive growth = good
        gdp = data.get("GDPCA", {})
        if gdp:
            scores.append(0.7 if gdp["trend"] == "rising" else 0.4 if gdp["trend"] == "flat" else 0.2)

        # Corporate Profits: rising = bullish
        cp = data.get("CP", {})
        if cp:
            scores.append(0.8 if cp["trend"] == "rising" else 0.4 if cp["trend"] == "flat" else 0.2)

        # CPI: below 3% = manageable, above = concern
        cpi = data.get("CPIAUCSL", {})
        if cpi and cpi.get("pct_change_period") is not None:
            yoy = abs(cpi["pct_change_period"])
            if yoy < 3:
                scores.append(0.8)
            elif yoy < 5:
                scores.append(0.5)
            else:
                scores.append(0.2)

        return round(sum(scores) / max(len(scores), 1), 3)

    # ── Narrative ────────────────────────────────────────

    def _build_narrative(
        self,
        leading: Dict[str, Dict],
        lagging: Dict[str, Dict],
        l_score: float,
        lag_score: float,
    ) -> str:
        """Build human-readable narrative from indicator data."""
        lines = []

        # Overall assessment
        if l_score > 0.65:
            lines.append("📈 Leading indicators suggest EXPANSION — favorable macro environment.")
        elif l_score > 0.45:
            lines.append("➡️ Leading indicators are MIXED — proceed with caution.")
        else:
            lines.append("📉 Leading indicators signal CONTRACTION RISK — defensive posture advised.")

        # Key highlights
        yc = leading.get("T10Y2Y", {})
        if yc:
            val = yc.get("latest", 0)
            if val < 0:
                lines.append(f"  ⚠️ Yield curve INVERTED ({val:.2f}%) — historical recession signal.")
            else:
                lines.append(f"  ✅ Yield curve positive ({val:.2f}%) — no recession signal.")

        indpro = leading.get("INDPRO", {})
        if indpro:
            val = indpro.get("latest", 0)
            trend = indpro.get("trend", "flat")
            lines.append(f"  {'✅' if trend == 'rising' else '⚠️'} Industrial Production: {val:.1f} ({trend})")

        ur = lagging.get("UNRATE", {})
        if ur:
            lines.append(f"  📊 Unemployment: {ur.get('latest', 0):.1f}% ({ur.get('trend', 'N/A')})")

        ff = lagging.get("FEDFUNDS", {})
        if ff:
            lines.append(f"  🏦 Fed Funds Rate: {ff.get('latest', 0):.2f}% ({ff.get('trend', 'N/A')})")

        lines.append(f"\n  Leading Score: {l_score:.2f} | Lagging Score: {lag_score:.2f}")
        return "\n".join(lines)
