"""
Fundamental Agent — Quality & Value scoring per stock.

Uses yfinance (free) instead of FMP paid endpoints for fundamental data.
yf.Ticker.info provides: PE, PB, ROE, margins, EV/EBITDA, FCF, etc.

Produces a 0→1 composite score based on:
  - Value (30%):  PE, PB, EV/EBITDA relative to sector medians
  - Quality (35%): ROE, Net Margin, FCF Yield
  - Safety (35%):  Current Ratio, Debt/Equity, Piotroski-style checks

Phase 2 agent — runs in parallel with Technical for each stock.
"""

import logging
from typing import Dict

import yfinance as yf

from .base_agent import BaseAgent, AgentResult
from .metric_explainer import MetricExplainer

logger = logging.getLogger(__name__)


class FundamentalAgent(BaseAgent):
    """Fundamental quality + value scoring agent using yfinance."""

    def __init__(self):
        self._explainer = MetricExplainer()

    @property
    def name(self) -> str:
        return "FundamentalAgent"

    async def analyze(self, symbol: str) -> AgentResult:
        """
        Analyze a single stock's fundamental quality and value.
        Returns score (0→1), confidence, and metrics dict.
        """
        logger.info(f"📊 FundamentalAgent: Analyzing {symbol}...")

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            if not info or info.get("quoteType") is None:
                logger.warning(f"⚠️ No yfinance info for {symbol}")
                return AgentResult(
                    agent_name="FundamentalAgent",
                    score=0.5,
                    confidence=0.2,
                    rationale=f"No fundamental data available for {symbol}",
                    data={"symbol": symbol, "metrics": {}},
                )

            # Extract key values
            extracted = self._extract_metrics(info)

            # Compute composite score
            score, sub_scores = self._compute_score(extracted)

            return AgentResult(
                agent_name="FundamentalAgent",
                score=round(score, 3),
                confidence=0.7,
                rationale=self._build_rationale(symbol, extracted, sub_scores),
                data={
                    "symbol": symbol,
                    "metrics": extracted,
                    "sub_scores": sub_scores,
                },
            )

        except Exception as e:
            logger.error(f"❌ FundamentalAgent failed for {symbol}: {e}")
            return AgentResult(
                agent_name="FundamentalAgent",
                score=0.5,
                confidence=0.2,
                rationale=f"Fundamental analysis failed: {e}",
                data={"symbol": symbol, "metrics": {}, "error": str(e)},
            )

    # ── Data Extraction ──────────────────────────────────

    def _extract_metrics(self, info: Dict) -> Dict:
        """Extract and normalize key fundamental metrics from yfinance info."""

        # Value ratios
        pe = self._safe_float(info.get("trailingPE") or info.get("forwardPE"))
        pb = self._safe_float(info.get("priceToBook"))
        ev_ebitda = self._safe_float(info.get("enterpriseToEbitda"))
        ps = self._safe_float(info.get("priceToSalesTrailing12Months"))

        # Quality ratios
        roe = self._safe_float(info.get("returnOnEquity"))        # Already 0-1 scale
        roa = self._safe_float(info.get("returnOnAssets"))
        net_margin = self._safe_float(info.get("profitMargins"))   # Already 0-1 scale
        gross_margin = self._safe_float(info.get("grossMargins"))
        operating_margin = self._safe_float(info.get("operatingMargins"))

        # FCF yield
        fcf = self._safe_float(info.get("freeCashflow"))
        market_cap = self._safe_float(info.get("marketCap"))
        fcf_yield = (fcf / market_cap) if market_cap > 0 else 0.0

        # Safety
        current_ratio = self._safe_float(info.get("currentRatio"))
        debt_to_equity = self._safe_float(info.get("debtToEquity"))  # In percentage (e.g. 150 = 1.5x)
        revenue_growth = self._safe_float(info.get("revenueGrowth"))
        earnings_growth = self._safe_float(info.get("earningsGrowth"))

        # Piotroski-style check (simplified from yfinance data)
        piotroski_score = self._estimate_piotroski(info)

        # Altman Z approximation (simplified)
        altman_z = self._estimate_altman_z(info)

        return {
            "pe_ratio": pe,
            "pb_ratio": pb,
            "ps_ratio": ps,
            "ev_ebitda": ev_ebitda,
            "fcf_yield": fcf_yield,
            "roe": roe,
            "roa": roa,
            "net_margin": net_margin,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "current_ratio": current_ratio,
            "debt_to_equity": debt_to_equity,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "piotroski_score": piotroski_score,
            "altman_z_score": altman_z,
            "metric_explanations": self._explainer.explanations,
        }

    def _estimate_piotroski(self, info: Dict) -> float:
        """Estimate Piotroski F-Score (0-9) from yfinance info fields."""
        score = 0

        # 1. Positive net income
        if self._safe_float(info.get("netIncomeToCommon")) > 0:
            score += 1
        # 2. Positive ROA
        if self._safe_float(info.get("returnOnAssets")) > 0:
            score += 1
        # 3. Positive operating cash flow
        if self._safe_float(info.get("operatingCashflow")) > 0:
            score += 1
        # 4. CFO > Net Income (quality of earnings)
        cfo = self._safe_float(info.get("operatingCashflow"))
        ni = self._safe_float(info.get("netIncomeToCommon"))
        if cfo > ni and ni != 0:
            score += 1
        # 5. Current ratio > 1
        if self._safe_float(info.get("currentRatio")) > 1:
            score += 1
        # 6. Gross margin improving (use presence of positive margin as proxy)
        if self._safe_float(info.get("grossMargins")) > 0.2:
            score += 1
        # 7. Asset turnover (revenue/total assets proxy via ROA and margin)
        if self._safe_float(info.get("returnOnAssets")) > 0.05:
            score += 1
        # 8. No new dilution (approximate: positive EPS)
        if self._safe_float(info.get("trailingEps")) > 0:
            score += 1
        # 9. Revenue growth
        if self._safe_float(info.get("revenueGrowth")) > 0:
            score += 1

        return float(score)

    def _estimate_altman_z(self, info: Dict) -> float:
        """
        Estimate Altman Z-Score from yfinance info.
        Z = 1.2*WC/TA + 1.4*RE/TA + 3.3*EBIT/TA + 0.6*MC/TL + 1.0*Rev/TA
        Uses available proxies from yfinance.
        """
        try:
            total_assets = self._safe_float(info.get("totalAssets"))
            if total_assets <= 0:
                return 0.0

            # Working capital / Total assets (approximate via current ratio)
            current_ratio = self._safe_float(info.get("currentRatio"))
            # If CR > 1, WC is positive; approximate WC/TA ~ (CR-1) * currentAssets/TA
            wc_ta = max(0, (current_ratio - 1) * 0.3) if current_ratio > 0 else 0

            # Retained earnings / Total assets (approximate using ROE * equity/assets)
            roe = self._safe_float(info.get("returnOnEquity"))
            re_ta = max(0, roe * 0.5) if roe > 0 else 0

            # EBIT / Total assets (approximate using operating margins * revenue / assets)
            ebit = self._safe_float(info.get("ebitda"))
            ebit_ta = ebit / total_assets if total_assets > 0 else 0

            # Market cap / Total liabilities
            market_cap = self._safe_float(info.get("marketCap"))
            total_debt = self._safe_float(info.get("totalDebt"))
            mc_tl = market_cap / total_debt if total_debt > 0 else 5.0  # No debt = very safe

            # Revenue / Total assets
            revenue = self._safe_float(info.get("totalRevenue"))
            rev_ta = revenue / total_assets if total_assets > 0 else 0

            z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mc_tl + 1.0 * rev_ta
            return round(max(0, z), 2)

        except Exception:
            return 0.0

    @staticmethod
    def _safe_float(val) -> float:
        """Safely convert to float, default 0."""
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    # ── Scoring Engine ───────────────────────────────────

    def _compute_score(self, m: Dict) -> tuple:
        """
        Compute a 0→1 composite fundamental score.

        Components (weighted):
          - Value (30%):  PE, PB, EV/EBITDA
          - Quality (35%): ROE, Net Margin, FCF Yield
          - Safety (35%):  Altman Z, Piotroski F

        Each sub-score is normalized to 0→1.
        """

        # ── Value Score (30%) ────────────────────────────
        pe = m.get("pe_ratio", 0)
        pb = m.get("pb_ratio", 0)
        ev_ebitda = m.get("ev_ebitda", 0)

        # Lower PE is better (for NASDAQ growth, use generous thresholds)
        if pe <= 0:
            pe_sc = 0.3  # Negative earnings
        elif pe <= 15:
            pe_sc = 1.0
        elif pe <= 25:
            pe_sc = 0.8
        elif pe <= 40:
            pe_sc = 0.6
        elif pe <= 60:
            pe_sc = 0.4
        else:
            pe_sc = 0.2

        # PB: lower is better
        if pb <= 0:
            pb_sc = 0.3
        elif pb <= 3:
            pb_sc = 1.0
        elif pb <= 8:
            pb_sc = 0.7
        elif pb <= 15:
            pb_sc = 0.5
        else:
            pb_sc = 0.3

        # EV/EBITDA: lower is better
        if ev_ebitda <= 0:
            ev_sc = 0.3
        elif ev_ebitda <= 12:
            ev_sc = 1.0
        elif ev_ebitda <= 20:
            ev_sc = 0.7
        elif ev_ebitda <= 35:
            ev_sc = 0.5
        else:
            ev_sc = 0.3

        value_score = (pe_sc * 0.4 + pb_sc * 0.3 + ev_sc * 0.3)

        # ── Quality Score (35%) ──────────────────────────
        roe = m.get("roe", 0)
        net_margin = m.get("net_margin", 0)
        fcf_yield = m.get("fcf_yield", 0)

        # ROE: higher is better
        roe_sc = min(max(roe / 0.30, 0), 1.0) if roe > 0 else 0.2

        # Net margin: higher is better
        margin_sc = min(max(net_margin / 0.25, 0), 1.0) if net_margin > 0 else 0.2

        # FCF yield: higher is better
        fcf_sc = min(max(fcf_yield / 0.06, 0), 1.0) if fcf_yield > 0 else 0.3

        quality_score = (roe_sc * 0.4 + margin_sc * 0.35 + fcf_sc * 0.25)

        # ── Safety Score (35%) ───────────────────────────
        z = m.get("altman_z_score", 0)
        f = m.get("piotroski_score", 0)

        # Altman Z: >2.99 = safe, 1.81-2.99 = grey, <1.81 = distress
        if z >= 3.0:
            z_sc = 1.0
        elif z >= 2.0:
            z_sc = 0.7
        elif z >= 1.0:
            z_sc = 0.4
        else:
            z_sc = 0.2

        # Piotroski: 0-9, higher is better
        f_sc = min(f / 9.0, 1.0) if f > 0 else 0.3

        safety_score = (z_sc * 0.5 + f_sc * 0.5)

        # ── Composite ────────────────────────────────────
        composite = (
            value_score * 0.30
            + quality_score * 0.35
            + safety_score * 0.35
        )

        sub_scores = {
            "value": round(value_score, 3),
            "quality": round(quality_score, 3),
            "safety": round(safety_score, 3),
            "pe_sc": round(pe_sc, 2),
            "roe_sc": round(roe_sc, 2),
            "z_sc": round(z_sc, 2),
            "f_sc": round(f_sc, 2),
        }

        return composite, sub_scores

    # ── Rationale ────────────────────────────────────────

    def _build_rationale(self, symbol: str, m: Dict, sub: Dict) -> str:
        """Build human-readable rationale."""
        lines = [f"📊 {symbol} Fundamentals:"]

        # Value
        lines.append(f"  Value ({sub['value']:.2f}): PE={m['pe_ratio']:.1f} PB={m['pb_ratio']:.1f} EV/EBITDA={m['ev_ebitda']:.1f}")

        # Quality
        roe_pct = m['roe'] * 100 if m['roe'] else 0
        margin_pct = m['net_margin'] * 100 if m['net_margin'] else 0
        lines.append(f"  Quality ({sub['quality']:.2f}): ROE={roe_pct:.1f}% Margin={margin_pct:.1f}% FCF Yield={m['fcf_yield']:.2%}")

        # Safety
        z = m['altman_z_score']
        z_zone = "Safe" if z > 2.99 else "Grey" if z > 1.81 else "Distress"
        lines.append(f"  Safety ({sub['safety']:.2f}): Altman Z={z:.1f} ({z_zone}) Piotroski={m['piotroski_score']:.0f}/9")

        return "\n".join(lines)
