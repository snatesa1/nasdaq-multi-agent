"""
Fundamental Indexation Engine — Replicating Arnott, Hsu, & Moore (2005)

Calculates Fundamental Weights (W_fund) vs Market Cap Weights (W_cap)
across size metrics (Book Value, Cash Flow, Revenue, Dividends) and computes
Fundamental Alpha Divergence (Delta = W_fund - W_cap) for Options Lab.
"""

import logging
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

def get_default_universe(limit: int = 20) -> List[str]:
    """Dynamically loads default index universe from live S&P 500 constituents."""
    try:
        from .universe import load_sp500_constituents
        constituents = load_sp500_constituents()
        if constituents:
            return constituents[:limit]
    except Exception as e:
        logger.debug(f"Dynamic S&P 500 constituents query failed: {e}")
    return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "JPM", "XOM", "UNH"]

class FundamentalIndexEngine:
    """
    Computes Fundamental Index weights and compares them against market capitalization weights.
    Identifies valuation noise drag and option trading overlay opportunities.
    """

    def fetch_ticker_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch fundamental size metrics for a single ticker via yfinance.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            
            if not info or info.get("marketCap") is None:
                logger.warning(f"Insufficient fundamental info for {symbol}")
                return None
                
            market_cap = float(info.get("marketCap", 0))
            shares = float(info.get("sharesOutstanding", 0)) or 1.0
            
            # 1. Book Value
            book_value_per_share = float(info.get("bookValue", 0) or 0)
            total_book_value = book_value_per_share * shares if book_value_per_share > 0 else float(info.get("totalStockholderEquity", 0) or 0)
            
            # 2. Operating Cash Flow / Income
            operating_cash_flow = float(info.get("operatingCashflow", 0) or 0)
            if operating_cash_flow <= 0:
                # Fallback estimate using operating margin * revenue
                rev = float(info.get("totalRevenue", 0) or 0)
                op_margin = float(info.get("operatingMargins", 0) or 0)
                operating_cash_flow = max(0.0, rev * op_margin)
                
            # 3. Revenue / Sales
            total_revenue = float(info.get("totalRevenue", 0) or 0)
            
            # 4. Gross Dividends
            dividend_rate = float(info.get("dividendRate", 0) or 0)
            total_dividends = dividend_rate * shares
            
            return {
                "symbol": symbol,
                "name": info.get("shortName", symbol),
                "market_cap": market_cap,
                "book_value": max(0.0, total_book_value),
                "cash_flow": max(0.0, operating_cash_flow),
                "revenue": max(0.0, total_revenue),
                "dividends": max(0.0, total_dividends),
                "trailing_pe": info.get("trailingPE"),
                "price_to_book": info.get("priceToBook"),
                "current_price": float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
            }
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            return None

    def compute_index(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compute Cap Weights, Fundamental Weights, and Alpha Deltas for the universe.
        """
        target_symbols = symbols if symbols and len(symbols) > 0 else get_default_universe()
        logger.info(f"Computing Fundamental Index for {len(target_symbols)} symbols...")
        
        data_list = []
        for sym in target_symbols:
            fund = self.fetch_ticker_fundamentals(sym)
            if fund:
                data_list.append(fund)
                
        if not data_list:
            return {"error": "Failed to fetch fundamental data for given universe."}
            
        df = pd.DataFrame(data_list)
        
        # Calculate Market Cap Weights
        total_market_cap = df["market_cap"].sum()
        df["w_cap"] = df["market_cap"] / total_market_cap if total_market_cap > 0 else 0
        
        # Calculate Individual Fundamental Metric Weights
        total_bv = df["book_value"].sum()
        total_cf = df["cash_flow"].sum()
        total_rev = df["revenue"].sum()
        total_div = df["dividends"].sum()
        
        df["w_bv"] = df["book_value"] / total_bv if total_bv > 0 else 0
        df["w_cf"] = df["cash_flow"] / total_cf if total_cf > 0 else 0
        df["w_rev"] = df["revenue"] / total_rev if total_rev > 0 else 0
        df["w_div"] = df["dividends"] / total_div if total_div > 0 else 0
        
        # Composite Fundamental Weight: Equal average across available metrics
        metric_cols = ["w_bv", "w_cf", "w_rev", "w_div"]
        df["w_fund"] = df[metric_cols].mean(axis=1)
        
        # Normalize w_fund so sum(w_fund) == 1.0
        total_w_fund = df["w_fund"].sum()
        if total_w_fund > 0:
            df["w_fund"] = df["w_fund"] / total_w_fund
            
        # Fundamental Alpha Delta = W_fund - W_cap
        df["alpha_delta"] = df["w_fund"] - df["w_cap"]
        df["alpha_delta_pct"] = (df["alpha_delta"] / df["w_cap"]) * 100
        
        # Determine Option Strategy Recommendation based on 80/20 Arnott divergence
        def get_option_recommendation(row):
            delta_pct = row["alpha_delta_pct"]
            if delta_pct > 15.0:
                return "Undervalued (Main Street > Wall St): Sell Cash-Secured Puts / Long LEAP Calls"
            elif delta_pct < -15.0:
                return "Overvalued (Cap Drag): Sell Covered Calls / Buy Downward Protection Puts"
            else:
                return "Fairly Valued: Neutral Delta Options Strategy"
                
        df["option_strategy"] = df.apply(get_option_recommendation, axis=1)
        
        # Sort by fundamental weight descending
        df = df.sort_values(by="w_fund", ascending=False)
        
        results = []
        for idx, row in df.iterrows():
            results.append({
                "symbol": row["symbol"],
                "name": row["name"],
                "market_cap": row["market_cap"],
                "current_price": row["current_price"],
                "w_cap": round(float(row["w_cap"]), 4),
                "w_fund": round(float(row["w_fund"]), 4),
                "alpha_delta": round(float(row["alpha_delta"]), 4),
                "alpha_delta_pct": round(float(row["alpha_delta_pct"]), 2),
                "option_strategy": row["option_strategy"],
                "metrics": {
                    "book_value": row["book_value"],
                    "cash_flow": row["cash_flow"],
                    "revenue": row["revenue"],
                    "dividends": row["dividends"],
                    "trailing_pe": row["trailing_pe"],
                    "price_to_book": row["price_to_book"]
                }
            })
            
        return {
            "universe_size": len(results),
            "total_market_cap": total_market_cap,
            "tickers": results
        }
