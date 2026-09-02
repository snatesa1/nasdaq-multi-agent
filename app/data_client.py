"""
Unified data client for FMP, Alpaca (OHLCV), and yfinance (deep history).
"""

import os
import contextlib
import io
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Suppress yfinance internal logging to keep console logs completely clean
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

@contextlib.contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull to suppress verbose yfinance outputs."""
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            try:
                yield
            except Exception:
                pass

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


class AlpacaOHLCVClient:
    """Lightweight Alpaca client — only for price data (OHLCV)."""

    def __init__(self):
        try:
            if settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY:
                self.client = StockHistoricalDataClient(
                    api_key=settings.ALPACA_API_KEY,
                    secret_key=settings.ALPACA_SECRET_KEY,
                )
            else:
                self.client = None
        except Exception as e:
            logger.warning(f"Alpaca client initialization offline: {e}")
            self.client = None

    def get_ohlcv(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Fetch daily OHLCV bars for a single symbol over the last N days directly from the Google Sheet."""
        end = datetime.now()
        start = end - timedelta(days=days)
        
        # Fetch from Google Sheets
        df_sheet = self.get_google_sheets_market_data([symbol], start, end)
        if not df_sheet.empty and symbol in df_sheet.columns:
            df_res = df_sheet[[symbol]].rename(columns={symbol: 'close'})
            logger.info(f"✅ Google Sheets get_ohlcv: fetched {len(df_res)} rows for {symbol}")
            return df_res
            
        logger.warning(f"⚠️ Google Sheets did not have data for {symbol} — returning empty DataFrame")
        return pd.DataFrame()

    def get_cached_tickers(self) -> List[str]:
        """Reads and returns the list of tickers cached in the Google Sheet."""
        import json
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_data_config.json")
            if not os.path.exists(config_path):
                return []
                
            with open(config_path, "r") as f:
                config = json.load(f)
            spreadsheet_id = config.get("spreadsheet_id")
            if not spreadsheet_id:
                return []
                
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
            df_raw = pd.read_csv(url, nrows=1)
            total_cols = len(df_raw.columns)
            tickers = []
            for i in range(0, total_cols, 2):
                if i + 1 >= total_cols:
                    break
                ticker = str(df_raw.columns[i]).strip()
                if ticker and not ticker.startswith("Unnamed"):
                    tickers.append(ticker)
            return tickers
        except Exception as e:
            logger.error(f"❌ Failed to get cached tickers: {e}")
            return []

    def get_google_sheets_market_data(self, symbols: List[str], start: datetime, end: datetime) -> pd.DataFrame:
        """Reads 10-year historical market data from the Google Sheet CSV export."""
        import json
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_data_config.json")
            if not os.path.exists(config_path):
                return pd.DataFrame()
                
            with open(config_path, "r") as f:
                config = json.load(f)
            spreadsheet_id = config.get("spreadsheet_id")
            if not spreadsheet_id:
                return pd.DataFrame()
                
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
            df_raw = pd.read_csv(url)
            
            total_cols = len(df_raw.columns)
            all_series = {}
            for i in range(0, total_cols, 2):
                if i + 1 >= total_cols:
                    break
                ticker = str(df_raw.columns[i]).strip()
                if ticker in symbols:
                    date_series = df_raw.iloc[1:, i]
                    price_series = df_raw.iloc[1:, i + 1]
                    
                    temp_df = pd.DataFrame({"date": date_series, "close": price_series})
                    temp_df = temp_df.dropna()
                    temp_df["date"] = pd.to_datetime(temp_df["date"], errors="coerce")
                    temp_df["close"] = pd.to_numeric(temp_df["close"], errors="coerce")
                    temp_df = temp_df.dropna()
                    
                    if not temp_df.empty:
                        series = pd.Series(temp_df["close"].values, index=temp_df["date"])
                        if series.index.tz is not None:
                            series.index = series.index.tz_localize(None)
                        series = series.loc[pd.to_datetime(start).tz_localize(None):pd.to_datetime(end).tz_localize(None)]
                        all_series[ticker] = series
                        
            if all_series:
                df_res = pd.DataFrame(all_series)
                logger.info(f"✅ Loaded {len(df_res)} rows for {len(all_series)} symbols from Google Sheets")
                return df_res
        except Exception as e:
            logger.error(f"❌ Failed to fetch market data from Google Sheet: {e}")
            
        return pd.DataFrame()

    def get_historical_batch(self, symbols: List[str], start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch historical daily OHLCV bars from Google Sheets for a batch of symbols."""
        df_sheet = self.get_google_sheets_market_data(symbols, start, end)
        if not df_sheet.empty:
            df_stacked = df_sheet.stack().to_frame(name='close')
            df_stacked.index.names = ['timestamp', 'symbol']
            df_stacked = df_stacked.reorder_levels(['symbol', 'timestamp'])
            return df_stacked
        logger.warning(f"⚠️ Google Sheets did not have batch data for {symbols[:5]}... — returning empty DataFrame")
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

            # Fetch from Google Sheets exclusively
            df_prices = self.get_google_sheets_market_data(symbols, start, end)

            if not df_prices.empty:
                # Normalize each stock to 100 at start to avoid scale/price bias and missing data discontinuities
                df_normalized = df_prices.copy()
                for col in df_normalized.columns:
                    col_series = df_normalized[col].dropna()
                    if not col_series.empty:
                        first_valid_val = col_series.iloc[0]
                        if first_valid_val > 0:
                            df_normalized[col] = (df_normalized[col] / first_valid_val) * 100
                
                # Calculate equally-weighted index series
                daily_series = df_normalized.mean(axis=1)
                if not daily_series.empty:
                    first_val = daily_series.dropna().iloc[0]
                    last_val = daily_series.dropna().iloc[-1]
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
        self, sector: str, start: datetime, end: datetime, top_n: int = 10, selection_criteria: str = "momentum"
    ) -> pd.Series:
        """
        Constructs a price-weighted index daily series for a sector over a date range.
        Uses static cache from data/historical_cache.parquet for historical data,
        and fetches delta for recent days dynamically using top momentum or market cap stocks.
        """
        today = datetime.now()
        if end >= today:
            end = today - timedelta(days=1)

        import os
        cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical_cache.parquet")
        
        df_cache = pd.DataFrame()
        if os.path.exists(cache_path):
            try:
                df_cache = pd.read_parquet(cache_path)
            except Exception as e:
                logger.warning(f"Failed to load historical cache: {e}")

        cached_series = pd.Series(dtype=float)
        last_cached_date = None
        
        if not df_cache.empty and sector in df_cache.columns:
            cached_series = df_cache[sector].dropna()
            cached_series.index = pd.to_datetime(cached_series.index)
            if cached_series.index.tz is not None:
                cached_series.index = cached_series.index.tz_localize(None)
            if not cached_series.empty:
                last_cached_date = cached_series.index.max()

        delta_start = start
        if last_cached_date is not None and start <= last_cached_date:
            delta_start = last_cached_date + timedelta(days=1)

        # If we need delta data, fetch it dynamically
        delta_series = pd.Series(dtype=float)
        if delta_start <= end:
            screener = NasdaqScreenerClient()
            df_screener = screener.load_data()
            if not df_screener.empty:
                df_sec = df_screener[df_screener["sector"] == sector].dropna(subset=["symbol"])
                df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != '']
                df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != 'nan']
                
                if not df_sec.empty:
                    df_sec = df_sec.copy()
                    df_sec["volume"] = pd.to_numeric(df_sec["volume"], errors="coerce").fillna(0)
                    df_sec["marketCap"] = pd.to_numeric(df_sec["marketCap"], errors="coerce").fillna(0)
                    
                    df_sec = df_sec[df_sec["symbol"].astype(str).str.len() <= 4]
                    df_sec = df_sec[df_sec["symbol"].astype(str).str.isalpha()]
                    df_sec = df_sec[df_sec["volume"] > 10000]
                    df_sec = df_sec[df_sec["marketCap"] > 50000000]
            
                    if "pctchange" in df_sec.columns:
                        df_sec["pctchange"] = df_sec["pctchange"].astype(str).str.replace("%", "").str.replace("$", "")
                        df_sec["pctchange"] = pd.to_numeric(df_sec["pctchange"], errors="coerce")
                        df_sec = df_sec.dropna(subset=["pctchange"])
                        
                        if selection_criteria == "market_cap":
                            df_sec = df_sec.sort_values(by="marketCap", ascending=False)
                        else:
                            # TOP MOMENTUM: Select > 10%, otherwise top 10
                            df_momentum = df_sec[df_sec["pctchange"] > 10.0]
                            if len(df_momentum) >= top_n:
                                df_sec = df_momentum.sort_values(by="pctchange", ascending=False)
                            else:
                                df_sec = df_sec.sort_values(by="pctchange", ascending=False)
            
                    symbols = df_sec["symbol"].tolist()[:top_n]
                    if symbols:
                        df_prices = pd.DataFrame()
                        data = self.get_historical_batch(symbols, delta_start, end)
                        if not data.empty and 'close' in data.columns:
                            if isinstance(data.index, pd.MultiIndex):
                                df_prices = data['close'].unstack(level='symbol')
                            else:
                                df_prices = data[['close']]
                                df_prices.columns = [symbols[0]]
            
                        if not df_prices.empty:
                            # Normalize each stock to 100 at start to avoid scale/price bias
                            df_normalized = df_prices.copy()
                            for col in df_normalized.columns:
                                col_series = df_normalized[col].dropna()
                                if not col_series.empty:
                                    first_valid_val = col_series.iloc[0]
                                    if first_valid_val > 0:
                                        df_normalized[col] = (df_normalized[col] / first_valid_val) * 100
                            delta_series = df_normalized.mean(axis=1)

        # Combine cache and delta with smooth re-baselining/chaining to prevent jumps
        if not cached_series.empty and not delta_series.empty:
            # Align timezones
            cached_series.index = pd.to_datetime(cached_series.index)
            if cached_series.index.tz is not None:
                cached_series.index = cached_series.index.tz_localize(None)
            delta_series.index = pd.to_datetime(delta_series.index)
            if delta_series.index.tz is not None:
                delta_series.index = delta_series.index.tz_localize(None)
                
            last_cached_val = cached_series.iloc[-1]
            first_delta_val = delta_series.iloc[0]
            if last_cached_val > 0 and first_delta_val > 0:
                ratio = last_cached_val / first_delta_val
                delta_series = delta_series * ratio

        combined_series = pd.concat([cached_series, delta_series])
        
        # Trim to requested start and end
        if not combined_series.empty:
            combined_series.index = pd.to_datetime(combined_series.index)
            if combined_series.index.tz is not None:
                combined_series.index = combined_series.index.tz_localize(None)
            mask = (combined_series.index.normalize() >= pd.to_datetime(start).normalize()) & (combined_series.index.normalize() <= pd.to_datetime(end).normalize())
            combined_series = combined_series.loc[mask]
            # Ensure unique index in case of overlap
            combined_series = combined_series[~combined_series.index.duplicated(keep='last')]
            
        return combined_series


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
