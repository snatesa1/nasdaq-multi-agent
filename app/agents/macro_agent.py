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

from ..data_client import FMPClient, YFinanceClient, NasdaqScreenerClient, AlpacaOHLCVClient
from .base_agent import AgentResult, BaseAgent
from .metric_explainer import VertexGeminiProvider

logger = logging.getLogger(__name__)

# ── Sector ETFs for sliding window comparison ────────────
SECTOR_ETFS = {
    # Nasdaq Screener Names
    "Health Care": "XLV",
    "Finance": "XLF",
    "Basic Materials": "XLB",
    "Telecommunications": "XLC",
    "Consumer Discr": "XLY",
    "Consumer Stapl": "XLP",
    # FMP / Standard Names
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

# ── Top stocks per sector will be loaded dynamically from NasdaqScreenerClient ─

# Fallback comparison years — used when Gemini is unavailable (prioritizing recent analog/latest years)
DEFAULT_COMPARISON_YEARS = [2022, 2023, 2024, 2025, datetime.now().year]


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
that had the most similar macro environment. Prioritize the most recent years (like 2023, 2024, 2025) if they are a strong match, as comparing to the latest cycles is highly valuable. Consider factors like:
- Technology revolutions (dot-com boom 1999, AI revolution 2023-2024)
- Credit/banking crises (2007-2008 GFC, 2023 SVB)
- Geopolitical conflicts & wars (2001, 2022 Russia-Ukraine)
- Inflation / rate hike cycles (1994, 2022)
- Private credit bubbles or liquidity crunches
- Pandemic recovery (2020-2021)

Return ONLY a JSON array of integers, e.g. [2023, 2024, 2025].
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
        self.screener = NasdaqScreenerClient()
        self.alpaca = AlpacaOHLCVClient()
        self.regime_analyzer = MacroRegimeAnalyzer()

    @property
    def name(self) -> str:
        return "MacroAgent"

    async def analyze(self, top_n: int = 11, window_days: int = 35, **kwargs) -> AgentResult:
        """
        Full macro analysis using NASDAQ Screener CSV pivot by Sector and Industry.

        Args:
            top_n: Number of top sectors to select (default 11).
            window_days: Sliding window size in days (default 35).
        """
        self._log_start(f"(top {top_n} sectors, {window_days}-day window)")

        import pandas as pd

        # ── Step 1: Load and pivot Nasdaq Screener CSV by Sector and Industry ──
        df = self.screener.load_data()
        if df.empty:
            logger.error("❌ Nasdaq screener CSV is empty — cannot execute pivot analysis!")
            scored_sectors = {}
            top_sectors = []
            stock_universe = []
            sliding_windows = {}
            comparison_years = kwargs.get("comparison_years", DEFAULT_COMPARISON_YEARS)
        else:
            df_clean = df.dropna(subset=["sector", "industry", "pctchange"]).copy()
            df_clean["pctchange"] = pd.to_numeric(df_clean["pctchange"], errors="coerce")
            df_clean = df_clean.dropna(subset=["pctchange"])

            # Pivot/group by Sector & Industry, getting the average % change
            pivot = df_clean.groupby(["sector", "industry"])["pctchange"].mean().reset_index()
            pivot = pivot.sort_values(by="pctchange", ascending=False)
            logger.info(f"📊 Top pivoted sector-industry segments:\n{pivot.head(10).to_string(index=False)}")

            # Calculate sector averages for UI/Slack rendering
            sector_averages = df_clean.groupby("sector")["pctchange"].mean().to_dict()
            max_change = max(abs(v) for v in sector_averages.values()) if sector_averages else 1
            if max_change == 0:
                max_change = 1
            scored_sectors = {
                k: round((v / max_change + 1) / 2, 3) for k, v in sector_averages.items()
            }

            # ── Step 2: Select top N macro groups and unique top sectors ─────────────────
            # Typically select top 3 to 5 groups to build the stock universe
            num_groups = min(max(3, top_n // 2), 5)
            top_groups = pivot.head(num_groups).to_dict("records")
            logger.info(f"🏆 Top selected macro groups: {top_groups}")

            top_sectors = list(dict.fromkeys([g["sector"] for g in top_groups]))
            logger.info(f"🏆 Unique top sectors: {top_sectors}")

            # ── Step 3: Spec-configured comparison years (no dynamic/local overrides) ────
            comparison_years = kwargs.get("comparison_years")
            if not comparison_years:
                try:
                    import yaml
                    import os
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    spec_path = os.path.join(base_dir, "config", "spec.yaml")
                    with open(spec_path, "r") as f:
                        spec = yaml.safe_load(f)
                    comparison_years = spec.get("pipeline", {}).get("tier_1", {}).get("macro_agent", {}).get("params", {}).get("comparison_years", [])
                    logger.info(f"📋 Loaded comparison years from spec: {comparison_years}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load comparison years from spec: {e}")
                    comparison_years = [1995, 2000, 2008, 2015, 2022, 2023, 2024, 2025, 2026]
            else:
                logger.info(f"📋 Using spec-configured comparison years: {comparison_years}")

            # ── Step 4: Sliding window comparison ────────────
            sliding_windows = {}
            for sector in top_sectors:
                df_sec = df_clean[df_clean["sector"] == sector]
                if not df_sec.empty:
                    df_sec = df_sec.sort_values(by="pctchange", ascending=False)
                    symbols = df_sec["symbol"].tolist()[:100]
                    sliding_windows[sector] = self.alpaca.get_sliding_window(
                        symbol_or_symbols=symbols,
                        window_days=window_days,
                        years=comparison_years,
                    )

            # ── Step 5: Build stock universe — top stocks per high-performing group ────
            fallback_universe_size = kwargs.get("fallback_universe_size", 10)
            seen = set()
            stock_universe = []
            
            stocks_per_group = max(2, fallback_universe_size // len(top_groups))
            for group in top_groups:
                sec = group["sector"]
                ind = group["industry"]
                
                # Fetch matching stocks
                group_stocks = df_clean[
                    (df_clean["sector"] == sec) & (df_clean["industry"] == ind)
                ].copy()
                
                # Sort by marketCap descending to get industry leaders
                if "marketCap" in group_stocks.columns:
                    group_stocks = group_stocks.sort_values(by="marketCap", ascending=False)
                elif "volume" in group_stocks.columns:
                    group_stocks = group_stocks.sort_values(by="volume", ascending=False)
                
                symbols = group_stocks["symbol"].tolist()
                selected_count = 0
                for sym in symbols:
                    if sym not in seen:
                        seen.add(sym)
                        stock_universe.append(sym)
                        selected_count += 1
                        if selected_count >= stocks_per_group:
                            break

            # Guarantee default leaders if empty
            if not stock_universe:
                logger.warning("⚠️ Stock universe empty — using default NASDAQ-100 leaders")
                stock_universe = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX"]

        # Sort sectors by score descending for formatting compatibility
        sorted_sectors = sorted(scored_sectors.items(), key=lambda x: x[1], reverse=True)

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
                "sector_pe": {},  # Bypassing FMP call cleanly
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
