"""
Macro Agent — Tier 1: Top-Down Sector/Industry Screening.

Uses FMP sector performance + yfinance sliding window comparison
across dynamically-selected analog years (identified by Gemini).
Identifies the hottest industries and selects a stock universe.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..data_client import FMPClient, YFinanceClient
from .base_agent import AgentResult, BaseAgent
from .metric_explainer import VertexGeminiProvider

logger = logging.getLogger(__name__)

# ── Sector ETFs for sliding window comparison ────────────
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}

# ── Top stocks per sector (NASDAQ-focused) ───────────────
SECTOR_STOCKS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "AMD", "ADBE", "CRM", "INTC"],
    "Healthcare": ["AMGN", "GILD", "VRTX", "REGN", "ISRG", "ILMN", "MRNA", "BIIB"],
    "Consumer Discretionary": ["AMZN", "TSLA", "COST", "SBUX", "LULU", "BKNG", "ROST", "ORLY"],
    "Communication Services": ["GOOGL", "META", "NFLX", "CMCSA", "TMUS", "CHTR"],
    "Financials": ["JPM", "V", "MA", "GS", "BLK", "SCHW", "AXP", "SPGI"],
    "Financial Services": ["JPM", "V", "MA", "GS", "BLK", "SCHW", "AXP", "SPGI"],
    "Industrials": ["HON", "UNP", "UPS", "RTX", "DE", "BA", "CAT", "GE"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO"],
    "Consumer Staples": ["PEP", "KO", "PG", "MDLZ", "MO", "CL", "KHC", "GIS"],
    "Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "VMC"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL"],
    "Real Estate": ["PLD", "AMT", "CCI", "EQIX", "SPG", "PSA", "O", "DLR"],
}

# Fallback comparison years — used when Gemini is unavailable
DEFAULT_COMPARISON_YEARS = [1999, 2008, 2022, datetime.now().year]


# ══════════════════════════════════════════════════════════
#  Gemini-Powered Macro Regime Analyzer
# ══════════════════════════════════════════════════════════

class MacroRegimeAnalyzer:
    """
    Fetches the latest macro headlines from FMP, sends them to Gemini,
    and gets back 3-4 historical analog years that match the current
    macro regime (e.g. war, AI bubble, credit crisis).
    """

    def __init__(self):
        self.fmp = FMPClient()
        self.llm = VertexGeminiProvider()

    def get_dynamic_years(self) -> List[int]:
        """Return dynamically-selected analog comparison years."""
        try:
            headlines = self._fetch_macro_headlines()
            if not headlines:
                logger.warning("⚠️ No headlines fetched — using default years")
                return DEFAULT_COMPARISON_YEARS

            years = self._ask_gemini_for_analogs(headlines)
            if years:
                # Always include current year
                current_year = datetime.now().year
                if current_year not in years:
                    years.append(current_year)
                logger.info(f"🧠 Gemini selected analog years: {years}")
                return sorted(years)

        except Exception as e:
            logger.error(f"❌ MacroRegimeAnalyzer failed: {e}")

        return DEFAULT_COMPARISON_YEARS

    def _fetch_macro_headlines(self) -> List[str]:
        """Fetch top 5 macro headlines from FMP general news."""
        news = self.fmp.get_general_news(limit=10)
        headlines = []
        for article in (news or [])[:5]:
            title = article.get("title", "")
            if title:
                headlines.append(title)
        logger.info(f"📰 Fetched {len(headlines)} macro headlines")
        return headlines

    def _ask_gemini_for_analogs(self, headlines: List[str]) -> List[int]:
        """Ask Gemini to identify historical analog years from headlines."""
        headlines_text = "\n".join(f"- {h}" for h in headlines)
        current_year = datetime.now().year

        prompt = f"""You are a macro-economist and financial historian.

Here are today's top macroeconomic headlines:
{headlines_text}

Based on these headlines, identify 3-4 historical years (between 1990 and {current_year - 1})
that had the most similar macro environment. Consider factors like:
- Technology revolutions (dot-com boom 1999, AI revolution 2023-2024)
- Credit/banking crises (2007-2008 GFC, 2023 SVB)
- Geopolitical conflicts & wars (2001, 2022 Russia-Ukraine)
- Inflation / rate hike cycles (1994, 2022)
- Private credit bubbles or liquidity crunches
- Pandemic recovery (2020-2021)

Return ONLY a JSON array of integers, e.g. [1999, 2008, 2022].
No explanation, no markdown, just the JSON array."""

        raw = self.llm.generate(prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )

        years = json.loads(cleaned)
        # Validate: must be list of ints in reasonable range
        valid = [
            int(y) for y in years
            if isinstance(y, (int, float)) and 1990 <= int(y) <= current_year
        ]
        return valid[:4]  # Cap at 4 analog years


class MacroAgent(BaseAgent):
    """
    Top-down macro agent that:
    1. Fetches FMP sector performance snapshots
    2. Scores sectors by momentum (current + historical comparison)
    3. Runs sliding window comparison across crisis years
    4. Selects top 2-3 industries → outputs stock universe
    """

    def __init__(self):
        self.fmp = FMPClient()
        self.yfinance = YFinanceClient()
        self.regime_analyzer = MacroRegimeAnalyzer()

    @property
    def name(self) -> str:
        return "MacroAgent"

    async def analyze(self, top_n: int = 11, window_days: int = 35, **kwargs) -> AgentResult:
        """
        Full macro analysis.

        Args:
            top_n: Number of top sectors to select (default 3).
            window_days: Sliding window size in days (default 30).
        """
        self._log_start(f"(top {top_n} sectors, {window_days}-day window)")

        # ── Step 1: Current sector performance from FMP ──
        biz_date = self._last_business_day()
        logger.info(f"📅 Using business date: {biz_date}")
        sector_perf = self.fmp.get_sector_performance(biz_date)
        sector_pe = self.fmp.get_sector_pe(biz_date)

        scored_sectors = self._score_sectors(sector_perf, sector_pe)

        # ── Fallback: if FMP returned no data, use all known sectors ──
        if not scored_sectors:
            logger.warning(
                "⚠️ FMP returned no sector data — using fallback (all sectors at 0.5)"
            )
            scored_sectors = {sector: 0.5 for sector in SECTOR_STOCKS}

        logger.info(f"📊 Sector scores: {scored_sectors}")

        # ── Step 2: Select top N sectors ─────────────────
        sorted_sectors = sorted(scored_sectors.items(), key=lambda x: x[1], reverse=True)
        top_sectors = [s[0] for s in sorted_sectors[:top_n]]
        logger.info(f"🏆 Top sectors: {top_sectors}")

        # ── Step 3: Dynamic year selection via Gemini ────
        comparison_years = self.regime_analyzer.get_dynamic_years()
        logger.info(f"📅 Comparison years: {comparison_years}")

        # ── Step 4: Sliding window comparison ────────────
        sliding_windows = {}
        for sector in top_sectors:
            etf = SECTOR_ETFS.get(sector)
            if etf:
                windows = self.yfinance.get_sliding_window(
                    symbol=etf,
                    window_days=window_days,
                    years=comparison_years,
                )
                sliding_windows[sector] = self._summarize_windows(windows)

        # ── Step 5: Build stock universe — top 2 per sector ────
        seen = set()
        stock_universe = []
        for sector in top_sectors:
            stocks = SECTOR_STOCKS.get(sector, [])
            for s in stocks[:2]:  # Top 2 per sector → ~6-10 stocks total
                if s not in seen:
                    seen.add(s)
                    stock_universe.append(s)

        # ── Fallback: guarantee at least some stocks ─────
        if not stock_universe:
            logger.warning("⚠️ Stock universe still empty — using default NASDAQ-100 leaders")
            stock_universe = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX"]

        result = AgentResult(
            agent_name=self.name,
            score=self._compute_macro_score(scored_sectors, top_sectors),
            confidence=0.7,
            rationale=self._build_rationale(sorted_sectors, top_sectors, sliding_windows),
            data={
                "selected_sectors": top_sectors,
                "sector_scores": scored_sectors,
                "stock_universe": stock_universe,
                "sliding_window_comparison": sliding_windows,
                "comparison_years": comparison_years,
                "sector_pe": {item.get("sector", "?"): item.get("pe", 0) for item in (sector_pe or [])},
            },
        )
        self._log_done(result)
        return result

    # ── Internal helpers ─────────────────────────────────

    @staticmethod
    def _last_business_day() -> str:
        """Return the most recent business day as 'YYYY-MM-DD'.
        Sat → Friday, Sun → Friday. Weekdays return today."""
        today = datetime.now()
        weekday = today.weekday()  # Mon=0 ... Sun=6
        if weekday == 5:       # Saturday → Friday
            today -= timedelta(days=1)
        elif weekday == 6:     # Sunday → Friday
            today -= timedelta(days=2)
        return today.strftime("%Y-%m-%d")

    def _score_sectors(
        self, performance: List[Dict], pe_data: List[Dict]
    ) -> Dict[str, float]:
        """
        Score each sector 0→1 based on:
        - avgChangesPercentage (momentum, 60% weight)
        - P/E relative to historical average (valuation, 40% weight — lower = better value)
        """
        scores = {}
        if not performance:
            return scores

        # Normalize momentum
        changes = {
            p.get("sector", "?"): float(p.get("averageChangePercentage", 0) or 0)
            for p in performance
        }
        max_change = max(abs(v) for v in changes.values()) if changes else 1
        if max_change == 0:
            max_change = 1  # All sectors at 0% change (weekend/holiday)
        norm_changes = {k: (v / max_change + 1) / 2 for k, v in changes.items()}

        # P/E score — lower relative P/E is better
        pe_map = {}
        if pe_data:
            pes = {p.get("sector", "?"): float(p.get("pe", 0) or 0) for p in pe_data}
            max_pe = max(pes.values()) if pes else 1
            if max_pe == 0:
                max_pe = 1
            pe_map = {k: 1 - (v / max_pe) for k, v in pes.items()}  # Invert: lower PE → higher score

        for sector in norm_changes:
            momentum = norm_changes.get(sector, 0.5)
            valuation = pe_map.get(sector, 0.5)
            scores[sector] = round(momentum * 0.6 + valuation * 0.4, 3)

        return scores

    def _summarize_windows(self, windows: Dict[int, any]) -> Dict[str, any]:
        """Summarize sliding window data for a sector ETF."""
        summary = {}
        for year, df in windows.items():
            if df is not None and not df.empty and "indexed_close" in df.columns:
                start_val = df["indexed_close"].iloc[0]
                end_val = df["indexed_close"].iloc[-1]
                pct_return = round(end_val - start_val, 2)
                summary[str(year)] = {
                    "return_pct": pct_return,
                    "start_indexed": round(start_val, 2),
                    "end_indexed": round(end_val, 2),
                    "data_points": len(df),
                }
        return summary

    def _compute_macro_score(
        self, all_scores: Dict[str, float], top_sectors: List[str]
    ) -> float:
        """Average score of selected sectors as overall macro score."""
        if not top_sectors:
            return 0.5
        return round(
            sum(all_scores.get(s, 0.5) for s in top_sectors) / len(top_sectors), 3
        )

    def _build_rationale(
        self,
        sorted_sectors: List,
        top_sectors: List[str],
        sliding_windows: Dict,
    ) -> str:
        """Build human-readable macro rationale."""
        lines = [f"🏆 Top sectors: {', '.join(top_sectors)}"]

        for sector in top_sectors:
            sw = sliding_windows.get(sector, {})
            if sw:
                current_year = str(max(int(y) for y in sw.keys()))
                current_ret = sw.get(current_year, {}).get("return_pct", "N/A")
                lines.append(f"  • {sector}: current window return = {current_ret}%")

                # Compare with crisis years
                for year_str, data in sw.items():
                    if year_str != current_year:
                        ret = data.get("return_pct", "N/A")
                        lines.append(f"    ↳ {year_str} same window: {ret}%")

        return "\n".join(lines)
