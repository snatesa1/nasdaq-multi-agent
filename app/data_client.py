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

    # ── Index Constituents ──────────────────────────────
    def get_sp500_constituents(self) -> List[Dict]:
        """Fetch list of S&P 500 stocks."""
        return self._get("sp500_constituent")

    def get_nasdaq_constituents(self) -> List[Dict]:
        """Fetch list of NASDAQ 100 stocks."""
        return self._get("nasdaq_constituent")


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

    def get_historical_batch(self, symbols: List[str], start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch historical daily OHLCV bars from Alpaca for a batch of symbols, with yfinance fallback."""
        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
            )
            bars = self.client.get_stock_bars(request)
            df = bars.df
            logger.info(f"✅ Alpaca historical batch: fetched {len(df)} rows for {len(symbols)} symbols")
            return df
        except Exception as e:
            logger.warning(f"⚠️ Alpaca batch fetch failed for {symbols[:5]}...: {e}. Falling back to yfinance...")
            try:
                df_yf = yf.download(
                    symbols,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    progress=False
                )
                if not df_yf.empty:
                    # Extract Close prices
                    close_cols = [c for c in df_yf.columns if isinstance(c, tuple) and len(c) > 1 and c[0] == 'Close']
                    if close_cols:
                        df_close = df_yf[close_cols]
                        df_close.columns = [c[1] for c in df_close.columns]
                    elif 'Close' in df_yf.columns:
                        df_close = df_yf[['Close']]
                        df_close.columns = [symbols[0]]
                    else:
                        df_close = df_yf

                    # Stacking to match Alpaca's MultiIndex [symbol, timestamp] structure
                    df_stacked = df_close.stack().to_frame(name='close')
                    df_stacked.index.names = ['timestamp', 'symbol']
                    df_stacked = df_stacked.reorder_levels(['symbol', 'timestamp'])
                    logger.info(f"✅ yfinance fallback batch: downloaded and formatted {len(df_stacked)} rows for {len(symbols)} symbols")
                    return df_stacked
            except Exception as yfe:
                logger.error(f"❌ yfinance fallback batch also failed: {yfe}")
            return pd.DataFrame()

    def get_sliding_window(
        self, symbol_or_symbols: Any, window_days: int = 30, years: List[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch sliding windows for comparison, either for a single symbol or a list of symbols (index).
        Calculates logarithmic returns. Exposes unified logic to all sub-agents.
        """
        import math
        if years is None:
            years = [2016, 2018, 2020, 2022, 2023, 2024, 2025, 2026]

        today = datetime.now()
        month, day = today.month, today.day
        results = {}

        is_list = isinstance(symbol_or_symbols, list)
        symbols = symbol_or_symbols if is_list else [symbol_or_symbols]
        symbols = [s for s in symbols if isinstance(s, str) and s.strip() and s != 'nan']

        for year in years:
            start = datetime(year, month, day) - timedelta(days=window_days)
            end = datetime(year, month, day)
            if end >= today:
                end = today - timedelta(days=1)

            # Determine whether to use Alpaca or yfinance fallback
            df_prices = pd.DataFrame()
            if year < 2016:
                # yfinance fallback
                try:
                    df_prices = yf.download(
                        symbols,
                        start=start.strftime("%Y-%m-%d"),
                        end=end.strftime("%Y-%m-%d"),
                        progress=False
                    )
                    if not df_prices.empty:
                        # Extract Close
                        close_cols = [c for c in df_prices.columns if isinstance(c, tuple) and len(c) > 1 and c[0] == 'Close']
                        if close_cols:
                            df_prices = df_prices[close_cols]
                            df_prices.columns = [c[1] for c in df_prices.columns]
                        elif 'Close' in df_prices.columns:
                            df_prices = df_prices[['Close']]
                except Exception as e:
                    logger.warning(f"⚠️ yfinance fallback failed for year {year}: {e}")
            else:
                # Alpaca query
                df_alp = self.get_historical_batch(symbols, start, end)
                if not df_alp.empty and 'close' in df_alp.columns:
                    if isinstance(df_alp.index, pd.MultiIndex):
                        df_prices = df_alp['close'].unstack(level='symbol')
                    else:
                        df_prices = df_alp[['close']]
                        if not is_list:
                            df_prices.columns = [symbols[0]]

            if not df_prices.empty:
                # Calculate daily average (price-weighted index or stock price)
                daily_series = df_prices.mean(axis=1)
                if not daily_series.empty:
                    first_val = daily_series.iloc[0]
                    last_val = daily_series.iloc[-1]
                    if first_val > 0 and last_val > 0:
                        # Calculate logarithmic return
                        log_ret = math.log(last_val / first_val) * 100
                        indexed_series = (daily_series / first_val) * 100
                        results[str(year)] = {
                            "return_pct": round(log_ret, 2),
                            "start_indexed": round(indexed_series.iloc[0], 2),
                            "end_indexed": round(indexed_series.iloc[-1], 2),
                            "data_points": len(indexed_series),
                        }
                        logger.info(f"📊 Sliding window {year}: indexed from {first_val:.2f} to {last_val:.2f}, log_return={log_ret:.2f}%")
        return results

    def get_sector_index_series(
        self, sector: str, start: datetime, end: datetime, top_n: int = 100
    ) -> pd.Series:
        """
        Constructs a price-weighted index daily series for a sector over a date range.
        Uses Alpaca for >= 2016 and yfinance for < 2016.
        """
        today = datetime.now()
        if end >= today:
            end = today - timedelta(days=1)

        screener = NasdaqScreenerClient()
        df_screener = screener.load_data()
        if df_screener.empty:
            return pd.Series()

        # Filter by sector
        df_sec = df_screener[df_screener["sector"] == sector].dropna(subset=["symbol"])
        df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != '']
        df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != 'nan']
        if df_sec.empty:
            return pd.Series()

        # Clean and filter for active, liquid major common stocks
        df_sec = df_sec.copy()
        df_sec["volume"] = pd.to_numeric(df_sec["volume"], errors="coerce").fillna(0)
        df_sec["marketCap"] = pd.to_numeric(df_sec["marketCap"], errors="coerce").fillna(0)
        
        # Apply strict standard common stock filters to prevent Alpaca SIP errors
        df_sec = df_sec[df_sec["symbol"].astype(str).str.len() <= 4]
        df_sec = df_sec[df_sec["symbol"].astype(str).str.isalpha()]
        df_sec = df_sec[df_sec["volume"] > 10000]
        df_sec = df_sec[df_sec["marketCap"] > 50000000]

        # Clean and sort by daily pctchange (highest momentum leaders first)
        if "pctchange" in df_sec.columns:
            df_sec["pctchange"] = df_sec["pctchange"].astype(str).str.replace("%", "").str.replace("$", "")
            df_sec["pctchange"] = pd.to_numeric(df_sec["pctchange"], errors="coerce")
            df_sec = df_sec.dropna(subset=["pctchange"])
            df_sec = df_sec.sort_values(by="pctchange", ascending=False)

        symbols = df_sec["symbol"].tolist()[:top_n]
        if not symbols:
            return pd.Series()

        # Batch download daily Close prices
        df_prices = pd.DataFrame()
        if start.year < 2016:
            # yfinance fallback
            try:
                data = yf.download(
                    symbols,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    progress=False
                )
                if not data.empty:
                    close_cols = [c for c in data.columns if isinstance(c, tuple) and len(c) > 1 and c[0] == 'Close']
                    if close_cols:
                        df_prices = data[close_cols]
                        df_prices.columns = [c[1] for c in df_prices.columns]
                    elif 'Close' in data.columns:
                        df_prices = data[['Close']]
            except Exception as e:
                logger.error(f"❌ yfinance fallback batch fetch failed for sector {sector}: {e}")
        else:
            # Alpaca
            data = self.get_historical_batch(symbols, start, end)
            if not data.empty and 'close' in data.columns:
                if isinstance(data.index, pd.MultiIndex):
                    df_prices = data['close'].unstack(level='symbol')
                else:
                    df_prices = data[['close']]
                    df_prices.columns = [symbols[0]]

        if df_prices.empty:
            return pd.Series()

        # Calculate daily price-weighted average index
        daily_index = df_prices.mean(axis=1)
        return daily_index


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
            years = [1999, 2001, 2003, 2008, 2011, 2016, 2018, 2024, 2025, 2026]

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
        return results


# ═══════════════════════════════════════════════════════════
#  NASDAQ Screener Client — Static Universe & Filtering
# ═══════════════════════════════════════════════════════════
import os

class NasdaqScreenerClient:
    """Client for reading and filtering the static NASDAQ screener CSV."""

    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Default to data/nasdaq_screener.csv relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, "data", "nasdaq_screener.csv")
        self.csv_path = csv_path
        self._df = None

    def load_data(self) -> pd.DataFrame:
        if self._df is None:
            if not os.path.exists(self.csv_path):
                logger.warning(f"⚠️ Screener CSV not found at {self.csv_path}")
                return pd.DataFrame()
            try:
                df = pd.read_csv(self.csv_path)
                
                # Clean up column data types
                if "lastsale" in df.columns:
                    df["lastsale"] = df["lastsale"].astype(str).str.replace("$", "", regex=False).astype(float)
                if "pctchange" in df.columns:
                    df["pctchange"] = df["pctchange"].astype(str).str.replace("%", "", regex=False).astype(float)
                
                self._df = df
                logger.info(f"✅ Loaded {len(df)} tickers from NASDAQ screener CSV")
            except Exception as e:
                logger.error(f"❌ Failed to load screener CSV: {e}")
                return pd.DataFrame()
        return self._df

    def get_screener_universe(self, allowed_countries: List[str] = ["United States"]) -> pd.DataFrame:
        """Get the base universe, optionally filtered by country."""
        df = self.load_data()
        if df.empty:
            return df
            
        if allowed_countries:
            df = df[df["country"].isin(allowed_countries)]
        return df

    def get_stocks_by_sector(self) -> Dict[str, List[str]]:
        """Group symbols by sector, returning a mapping of Sector -> [Symbols]."""
        df = self.get_screener_universe()
        if df.empty:
            return {}
        
        # Drop rows where sector is NaN or empty
        df_sector = df.dropna(subset=["sector"])
        grouped = df_sector.groupby("sector")["symbol"].apply(list).to_dict()
        return grouped

    def filter_universe(
        self,
        min_market_cap: Optional[float] = None,
        min_net_change: Optional[float] = None,
        min_pct_change: Optional[float] = None,
    ) -> pd.DataFrame:
        """Helper to filter the universe by fundamental/price metrics."""
        df = self.get_screener_universe()
        if df.empty:
            return df
            
        if min_market_cap is not None:
            df = df[df["marketCap"] >= min_market_cap]
        if min_net_change is not None:
            df = df[df["netchange"] >= min_net_change]
        if min_pct_change is not None:
            df = df[df["pctchange"] >= min_pct_change]
            
        return df

    def get_display_columns(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """Returns only the requested display columns: Symbol, Name, Last Sale, Net Change, % Change, Market Cap."""
        if df is None:
            df = self.get_screener_universe()
        
        # Mapping existing columns to requested display names
        cols_map = {
            "symbol": "Symbol",
            "name": "Name",
            "lastsale": "Last Sale",
            "netchange": "Net Change",
            "pctchange": "% Change",
            "marketCap": "Market Cap"
        }
        available_cols = [c for c in cols_map.keys() if c in df.columns]
        display_df = df[available_cols].rename(columns=cols_map)
        return display_df
