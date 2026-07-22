import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from .config import settings


logger = logging.getLogger(__name__)

_name_mapping = None
_sector_mapping = None
_screener_rows = None

def _load_screener_data():
    global _name_mapping, _sector_mapping, _screener_rows
    if _screener_rows is not None:
        return
    try:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nasdaq_screener.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = df.dropna(subset=['symbol'])
            df['symbol'] = df['symbol'].str.strip().str.upper()
            _screener_rows = df.set_index('symbol').to_dict('index')
            
            # Populate name and sector maps
            _name_mapping = {sym: row.get('name', '').strip() for sym, row in _screener_rows.items() if isinstance(row.get('name'), str)}
            _sector_mapping = {sym: row.get('sector', '').strip() for sym, row in _screener_rows.items() if isinstance(row.get('sector'), str)}
        else:
            _screener_rows = {}
            _name_mapping = {}
            _sector_mapping = {}
    except Exception as e:
        logger.error(f"Failed to load screener data: {e}")
        _screener_rows = {}
        _name_mapping = {}
        _sector_mapping = {}

def get_name_mapping() -> Dict[str, str]:
    _load_screener_data()
    return _name_mapping

def get_sector_mapping() -> Dict[str, str]:
    _load_screener_data()
    return _sector_mapping

def get_screener_rows() -> Dict[str, Dict[str, Any]]:
    _load_screener_data()
    return _screener_rows

def fetch_alpaca_market_data(symbol: str, days: int = 365) -> Optional[Dict[str, Any]]:
    """
    Fetch historical daily close prices and calculate annualized volatility from Alpaca.
    """
    api_key = settings.ALPACA_API_KEY
    secret_key = settings.ALPACA_SECRET_KEY
    
    if not api_key or not secret_key:
        logger.warning("Alpaca API keys are missing in Secret Manager/Env. Skipping Alpaca.")
        return None
        
    symbol = symbol.strip().upper()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Format dates as RFC3339
    start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end_date.strftime("%Y-%m-%dT00:00:00Z")
    
    # Alpaca standard v2 market data endpoint for stocks
    url = "https://data.alpaca.markets/v2/stocks/bars"
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key,
        "accept": "application/json"
    }
    params = {
        "symbols": symbol,
        "timeframe": "1Day",
        "start": start_str,
        "end": end_str,
        "adjustment": "all"
    }
    
    try:
        logger.info(f"Fetching {symbol} daily bars from Alpaca...")
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code != 200:
            logger.warning(f"Alpaca API returned status {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        bars = data.get("bars", {}).get(symbol, [])
        if not bars:
            logger.warning(f"No Alpaca historical data found for {symbol}")
            return None
            
        close_prices = [float(bar["c"]) for bar in bars]
        dates = [bar["t"].split("T")[0] for bar in bars]
        
        if len(close_prices) < 2:
            return None
            
        current_price = float(close_prices[-1])
        high = float(bars[-1].get("h", current_price))
        low = float(bars[-1].get("l", current_price))
        volume = int(bars[-1].get("v", 0))
        
        # Daily percent change
        change = 0.0
        if len(close_prices) >= 2:
            change = float(((close_prices[-1] - close_prices[-2]) / close_prices[-2]) * 100)
            
        name = get_name_mapping().get(symbol, symbol)
        
        # Calculate daily log returns
        log_returns = np.log(np.array(close_prices[1:]) / np.array(close_prices[:-1]))
        annualized_vol = float(np.std(log_returns) * np.sqrt(252))
        annualized_drift = float(np.mean(log_returns) * 252)
        
        logger.info(f"Successfully fetched {symbol} from Alpaca. Volatility: {annualized_vol:.4f}")
        return {
            "symbol": symbol,
            "name": name,
            "current_price": current_price,
            "change": change,
            "high": high,
            "low": low,
            "volume": volume,
            "historical_volatility": annualized_vol,
            "drift": annualized_drift,
            "prices": close_prices,
            "dates": dates,
            "is_simulated": False
        }
    except Exception as e:
        logger.error(f"Alpaca fetch failed for {symbol}: {e}")
        return None

def fetch_market_data(symbol: str, days: int = 365) -> Dict[str, Any]:
    """
    Fetch historical close prices and calculate annualized volatility.
    Tries Alpaca first, falls back to yfinance, and finally simulated/cache data.
    """
    symbol_upper = symbol.strip().upper()
    
    # 1. Try Alpaca first (uses secure keys, bypassed from GCP blocking)
    alpaca_data = fetch_alpaca_market_data(symbol_upper, days)
    if alpaca_data is not None:
        return alpaca_data
        
    # 2. Fallback to yfinance (public endpoint, might be blocked on Cloud Run)
    try:
        logger.info(f"Trying yfinance fallback for {symbol_upper}...")
        ticker = yf.Ticker(symbol_upper)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        
        if not df.empty:
            close_prices = df["Close"].dropna().tolist()
            dates = df.index.strftime("%Y-%m-%d").tolist()
            
            if len(close_prices) >= 2:
                current_price = float(close_prices[-1])
                high = float(df["High"].iloc[-1])
                low = float(df["Low"].iloc[-1])
                volume = int(df["Volume"].iloc[-1])
                change = float(((close_prices[-1] - close_prices[-2]) / close_prices[-2]) * 100)
                name = get_name_mapping().get(symbol_upper, symbol_upper)
                
                log_returns = np.log(np.array(close_prices[1:]) / np.array(close_prices[:-1]))
                annualized_vol = float(np.std(log_returns) * np.sqrt(252))
                annualized_drift = float(np.mean(log_returns) * 252)
                
                return {
                    "symbol": symbol_upper,
                    "name": name,
                    "current_price": current_price,
                    "change": change,
                    "high": high,
                    "low": low,
                    "volume": volume,
                    "historical_volatility": annualized_vol,
                    "drift": annualized_drift,
                    "prices": close_prices,
                    "dates": dates,
                    "is_simulated": False
                }
    except Exception as e:
        logger.error(f"Error fetching yfinance fallback for {symbol_upper}: {e}")
        
    # 3. Fallback to Nasdaq 10-year historical cache parquet if available
    try:
        cache_data = fetch_cache_fallback(symbol_upper)
        if cache_data is not None:
            logger.info(f"Using Nasdaq 10-year cache fallback for {symbol_upper}")
            return cache_data
    except Exception as e:
        logger.error(f"Error reading 10-year cache fallback for {symbol_upper}: {e}")

    # 4. Fallback to simulated data if all else fails
    logger.warning(f"Using simulated fallback data for {symbol_upper}")
    return get_simulated_market_data(symbol_upper)

def fetch_cache_fallback(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch historical prices from the 10-year sector cache parquet file.
    """
    sector = get_sector_mapping().get(symbol)
    if not sector:
        return None
        
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "historical_cache.parquet")
    if not os.path.exists(cache_path):
        return None
        
    df_cache = pd.read_parquet(cache_path)
    if sector not in df_cache.columns:
        return None
        
    series = df_cache[sector].dropna()
    if series.empty:
        return None
        
    prices = series.tolist()
    dates = [str(d).split(" ")[0] for d in series.index]
    
    # Get details from screener if available
    screener_row = get_screener_rows().get(symbol, {})
    
    def safe_float(val):
        if val is None:
            return None
        try:
            return float(str(val).replace("$", "").replace("%", "").replace(",", "").strip())
        except (ValueError, TypeError):
            return None
            
    # Scale prices to match the last sale price of the ticker
    last_sale = safe_float(screener_row.get("lastsale"))
    if last_sale is not None and last_sale > 0 and prices:
        scale_factor = last_sale / prices[-1]
        prices = [p * scale_factor for p in prices]
        
    current_price = float(prices[-1]) if prices else 100.0
    
    # Calculate daily percent change
    change = 0.0
    if len(prices) >= 2:
        change = float(((prices[-1] - prices[-2]) / prices[-2]) * 100)
    elif "pctchange" in screener_row:
        change = safe_float(screener_row.get("pctchange")) or 0.0
        
    high = current_price
    low = current_price
    volume = int(screener_row.get("volume") or 0)
    name = screener_row.get("name") or symbol
    
    log_returns = np.log(np.array(prices[1:]) / np.array(prices[:-1]))
    annualized_vol = float(np.std(log_returns) * np.sqrt(252)) if len(log_returns) > 0 else 0.25
    annualized_drift = float(np.mean(log_returns) * 252) if len(log_returns) > 0 else 0.05
    
    return {
        "symbol": symbol,
        "name": name,
        "current_price": current_price,
        "change": change,
        "high": high,
        "low": low,
        "volume": volume,
        "historical_volatility": annualized_vol,
        "drift": annualized_drift,
        "prices": prices,
        "dates": dates,
        "is_simulated": False
    }

def get_simulated_market_data(symbol: str) -> Dict[str, Any]:
    """
    Generate fallback simulated data if ticker lookup fails.
    """
    symbol_upper = symbol.upper()
    
    # Check if we have screener info to make it more realistic
    screener_row = get_screener_rows().get(symbol_upper, {})
    
    def safe_float(val):
        if val is None:
            return None
        try:
            return float(str(val).replace("$", "").replace("%", "").replace(",", "").strip())
        except (ValueError, TypeError):
            return None
            
    name = screener_row.get("name") or symbol_upper
    
    # Provide realistic defaults for popular tickers
    defaults = {
        "AAPL": (220.0, 0.22, 0.08),
        "TSLA": (180.0, 0.48, 0.12),
        "NVDA": (120.0, 0.42, 0.25),
        "PANW": (315.0, 0.30, 0.15),
        "MSFT": (420.0, 0.18, 0.07),
        "BTC": (65000.0, 0.55, 0.20)
    }
    
    last_sale_price = safe_float(screener_row.get("lastsale"))
    if last_sale_price is not None and last_sale_price > 0:
        S0 = last_sale_price
        vol = 0.25
        drift = 0.05
    else:
        S0, vol, drift = defaults.get(symbol_upper, (100.0, 0.25, 0.05))
    
    # Generate 100 simulated daily prices using GBM
    dt = 1/252.0
    prices = [S0]
    dates = [(datetime.now() - timedelta(days=100-i)).strftime("%Y-%m-%d") for i in range(100)]
    
    for _ in range(99):
        # simple random walk
        next_price = prices[-1] * np.exp((drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * np.random.standard_normal())
        prices.append(float(next_price))
        
    change = float(screener_row.get("pctchange") or 0.0)
    if change == 0.0 and len(prices) >= 2:
        change = float(((prices[-1] - prices[-2]) / prices[-2]) * 100)
        
    volume = int(screener_row.get("volume") or 10000)
    
    return {
        "symbol": symbol_upper,
        "name": name,
        "current_price": float(prices[-1]),
        "change": change,
        "high": float(max(prices[-5:])),
        "low": float(min(prices[-5:])),
        "volume": volume,
        "historical_volatility": vol,
        "drift": drift,
        "prices": prices,
        "dates": dates,
        "is_simulated": True
    }
