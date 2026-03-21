"""
Technical Agent — Tier 2: Price/Volume Technical Analysis.

Adapted from gcp-slack-agent-cloud TechnicalAnalyzer.
Adds ATR, ADX, Hurst exponent to existing EMA/RSI/MACD/Bollinger.
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from ..data_client import AlpacaOHLCVClient, FMPClient
from .base_agent import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    """
    Tier 2 agent that computes technical indicators and produces
    a composite technical score with regime classification.
    """

    def __init__(self):
        self.alpaca = AlpacaOHLCVClient()
        self.fmp = FMPClient()

    @property
    def name(self) -> str:
        return "TechnicalAgent"

    async def analyze(self, symbol: str, ohlcv_df: Optional[pd.DataFrame] = None, **kwargs) -> AgentResult:
        """
        Full technical analysis for a single stock.

        Args:
            symbol: Ticker symbol (e.g., 'NVDA').
            ohlcv_df: Pre-fetched OHLCV data (optional, will fetch if None).
        """
        self._log_start(f"({symbol})")

        # Fetch data if not provided
        if ohlcv_df is None or ohlcv_df.empty:
            ohlcv_df = self.alpaca.get_ohlcv(symbol, days=365)

        if ohlcv_df.empty:
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                confidence=0.1,
                rationale=f"No OHLCV data available for {symbol}.",
            )

        # Normalize column names to lowercase
        ohlcv_df.columns = [c.lower() for c in ohlcv_df.columns]

        # ── Calculate all indicators ─────────────────────
        indicators = {}
        indicators.update(self._calculate_ema(ohlcv_df))
        indicators.update(self._calculate_rsi(ohlcv_df))
        indicators.update(self._calculate_macd(ohlcv_df))
        indicators.update(self._calculate_bollinger(ohlcv_df))
        indicators.update(self._calculate_atr(ohlcv_df))
        indicators.update(self._calculate_adx(ohlcv_df))
        indicators.update(self._calculate_hurst(ohlcv_df))
        momentum_regime = self._classify_momentum_regime(ohlcv_df, indicators)

        # ── Score and classify ───────────────────────────
        score = self._compute_score(indicators, momentum_regime)
        regime = self._classify_regime(indicators)

        result = AgentResult(
            agent_name=self.name,
            score=score,
            confidence=0.8,
            rationale=self._build_rationale(symbol, indicators, momentum_regime, regime),
            data={
                "symbol": symbol,
                "indicators": indicators,
                "regime": regime,
                "momentum_regime": momentum_regime,
            },
        )
        self._log_done(result)
        return result

    # ═══════════════════════════════════════════════════════
    #  Indicator Calculations
    # ═══════════════════════════════════════════════════════

    def _calculate_ema(self, df: pd.DataFrame) -> Dict:
        """EMA 20, 50, 200 — trend direction."""
        close = df["close"]
        current = close.iloc[-1]
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        ema200 = close.ewm(span=200).mean().iloc[-1] if len(close) >= 200 else None

        return {
            "ema20": round(float(ema20), 2),
            "ema50": round(float(ema50), 2),
            "ema200": round(float(ema200), 2) if ema200 else None,
            "price": round(float(current), 2),
            "above_ema20": bool(current > ema20),
            "above_ema50": bool(current > ema50),
            "above_ema200": bool(current > ema200) if ema200 else None,
        }

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """RSI — momentum oscillator."""
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1])

        return {
            "rsi": round(current_rsi, 2),
            "rsi_zone": "overbought" if current_rsi > 70 else "oversold" if current_rsi < 30 else "neutral",
        }

    def _calculate_macd(self, df: pd.DataFrame) -> Dict:
        """MACD — trend momentum."""
        close = df["close"]
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal

        return {
            "macd_line": round(float(macd.iloc[-1]), 4),
            "macd_signal": round(float(signal.iloc[-1]), 4),
            "macd_histogram": round(float(histogram.iloc[-1]), 4),
            "macd_bullish": bool(macd.iloc[-1] > signal.iloc[-1]),
        }

    def _calculate_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Dict:
        """Bollinger Bands — volatility + overextension."""
        close = df["close"]
        sma = close.rolling(period).mean()
        std = close.rolling(period).std()
        upper = sma + std_dev * std
        lower = sma - std_dev * std

        current = float(close.iloc[-1])
        bb_upper = float(upper.iloc[-1])
        bb_lower = float(lower.iloc[-1])
        bb_width = (bb_upper - bb_lower) / float(sma.iloc[-1])

        # %B: position within bands
        pct_b = (current - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) != 0 else 0.5

        return {
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "bb_width": round(bb_width, 4),
            "bb_pct_b": round(float(pct_b), 4),
            "bb_zone": "upper" if pct_b > 0.8 else "lower" if pct_b < 0.2 else "middle",
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """Average True Range — volatility measure."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        current_atr = float(atr.iloc[-1])
        current_price = float(close.iloc[-1])
        atr_pct = (current_atr / current_price) * 100

        return {
            "atr": round(current_atr, 2),
            "atr_pct": round(atr_pct, 2),
            "volatility_level": "high" if atr_pct > 3 else "moderate" if atr_pct > 1.5 else "low",
        }

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict:
        """Average Directional Index — trend strength (not direction)."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smoothed with EMA
        atr = tr.ewm(span=period, min_periods=period).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, min_periods=period).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, min_periods=period).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, min_periods=period).mean()

        current_adx = float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else 0

        return {
            "adx": round(current_adx, 2),
            "plus_di": round(float(plus_di.iloc[-1]), 2),
            "minus_di": round(float(minus_di.iloc[-1]), 2),
            "trend_strength": "strong" if current_adx > 25 else "weak" if current_adx < 20 else "moderate",
            "trend_direction": "bullish" if float(plus_di.iloc[-1]) > float(minus_di.iloc[-1]) else "bearish",
        }

    def _calculate_hurst(self, df: pd.DataFrame, lag_max: int = 100) -> Dict:
        """
        Hurst Exponent via R/S (Rescaled Range) analysis.
        H < 0.5 → mean-reverting
        H ≈ 0.5 → random walk
        H > 0.5 → trending
        """
        close = df["close"].values
        if len(close) < lag_max + 10:
            lag_max = max(20, len(close) // 3)

        lags = range(10, lag_max)
        rs_values = []

        for lag in lags:
            # Split series into chunks of length 'lag'
            chunks = [close[i : i + lag] for i in range(0, len(close) - lag, lag)]
            rs_list = []
            for chunk in chunks:
                if len(chunk) < 10:
                    continue
                mean = np.mean(chunk)
                deviations = chunk - mean
                cumulative = np.cumsum(deviations)
                R = np.max(cumulative) - np.min(cumulative)
                S = np.std(chunk, ddof=1) if np.std(chunk, ddof=1) > 0 else 1e-10
                rs_list.append(R / S)
            if rs_list:
                rs_values.append((np.log(lag), np.log(np.mean(rs_list))))

        # Linear fit: log(R/S) = H * log(n)
        if len(rs_values) > 5:
            x = np.array([r[0] for r in rs_values])
            y = np.array([r[1] for r in rs_values])
            hurst = float(np.polyfit(x, y, 1)[0])
        else:
            hurst = 0.5  # Default to random walk

        hurst = max(0.0, min(1.0, hurst))  # Clamp

        if hurst > 0.55:
            classification = "trending"
        elif hurst < 0.45:
            classification = "mean_reverting"
        else:
            classification = "random_walk"

        return {
            "hurst": round(hurst, 4),
            "hurst_classification": classification,
        }

    # ═══════════════════════════════════════════════════════
    #  Regime & Scoring
    # ═══════════════════════════════════════════════════════

    def _classify_momentum_regime(self, df: pd.DataFrame, indicators: Dict) -> str:
        """Determine current momentum regime based on EMA alignment."""
        above_20 = indicators.get("above_ema20", False)
        above_50 = indicators.get("above_ema50", False)
        above_200 = indicators.get("above_ema200")

        if above_20 and above_50 and above_200:
            return "strong_uptrend"
        elif above_20 and above_50:
            return "uptrend"
        elif not above_20 and not above_50 and above_200 is False:
            return "strong_downtrend"
        elif not above_20 and not above_50:
            return "downtrend"
        else:
            return "consolidation"

    def _classify_regime(self, indicators: Dict) -> str:
        """Overall regime classification combining all indicators."""
        hurst = indicators.get("hurst_classification", "random_walk")
        adx_strength = indicators.get("trend_strength", "moderate")

        if hurst == "trending" and adx_strength == "strong":
            return "trending"
        elif hurst == "mean_reverting":
            return "mean_reverting"
        else:
            return "mixed"

    def _compute_score(self, indicators: Dict, momentum: str) -> float:
        """
        Composite technical score (0→1, higher = more bullish).

        Weights:
        - EMA alignment: 25%
        - RSI: 20%
        - MACD: 20%
        - Bollinger %B: 15%
        - ADX direction: 20%
        """
        scores = []

        # EMA alignment (25%)
        ema_score = {
            "strong_uptrend": 0.95,
            "uptrend": 0.75,
            "consolidation": 0.50,
            "downtrend": 0.25,
            "strong_downtrend": 0.05,
        }.get(momentum, 0.5)
        scores.append(("ema", ema_score, 0.25))

        # RSI (20%) — not too overbought, not oversold
        rsi = indicators.get("rsi", 50)
        if rsi > 70:
            rsi_score = 0.4  # Overbought — risk of pullback
        elif rsi > 50:
            rsi_score = 0.7 + (rsi - 50) * 0.005  # Moderately bullish
        elif rsi > 30:
            rsi_score = 0.3 + (rsi - 30) * 0.02  # Neutral
        else:
            rsi_score = 0.6  # Oversold — potential bounce
        scores.append(("rsi", rsi_score, 0.20))

        # MACD (20%)
        macd_bull = indicators.get("macd_bullish", False)
        macd_hist = indicators.get("macd_histogram", 0)
        macd_score = 0.7 if macd_bull else 0.3
        if macd_bull and macd_hist > 0:
            macd_score = 0.85
        scores.append(("macd", macd_score, 0.20))

        # Bollinger %B (15%)
        pct_b = indicators.get("bb_pct_b", 0.5)
        bb_score = min(1.0, max(0.0, pct_b))  # Direct mapping
        scores.append(("bollinger", bb_score, 0.15))

        # ADX direction (20%)
        adx_dir = indicators.get("trend_direction", "neutral")
        adx_val = indicators.get("adx", 20)
        if adx_dir == "bullish" and adx_val > 25:
            adx_score = 0.85
        elif adx_dir == "bullish":
            adx_score = 0.65
        elif adx_dir == "bearish" and adx_val > 25:
            adx_score = 0.15
        else:
            adx_score = 0.4
        scores.append(("adx", adx_score, 0.20))

        # Weighted average
        total = sum(s * w for _, s, w in scores)
        return round(total, 3)

    # ═══════════════════════════════════════════════════════
    #  Rationale
    # ═══════════════════════════════════════════════════════

    def _build_rationale(self, symbol: str, indicators: Dict, momentum: str, regime: str) -> str:
        lines = [
            f"⚡ {symbol} Technical Analysis",
            f"  Regime: {regime.upper()} | Momentum: {momentum.replace('_', ' ').title()}",
            f"  Hurst: {indicators.get('hurst', 'N/A')} ({indicators.get('hurst_classification', 'N/A')})",
            "",
            f"  📊 Price: ${indicators.get('price', 0):.2f}",
            f"     EMA20: ${indicators.get('ema20', 0):.2f} | EMA50: ${indicators.get('ema50', 0):.2f} | EMA200: {'$' + str(indicators.get('ema200', 'N/A'))}",
            f"     RSI: {indicators.get('rsi', 'N/A')} ({indicators.get('rsi_zone', 'N/A')})",
            f"     MACD: {'Bullish ✅' if indicators.get('macd_bullish') else 'Bearish ❌'} (hist: {indicators.get('macd_histogram', 0):.4f})",
            f"     Bollinger: {indicators.get('bb_zone', 'N/A')} (%%B: {indicators.get('bb_pct_b', 0):.2f})",
            f"     ATR: {indicators.get('atr', 0):.2f} ({indicators.get('volatility_level', 'N/A')} volatility, {indicators.get('atr_pct', 0):.1f}%)",
            f"     ADX: {indicators.get('adx', 0):.1f} ({indicators.get('trend_strength', 'N/A')} {indicators.get('trend_direction', 'N/A')})",
        ]
        return "\n".join(lines)
