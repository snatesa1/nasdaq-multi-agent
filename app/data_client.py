"""
Unified data client for FMP, Alpaca (OHLCV), and yfinance (deep history).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from .config import settings

logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"


# ═══════════════════════════════════════════════════════════
#  FMP Client — Sectors, Fundamentals, News, Economics
# ═══════════════════════════════════════════════════════════
class FMPClient:
    """Financial Modeling Prep API client."""

    def __init__(self):
        self.api_key = settings.FMP_API_KEY

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> any:
        """Generic FMP GET request with API key injection."""
        params = params or {}
        params["apikey"] = self.api_key
        url = f"{FMP_BASE}/{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"❌ FMP request failed [{endpoint}]: {e}")
            return []

    # ── Sector / Industry ────────────────────────────────
    def get_sector_performance(self, date: Optional[str] = None) -> List[Dict]:
        """Sector performance snapshot. date format: YYYY-MM-DD."""
        params = {"date": date} if date else {}
        return self._get("sector-performance-snapshot", params)

    def get_industry_performance(self, date: Optional[str] = None) -> List[Dict]:
        """Industry-level performance snapshot."""
        params = {"date": date} if date else {}
        return self._get("industry-performance-snapshot", params)

    def get_historical_sector_performance(self, sector: str) -> List[Dict]:
        """Historical performance for a specific sector."""
        return self._get("historical-sector-performance", {"sector": sector})

    def get_sector_pe(self, date: Optional[str] = None) -> List[Dict]:
        """Sector P/E ratio snapshot."""
        params = {"date": date} if date else {}
        return self._get("sector-pe-snapshot", params)

    # ── Stock News ───────────────────────────────────────
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Fetch stock-specific news articles."""
        return self._get("news/stock", {"symbols": symbol, "limit": limit})

    def get_general_news(self, limit: int = 20) -> List[Dict]:
        """Fetch general market/financial news."""
        return self._get("news/general-latest", {"limit": limit})

    # ── Fundamentals ─────────────────────────────────────
    def get_financial_ratios(self, symbol: str) -> List[Dict]:
        """ROE, ROA, margins, current ratio, etc."""
        return self._get("ratios", {"symbol": symbol})

    def get_key_metrics(self, symbol: str) -> List[Dict]:
        """P/E, P/B, EV/EBITDA, FCF yield, etc."""
        return self._get("key-metrics", {"symbol": symbol})

    def get_financial_scores(self, symbol: str) -> List[Dict]:
        """Altman Z-Score, Piotroski Score."""
        return self._get("financial-scores", {"symbol": symbol})

    def get_income_statement(self, symbol: str) -> List[Dict]:
        """Revenue, net income, margins."""
        return self._get("income-statement", {"symbol": symbol})

    def get_cash_flow(self, symbol: str) -> List[Dict]:
        """FCF, capex patterns."""
        return self._get("cash-flow-statement", {"symbol": symbol})

    # ── Economics ─────────────────────────────────────────
    def get_economic_indicator(self, name: str) -> List[Dict]:
        """Fetch economic indicator data (GDP, CPI, unemployment, etc)."""
        return self._get("economic-indicators", {"name": name})

    def get_treasury_rates(self) -> List[Dict]:
        """Latest and historical treasury rates."""
        return self._get("treasury-rates")

    # ── Technical Indicators (server-side) ───────────────
    def get_technical_indicator(
        self, symbol: str, indicator: str, period: int = 14, timeframe: str = "1day"
    ) -> List[Dict]:
        """Fetch FMP-computed technical indicators (rsi, adx, ema, etc)."""
        return self._get(
            f"technical-indicators/{indicator}",
            {"symbol": symbol, "periodLength": period, "timeframe": timeframe},
        )


# ═══════════════════════════════════════════════════════════
#  Alpaca Client — OHLCV Price Data
# ═══════════════════════════════════════════════════════════
class AlpacaOHLCVClient:
    """Lightweight Alpaca client — only for price data (OHLCV)."""

    def __init__(self):
        self.client = StockHistoricalDataClient(
            api_key=settings.ALPACA_API_KEY,
            secret_key=settings.ALPACA_SECRET_KEY,
        )

    def get_ohlcv(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Fetch daily OHLCV bars from Alpaca."""
        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=days),
            )
            bars = self.client.get_stock_bars(request)
            df = bars.df
            if isinstance(df.index, pd.MultiIndex):
                df = df.xs(symbol)
            logger.info(f"✅ Alpaca OHLCV: {symbol} — {len(df)} bars")
            return df
        except Exception as e:
            logger.error(f"❌ Alpaca OHLCV fetch failed for {symbol}: {e}")
            return pd.DataFrame()


# ═══════════════════════════════════════════════════════════
#  yfinance Client — Deep Historical Data (1999+)
# ═══════════════════════════════════════════════════════════
class YFinanceClient:
    """yfinance for deep historical data going back to 1999, 2008, etc."""

    @staticmethod
    def get_historical(
        symbol: str, start: str, end: str
    ) -> pd.DataFrame:
        """
        Fetch historical data for a symbol between dates.
        Args:
            symbol: Ticker (e.g. 'XLK', 'QQQ', 'AAPL')
            start: 'YYYY-MM-DD'
            end: 'YYYY-MM-DD'
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)
            if df.empty:
                logger.warning(f"⚠️ yfinance returned no data for {symbol} [{start} → {end}]")
            else:
                logger.info(f"✅ yfinance: {symbol} — {len(df)} bars [{start} → {end}]")
            return df
        except Exception as e:
            logger.error(f"❌ yfinance fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_sliding_window(
        symbol: str, window_days: int = 30, years: List[int] = None
    ) -> Dict[int, pd.DataFrame]:
        """
        Fetch the same calendar window across multiple years for comparison.
        Indexes each window to 100 at start (FRED blog pattern).

        Returns:
            Dict mapping year → DataFrame with 'indexed_close' column.
        """
        if years is None:
            years = [1999, 2008, 2024, 2025, 2026]

        today = datetime.now()
        month, day = today.month, today.day
        results = {}

        for year in years:
            start = datetime(year, month, day) - timedelta(days=window_days)
            end = datetime(year, month, day)
            # For current/future year, cap at today
            if end > today:
                end = today

            df = YFinanceClient.get_historical(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
            if not df.empty and "Close" in df.columns:
                # Index to 100 at start of window
                first_close = df["Close"].iloc[0]
                df["indexed_close"] = (df["Close"] / first_close) * 100
                results[year] = df
                logger.info(f"📊 Sliding window {year}: {symbol} indexed from {first_close:.2f}")
            else:
                logger.warning(f"⚠️ No data for {symbol} in {year} window")

        return results
