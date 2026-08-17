"""
Signal Engine for the Saxo Wheel Options Protocol.

Composes 3 independent signal layers into a single trade decision score:
- Layer 1: Momentum Signal (50% weight) — Saxo OHLC candles + TechnicalAgent (EMA alignment, RSI, MACD, Hurst, ADX)
- Layer 2: Macro Regime Signal (30% weight) — VIX level + FRED Yield Curve slope (T10Y2Y)
- Layer 3: News Sentiment Signal (20% weight) — News headline sentiment scoring

Decision thresholds:
- composite_score >= 0.55: PROCEED
- composite_score 0.40 - 0.55: CAUTION (requires Slack human approval)
- composite_score < 0.40: BLOCK (trade halted)
"""

import logging
import pandas as pd
import yfinance as yf
from typing import Dict, Any, Optional

from .agents.technical_agent import TechnicalAgent

logger = logging.getLogger(__name__)


class SignalEngine:
    """
    Multi-layer signal scoring engine for Saxo Wheel options entry timing.
    """

    WEIGHT_MOMENTUM = 0.50
    WEIGHT_MACRO = 0.30
    WEIGHT_NEWS = 0.20

    def __init__(self):
        self.technical_agent = TechnicalAgent()

    async def compute_momentum_score(self, symbol: str, ohlcv_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Layer 1: Momentum Signal (50% weight).
        Uses TechnicalAgent to evaluate trend, RSI oversold pullbacks, and MACD alignment.
        """
        try:
            res = await self.technical_agent.analyze(symbol, ohlcv_df=ohlcv_df)
            data = res.data or {}
            indicators = data.get("indicators", {})
            regime = data.get("regime", "neutral")
            raw_tech_score = res.score

            rsi = indicators.get("rsi", 50.0)
            price = indicators.get("price", 0.0)
            above_ema200 = indicators.get("above_ema200", True)

            # For Cash-Secured Put (CSP) selling:
            # We WANT a healthy stock making a mild pullback to support (RSI 30 - 50, price > EMA200).
            if above_ema200 and 30 <= rsi <= 50:
                adjusted_score = max(raw_tech_score, 0.75)  # Ideal pullback setup
            elif not above_ema200 and rsi < 30:
                adjusted_score = min(raw_tech_score, 0.35)  # Downtrending knife drop
            else:
                adjusted_score = raw_tech_score

            return {
                "score": round(adjusted_score, 3),
                "raw_technical_score": round(raw_tech_score, 3),
                "rsi": rsi,
                "regime": regime,
                "above_ema200": above_ema200,
                "price": price,
            }
        except Exception as e:
            logger.error(f"Error computing momentum score for {symbol}: {e}")
            return {
                "score": 0.50,
                "raw_technical_score": 0.50,
                "rsi": 50.0,
                "regime": "unknown",
                "above_ema200": True,
                "price": 0.0,
            }

    def compute_macro_score(self, vix_level: Optional[float] = None, yield_spread: Optional[float] = None) -> Dict[str, Any]:
        """
        Layer 2: Macro Regime Signal (30% weight).
        Fetches VIX volatility level and US Yield Curve 10Y-2Y spread.
        """
        # Fetch VIX if not provided
        if vix_level is None:
            try:
                vix_ticker = yf.Ticker("^VIX")
                vix_hist = vix_ticker.history(period="5d")
                if not vix_hist.empty:
                    vix_level = float(vix_hist["Close"].iloc[-1])
                else:
                    vix_level = 18.0
            except Exception:
                vix_level = 18.0

        # Fetch Yield Curve spread (10Y minus 2Y) if not provided
        if yield_spread is None:
            try:
                tnx = yf.Ticker("^TNX").history(period="5d")["Close"].iloc[-1] / 10.0  # 10Y Yield
                irx = yf.Ticker("^IRX").history(period="5d")["Close"].iloc[-1] / 10.0  # Short yield proxy
                yield_spread = float(tnx - irx)
            except Exception:
                yield_spread = 0.25

        # Score VIX Regime
        if vix_level < 15.0:
            vix_score = 0.85
            vix_regime = "COMPLACENT_LOW_VOL"
        elif vix_level <= 22.0:
            vix_score = 0.75
            vix_regime = "NORMAL_VOLATILITY"
        elif vix_level <= 30.0:
            vix_score = 0.50
            vix_regime = "ELEVATED_VOLATILITY"
        else:
            vix_score = 0.20
            vix_regime = "HIGH_FEAR_STRESS"

        # Yield Curve modifier
        curve_bonus = 0.10 if yield_spread > 0 else -0.15
        curve_regime = "NORMAL_SLOPE" if yield_spread > 0 else "INVERTED_RECESSION_RISK"

        macro_score = min(1.0, max(0.1, vix_score + curve_bonus))

        return {
            "score": round(macro_score, 3),
            "vix_level": round(vix_level, 2),
            "vix_regime": vix_regime,
            "yield_spread": round(yield_spread, 2),
            "curve_regime": curve_regime,
        }

    def compute_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Layer 3: News Sentiment Signal (20% weight).
        Analyzes recent news headlines for negative risk events (e.g. SEC investigations, litigation).
        """
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news or []
            headline_count = len(news_items)

            if not news_items:
                return {
                    "score": 0.65,
                    "sentiment": "NEUTRAL",
                    "headline_count": 0,
                    "flagged_keywords": [],
                }

            negative_keywords = ["investigation", "lawsuit", "sec", "probe", "bankrupt", "fraud", "downgrade", "recall"]
            flagged = []

            for item in news_items[:10]:
                title = item.get("title", "").lower()
                for kw in negative_keywords:
                    if kw in title:
                        flagged.append(kw)

            if len(flagged) >= 2:
                sentiment_score = 0.20
                sentiment = "BEARISH_RISK"
            elif len(flagged) == 1:
                sentiment_score = 0.45
                sentiment = "CAUTIOUS"
            else:
                sentiment_score = 0.75
                sentiment = "BULLISH_NEUTRAL"

            return {
                "score": round(sentiment_score, 3),
                "sentiment": sentiment,
                "headline_count": headline_count,
                "flagged_keywords": list(set(flagged)),
            }
        except Exception as e:
            logger.error(f"Error computing news sentiment for {symbol}: {e}")
            return {
                "score": 0.65,
                "sentiment": "NEUTRAL",
                "headline_count": 0,
                "flagged_keywords": [],
            }

    async def compute_composite_score(self, symbol: str, ohlcv_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Computes the 3-layer composite signal score for trade decisioning.
        """
        symbol = symbol.strip().upper()
        logger.info(f"📊 SignalEngine: Computing composite signal score for {symbol}...")

        momentum = await self.compute_momentum_score(symbol, ohlcv_df=ohlcv_df)
        macro = self.compute_macro_score()
        news = self.compute_news_sentiment(symbol)

        composite_score = (
            momentum["score"] * self.WEIGHT_MOMENTUM +
            macro["score"] * self.WEIGHT_MACRO +
            news["score"] * self.WEIGHT_NEWS
        )
        composite_score = round(composite_score, 3)

        if composite_score >= 0.55:
            decision = "PROCEED"
        elif composite_score >= 0.40:
            decision = "CAUTION"
        else:
            decision = "BLOCK"

        # Determine strategy hint
        if momentum["above_ema200"] and momentum["rsi"] <= 45:
            strategy_hint = "CSP_PULLBACK_BUY"
        elif momentum["rsi"] > 65:
            strategy_hint = "CC_COVERED_CALL"
        else:
            strategy_hint = "NEUTRAL_WHEEL"

        return {
            "symbol": symbol,
            "composite_score": composite_score,
            "decision": decision,
            "strategy_hint": strategy_hint,
            "layers": {
                "momentum": momentum,
                "macro": macro,
                "news": news,
            },
        }
