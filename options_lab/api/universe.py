import os
import logging
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Set, Optional
import yfinance as yf

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SP500_PATH = os.path.join(DATA_DIR, "sp500_constituents.csv")
NASDAQ_PATH = os.path.join(DATA_DIR, "nasdaq_screener.csv")

def load_sp500_constituents(force_refresh: bool = False) -> List[str]:
    """
    Fetch S&P 500 constituents from Wikipedia, cache it locally, and return the list of tickers.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if os.path.exists(SP500_PATH) and not force_refresh:
        try:
            df = pd.read_csv(SP500_PATH)
            if not df.empty and "symbol" in df.columns:
                symbols = df["symbol"].str.strip().str.upper().tolist()
                logger.info(f"Loaded {len(symbols)} S&P 500 tickers from cache.")
                return symbols
        except Exception as e:
            logger.error(f"Error reading S&P 500 cache: {e}")
            
    # Scraping Wikipedia
    logger.info("Fetching S&P 500 constituents from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "constituents"})
        
        symbols = []
        names = []
        sectors = []
        
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    ticker = cols[0].text.strip().replace(".", "-") # Replace dot with hyphen (e.g. BRK.B -> BRK-B)
                    name = cols[1].text.strip()
                    sector = cols[3].text.strip()
                    
                    symbols.append(ticker.upper())
                    names.append(name)
                    sectors.append(sector)
            
            df_new = pd.DataFrame({
                "symbol": symbols,
                "name": names,
                "sector": sectors
            })
            df_new.to_csv(SP500_PATH, index=False)
            logger.info(f"Scraped and cached {len(symbols)} S&P 500 tickers successfully.")
            return symbols
        else:
            logger.error("Could not find constituents table in Wikipedia page.")
    except Exception as e:
        logger.error(f"Wikipedia S&P 500 scrape failed: {e}")
        
    # Fallback to a hardcoded minimal list of S&P 500 heavyweights if scraping fails
    fallback_list = ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "BRK-B", "LLY", "JPM", "TSLA", "UNH", "V", "XOM", "AVGO"]
    logger.warning(f"Using S&P 500 fallback list of {len(fallback_list)} symbols.")
    return fallback_list

def load_nasdaq_universe() -> List[str]:
    """
    Read NASDAQ tickers from the local nasdaq_screener.csv file.
    """
    if os.path.exists(NASDAQ_PATH):
        try:
            df = pd.read_csv(NASDAQ_PATH)
            df = df.dropna(subset=["symbol"])
            symbols = df["symbol"].str.strip().str.upper().tolist()
            # Clean symbols (remove rights, warrants, preferreds, etc. if needed)
            cleaned_symbols = [sym for sym in symbols if sym.isalpha() or "-" in sym]
            logger.info(f"Loaded {len(cleaned_symbols)} NASDAQ tickers from screener.")
            return cleaned_symbols
        except Exception as e:
            logger.error(f"Error reading NASDAQ screener: {e}")
    else:
        logger.warning(f"NASDAQ screener not found at {NASDAQ_PATH}")
    return []

def get_combined_universe() -> Set[str]:
    """
    Returns the union of S&P 500 and NASDAQ symbols.
    """
    sp500 = set(load_sp500_constituents())
    nasdaq = set(load_nasdaq_universe())
    return sp500.union(nasdaq)

def calculate_piotroski_score(info: Dict[str, Any]) -> Optional[int]:
    """
    Estimate Piotroski F-Score (0-9) based on yfinance info metrics.
    Returns None if key fields are missing to distinguish from a true 0 score.
    """
    score = 0
    available_fields = 0
    
    # 1. Profitability: Positive net income
    net_income = info.get("netIncomeToCommon") or info.get("netIncome")
    if net_income is not None:
        available_fields += 1
        if float(net_income) > 0:
            score += 1
        
    # 2. Profitability: Positive ROA
    roa = info.get("returnOnAssets")
    if roa is not None:
        available_fields += 1
        if float(roa) > 0:
            score += 1
        
    # 3. Profitability: Positive operating cash flow
    cfo = info.get("operatingCashflow")
    if cfo is not None:
        available_fields += 1
        if float(cfo) > 0:
            score += 1
        
    # 4. Profitability: Quality of earnings (CFO > Net Income)
    if cfo is not None and net_income is not None:
        available_fields += 1
        if float(cfo) > float(net_income):
            score += 1
        
    # 5. Leverage: Decreasing Debt-to-Equity (proxy: current ratio > 1)
    current_ratio = info.get("currentRatio")
    if current_ratio is not None:
        available_fields += 1
        if float(current_ratio) > 1.0:
            score += 1
        
    # 6. Efficiency: Gross margin improving (proxy: grossMargin > 20%)
    gross_margin = info.get("grossMargins")
    if gross_margin is not None:
        available_fields += 1
        if float(gross_margin) > 0.20:
            score += 1
        
    # 7. Efficiency: Asset turnover (proxy: positive return on assets)
    if roa is not None:
        available_fields += 1
        if float(roa) > 0.05:
            score += 1
        
    # 8. Dilution: No dilution (proxy: trailing EPS > 0)
    eps = info.get("trailingEps")
    if eps is not None:
        available_fields += 1
        if float(eps) > 0:
            score += 1
        
    # 9. Growth: Revenue growth (proxy: positive revenue growth)
    rev_growth = info.get("revenueGrowth")
    if rev_growth is not None:
        available_fields += 1
        if float(rev_growth) > 0:
            score += 1
            
    # We require at least 4 fields to return a valid Piotroski score
    if available_fields >= 4:
        # Scale score if some fields were missing to keep it out of 9
        scaled_score = int(round((score / available_fields) * 9))
        return scaled_score
    return None

def calculate_altman_z_score(info: Dict[str, Any]) -> Optional[float]:
    """
    Estimate Altman Z-Score from yfinance info proxies.
    Z = 1.2*WC/TA + 1.4*RE/TA + 3.3*EBIT/TA + 0.6*MC/TL + 1.0*Rev/TA
    Returns None if total assets is not available.
    """
    try:
        total_assets = info.get("totalAssets")
        if not total_assets or float(total_assets) <= 0:
            return None
            
        ta = float(total_assets)
        current_ratio = info.get("currentRatio") or 1.0
        wc_ta = max(0.0, (float(current_ratio) - 1.0) * 0.3)
        
        roe = info.get("returnOnEquity") or 0.0
        re_ta = max(0.0, float(roe) * 0.5)
        
        ebitda = info.get("ebitda") or 0.0
        ebit_ta = float(ebitda) / ta
        
        market_cap = info.get("marketCap") or 1e9
        total_debt = info.get("totalDebt") or 0.0
        td = float(total_debt)
        mc_tl = float(market_cap) / td if td > 0 else 5.0
        
        revenue = info.get("totalRevenue") or 0.0
        rev_ta = float(revenue) / ta
        
        z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mc_tl + 1.0 * rev_ta
        return float(z)
    except Exception:
        return None

def check_fundamental_quality(symbol: str) -> Dict[str, Any]:
    """
    Evaluate if a stock meets our exhaustive fundamental filters.
    Requires passing at least 75% of the available filters to accommodate missing fields.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        
        if not info or info.get("quoteType") is None:
            return {"pass": False, "reason": "No info available"}
            
        # Get metrics
        roe = info.get("returnOnEquity")
        op_margin = info.get("operatingMargins")
        debt_to_equity = info.get("debtToEquity")
        
        piotroski = calculate_piotroski_score(info)
        altman_z = calculate_altman_z_score(info)
        
        # Prepare evaluation checks (True/False/None)
        checks = {}
        
        if piotroski is not None:
            checks["piotroski_score"] = piotroski >= 6
        if roe is not None:
            checks["roe"] = float(roe) >= 0.12
        if op_margin is not None:
            checks["operating_margin"] = float(op_margin) >= 0.10
        if debt_to_equity is not None:
            # yfinance reports debtToEquity in percent (e.g. 150 = 1.5x) or ratio (e.g. 1.5)
            d2e_val = float(debt_to_equity)
            if d2e_val > 10: # likely in percentage format
                checks["debt_to_equity"] = d2e_val <= 150.0
            else:
                checks["debt_to_equity"] = d2e_val <= 1.5
        if altman_z is not None:
            checks["altman_z"] = altman_z >= 1.8
            
        if not checks:
            return {"pass": False, "reason": "No fundamental metrics could be retrieved"}
            
        # Count passes
        total_checks = len(checks)
        passed_checks = sum(1 for v in checks.values() if v)
        pass_ratio = passed_checks / total_checks
        
        # Require 75% pass rate of available checks
        passed = pass_ratio >= 0.75
        
        # Make a readable metrics summary
        summary_metrics = {
            "piotroski_score": piotroski if piotroski is not None else "N/A",
            "altman_z_score": round(altman_z, 2) if altman_z is not None else "N/A",
            "roe": round(float(roe) * 100, 1) if roe is not None else "N/A",
            "operating_margin": round(float(op_margin) * 100, 1) if op_margin is not None else "N/A",
            "debt_to_equity": round(float(debt_to_equity), 1) if debt_to_equity is not None else "N/A"
        }
        
        return {
            "pass": passed,
            "checks": checks,
            "pass_ratio": f"{passed_checks}/{total_checks} ({round(pass_ratio*100)}%)",
            "metrics": summary_metrics
        }
    except Exception as e:
        logger.error(f"Error checking fundamentals for {symbol}: {e}")
        return {"pass": False, "reason": f"Fundamental check error: {str(e)}"}

def screen_52w_low(symbol: str, threshold_pct: float = 0.20) -> Dict[str, Any]:
    """
    Check if a symbol is within threshold_pct (e.g. 20%) of its 52-week low.
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="1y")
        if history.empty:
            return {"pass": False, "reason": "No price history available"}
            
        current_price = float(history["Close"].iloc[-1])
        low_52w = float(history["Low"].min())
        high_52w = float(history["High"].max())
        
        pct_above_low = (current_price - low_52w) / low_52w
        
        is_near_low = pct_above_low <= threshold_pct
        
        return {
            "pass": is_near_low,
            "current_price": round(current_price, 2),
            "low_52w": round(low_52w, 2),
            "high_52w": round(high_52w, 2),
            "pct_above_low": round(pct_above_low * 100, 1)
        }
    except Exception as e:
        logger.error(f"Error screening 52W low for {symbol}: {e}")
        return {"pass": False, "reason": f"52W low screen error: {str(e)}"}
