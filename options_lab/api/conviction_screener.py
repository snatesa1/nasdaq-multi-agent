"""
5-Pillar Practitioner Conviction Screener module for the Saxo Wheel Strategy.

Replaces academic Piotroski F-Score and Altman Z-Score with 5 practical conviction pillars:
1. Earnings Predictability (25%): Surprise history, beat rate, analyst consensus tightness
2. Cash Generation Power (25%): FCF Yield, Operating Cash Flow Margin, Cash-vs-Earnings quality
3. Balance Sheet Fortress (20%): Net Cash Position, Debt/EBITDA, Current Ratio
4. Institutional Conviction (15%): Institutional ownership %, Analyst recommendation mean, Short interest %
5. Valuation Reasonableness (15%): Forward vs Trailing PE, PEG ratio, 52W range position
"""

import logging
import yfinance as yf
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely converts input value to float with default fallback."""
    if val is None:
        return default
    try:
        res = float(val)
        return res if not (res != res) else default  # Handles NaN
    except (ValueError, TypeError):
        return default


class ConvictionScreener:
    """
    Evaluates 5 practitioner conviction pillars for options selling candidates.
    Returns composite conviction score [0.0 - 1.0] and decision tier.
    """

    PILLAR_WEIGHTS = {
        "earnings_predictability": 0.25,
        "cash_generation": 0.25,
        "balance_sheet": 0.20,
        "institutional_conviction": 0.15,
        "valuation": 0.15,
    }

    QUALIFIED_THRESHOLD = 0.70
    MARGINAL_THRESHOLD = 0.60

    def __init__(self):
        pass

    def score_earnings_predictability(self, ticker: yf.Ticker, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pillar 1: Earnings Predictability (25% weight)
        Evaluates surprise history, consistency, and analyst estimate tightness.
        """
        avg_surprise = 0.0
        surprise_std = 25.0
        beat_rate = 0.5

        try:
            earnings_hist = ticker.earnings_history
            if earnings_hist is not None and not earnings_hist.empty:
                surprises = earnings_hist["Surprise(%)"].dropna()
                if not surprises.empty:
                    avg_surprise = safe_float(surprises.mean())
                    surprise_std = safe_float(surprises.std(), default=20.0)
                    beat_rate = safe_float((surprises > 0).mean(), default=0.5)
        except Exception as e:
            logger.debug(f"Could not parse earnings history for {ticker.ticker}: {e}")

        # Analyst estimate spread
        target_high = safe_float(info.get("targetHighPrice"))
        target_low = safe_float(info.get("targetLowPrice"))
        target_mean = safe_float(info.get("targetMeanPrice"))

        if target_mean > 0 and target_high > 0 and target_low > 0:
            analyst_spread = (target_high - target_low) / target_mean
        else:
            analyst_spread = 0.40  # Moderate default

        # Component scores [0.0 - 1.0]
        surprise_score = min(1.0, max(0.0, (avg_surprise + 10.0) / 20.0))  # Maps -10% to +10%
        consistency_score = max(0.0, 1.0 - (surprise_std / 30.0))
        beat_score = min(1.0, max(0.0, beat_rate))
        consensus_score = max(0.0, 1.0 - (analyst_spread / 0.80))

        composite = (
            surprise_score * 0.30 +
            consistency_score * 0.25 +
            beat_score * 0.25 +
            consensus_score * 0.20
        )

        return {
            "score": round(composite, 3),
            "avg_surprise_pct": round(avg_surprise, 1),
            "surprise_std": round(surprise_std, 1),
            "beat_rate": round(beat_rate, 2),
            "analyst_spread": round(analyst_spread, 2),
        }

    def score_cash_generation(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pillar 2: Cash Generation Power (25% weight)
        Evaluates FCF yield, operating cash flow margin, and cash-vs-earnings quality.
        Includes sector proxy for Financial Services (banks/insurers) where CFO is not reported.
        """
        sector = info.get("sector", "")
        is_financial = (sector == "Financial Services" or sector == "Financials")

        fcf = safe_float(info.get("freeCashflow"))
        mcap = safe_float(info.get("marketCap"))
        cfo = safe_float(info.get("operatingCashflow"))
        revenue = safe_float(info.get("totalRevenue"))
        net_income = safe_float(info.get("netIncomeToCommon") or info.get("netIncome"))
        net_margin = safe_float(info.get("profitMargins"))
        roa = safe_float(info.get("returnOnAssets"))

        if is_financial and (cfo <= 0.0 or fcf <= 0.0 or revenue == 0.0):
            # Financial Services sector proxy (Banks/Insurance: GAAP operating cash flow includes loan originations)
            fcf_yield = (net_income / mcap) if mcap > 0 else 0.0
            ocf_margin = net_margin if net_margin > 0 else 0.25
            cash_quality = 1.0 if roa > 0.01 else (roa / 0.01 if roa > 0 else 0.5)
        else:
            fcf_yield = (fcf / mcap) if mcap > 0 else 0.0
            ocf_margin = (cfo / revenue) if revenue > 0 else 0.0
            cash_quality = (cfo / net_income) if net_income > 0 else (1.0 if cfo > 0 else 0.0)

        # Component scores
        fcf_score = min(1.0, max(0.0, fcf_yield / 0.06))           # 6% FCF yield = 1.0
        ocf_score = min(1.0, max(0.0, ocf_margin / 0.20))         # 20% OCF margin = 1.0
        quality_score = min(1.0, max(0.0, cash_quality / 1.3))     # CFO 1.3x NI = 1.0

        composite = fcf_score * 0.35 + ocf_score * 0.35 + quality_score * 0.30

        return {
            "score": round(composite, 3),
            "fcf_yield_pct": round(fcf_yield * 100, 2),
            "ocf_margin_pct": round(ocf_margin * 100, 2),
            "cash_vs_earnings_ratio": round(cash_quality, 2),
            "is_financial_sector_proxy": is_financial
        }

    def score_balance_sheet(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pillar 3: Balance Sheet Fortress (20% weight)
        Evaluates net cash, Debt/EBITDA, and liquidity ratio.
        Includes Tier 1 equity capital proxy for Financial Services.
        """
        sector = info.get("sector", "")
        is_financial = (sector == "Financial Services" or sector == "Financials")

        total_cash = safe_float(info.get("totalCash"))
        total_debt = safe_float(info.get("totalDebt"))
        ebitda = safe_float(info.get("ebitda"))
        current_ratio = safe_float(info.get("currentRatio"), default=1.0)
        book_value = safe_float(info.get("bookValue"))

        if is_financial and (ebitda == 0.0 or current_ratio == 1.0):
            # For banks, equity capital > 0 and positive book value represent balance sheet fortress
            net_cash = safe_float(info.get("marketCap")) * 0.10  # Proxy cash buffer
            debt_to_ebitda = 1.5  # Standard bank regulatory capital proxy
            net_cash_score = 0.85 if book_value > 0 else 0.40
            leverage_score = 0.80
            liquidity_score = 0.85
        else:
            net_cash = total_cash - total_debt
            debt_to_ebitda = (total_debt / ebitda) if ebitda > 0 else (0.0 if total_debt == 0 else 8.0)

            if net_cash > 0:
                net_cash_score = 1.0
            else:
                net_cash_score = max(0.2, 1.0 - (abs(net_cash) / (total_cash + 1e6)))

            leverage_score = max(0.0, 1.0 - (debt_to_ebitda / 4.0))     # <= 4.0x EBITDA
            liquidity_score = min(1.0, max(0.0, (current_ratio - 0.5) / 1.5))

        composite = net_cash_score * 0.40 + leverage_score * 0.35 + liquidity_score * 0.25

        return {
            "score": round(composite, 3),
            "net_cash_millions": round(net_cash / 1e6, 1),
            "debt_to_ebitda": round(debt_to_ebitda, 1),
            "current_ratio": round(current_ratio, 2),
            "is_financial_sector_proxy": is_financial
        }

    def score_institutional_conviction(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pillar 4: Institutional & Analyst Conviction (15% weight)
        Evaluates institutional ownership %, analyst recommendations, short interest.
        """
        inst_pct = safe_float(info.get("heldPercentInstitutions"))
        rec_mean = safe_float(info.get("recommendationMean"), default=3.0)  # 1.0 (Strong Buy) to 5.0 (Sell)
        num_analysts = safe_float(info.get("numberOfAnalystOpinions"))
        short_pct = safe_float(info.get("shortPercentOfFloat"))

        # Component scores
        inst_score = min(1.0, max(0.0, inst_pct / 0.75))          # 75%+ institutional = 1.0
        rec_score = max(0.0, (5.0 - rec_mean) / 4.0)              # 1.0 -> 1.0, 3.0 -> 0.5, 5.0 -> 0.0
        coverage_score = min(1.0, max(0.0, num_analysts / 15.0))   # 15+ analysts = 1.0
        short_score = max(0.0, 1.0 - (short_pct / 0.08))          # <= 8% short float = 1.0

        composite = (
            inst_score * 0.30 +
            rec_score * 0.30 +
            coverage_score * 0.20 +
            short_score * 0.20
        )

        return {
            "score": round(composite, 3),
            "institutional_pct": round(inst_pct * 100, 1),
            "recommendation_mean": round(rec_mean, 2),
            "analyst_count": int(num_analysts),
            "short_interest_pct": round(short_pct * 100, 1),
        }

    def score_valuation(self, ticker: yf.Ticker, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pillar 5: Valuation Reasonableness (15% weight)
        Evaluates Forward vs Trailing PE, PEG ratio, and 52W price range position.
        """
        forward_pe = safe_float(info.get("forwardPE"))
        trailing_pe = safe_float(info.get("trailingPE"))
        peg = safe_float(info.get("pegRatio"))

        # Range position (0.0 at 52W low, 1.0 at 52W high)
        range_position = 0.5
        try:
            hist = ticker.history(period="1y")
            if not hist.empty and "Close" in hist.columns:
                current_price = safe_float(hist["Close"].iloc[-1])
                low_52w = safe_float(hist["Low"].min())
                high_52w = safe_float(hist["High"].max())
                if high_52w > low_52w:
                    range_position = (current_price - low_52w) / (high_52w - low_52w)
        except Exception as e:
            logger.debug(f"Could not compute 52W range for {ticker.ticker}: {e}")

        # Component scores
        pe_trend_score = 1.0 if (forward_pe > 0 and forward_pe < trailing_pe) else 0.5
        
        if peg <= 0:
            peg_score = 0.4
        elif peg <= 1.2:
            peg_score = 1.0
        elif peg <= 2.0:
            peg_score = 0.7
        else:
            peg_score = max(0.2, 1.0 - (peg - 2.0) / 3.0)

        # Mid-range pullback (0.25 - 0.65) is ideal for selling puts
        if 0.25 <= range_position <= 0.65:
            range_score = 1.0
        elif range_position < 0.25:
            range_score = 0.7  # Low price = value, but check knife risk
        else:
            range_score = max(0.2, 1.0 - (range_position - 0.65) / 0.35)

        composite = pe_trend_score * 0.30 + peg_score * 0.35 + range_score * 0.35

        return {
            "score": round(composite, 3),
            "forward_pe": round(forward_pe, 1),
            "trailing_pe": round(trailing_pe, 1),
            "peg_ratio": round(peg, 2),
            "range_position_pct": round(range_position * 100, 1),
        }

    def screen(self, symbol: str) -> Dict[str, Any]:
        """
        Executes full 5-pillar conviction evaluation for a single ticker symbol.
        """
        symbol = symbol.strip().upper()
        logger.info(f"🔍 ConvictionScreener: Screening {symbol} across 5 pillars...")

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}

            if not info or info.get("quoteType") is None:
                return {
                    "symbol": symbol,
                    "conviction_score": 0.0,
                    "decision": "REJECTED",
                    "reason": "No ticker info available from provider",
                    "pillars": {},
                }

            # Evaluate each pillar
            p1 = self.score_earnings_predictability(ticker, info)
            p2 = self.score_cash_generation(info)
            p3 = self.score_balance_sheet(info)
            p4 = self.score_institutional_conviction(info)
            p5 = self.score_valuation(ticker, info)

            pillars = {
                "earnings_predictability": p1,
                "cash_generation": p2,
                "balance_sheet": p3,
                "institutional_conviction": p4,
                "valuation": p5,
            }

            # Weighted composite score
            composite_score = sum(
                pillars[key]["score"] * self.PILLAR_WEIGHTS[key]
                for key in self.PILLAR_WEIGHTS
            )
            composite_score = round(composite_score, 3)

            # Decision tier
            if composite_score >= self.QUALIFIED_THRESHOLD:
                decision = "QUALIFIED"
            elif composite_score >= self.MARGINAL_THRESHOLD:
                decision = "MARGINAL"
            else:
                decision = "REJECTED"

            # Identify strongest and weakest pillars
            sorted_pillars = sorted(pillars.items(), key=lambda x: x[1]["score"], reverse=True)
            strongest_pillar = sorted_pillars[0][0]
            weakest_pillar = sorted_pillars[-1][0]

            rationale = (
                f"{symbol} scored {composite_score:.2f}/1.00 ({decision}). "
                f"Strongest pillar: {strongest_pillar} ({pillars[strongest_pillar]['score']:.2f}). "
                f"Weakest pillar: {weakest_pillar} ({pillars[weakest_pillar]['score']:.2f})."
            )

            return {
                "symbol": symbol,
                "conviction_score": composite_score,
                "decision": decision,
                "strongest_pillar": strongest_pillar,
                "weakest_pillar": weakest_pillar,
                "rationale": rationale,
                "pillars": pillars,
            }

        except Exception as e:
            logger.error(f"Error screening conviction for {symbol}: {e}")
            return {
                "symbol": symbol,
                "conviction_score": 0.0,
                "decision": "REJECTED",
                "reason": f"Screening error: {str(e)}",
                "pillars": {},
            }
