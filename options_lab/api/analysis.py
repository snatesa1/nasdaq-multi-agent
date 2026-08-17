import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from .db import get_portfolio
from .market_data import fetch_market_data

logger = logging.getLogger(__name__)

def get_sector_mapping() -> Dict[str, str]:
    """Load sector mapping from nasdaq_screener.csv."""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nasdaq_screener.csv")
        if not os.path.exists(csv_path):
            return {}
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=['sector', 'symbol'])
        df['symbol'] = df['symbol'].str.strip().str.upper()
        df['sector'] = df['sector'].str.strip()
        return df.set_index('symbol')['sector'].to_dict()
    except Exception as e:
        logger.error(f"Failed to load sector mapping: {e}")
        return {}

def analyze_portfolio_diversification(portfolio_id: str) -> Dict[str, Any]:
    """
    Perform sector, asset class, and correlation analysis on a portfolio.
    """
    portfolio = get_portfolio(portfolio_id)
    if not portfolio or not portfolio.get("tickers"):
        return {"error": "Portfolio is empty or not found."}
        
    tickers = portfolio["tickers"]
    symbols = [t["symbol"].upper().strip() for t in tickers]
    
    # 1. Sector Mapping & Asset Class Classification
    sector_map = get_sector_mapping()
    
    sector_counts = {}
    asset_class_counts = {}
    
    sector_allocations = []
    asset_class_allocations = []
    
    for sym in symbols:
        # Determine Sector
        # Manual overrides for cryptos, futures, and ETFs
        if sym in ["BTC", "ETH", "IBIT"]:
            sector = "Crypto / Digital Assets"
        elif sym == "COIN":
            sector = "Financials (Crypto Exposure)"
        elif sym.endswith("=F"):
            sector = "Futures / Index"
        elif sym in ["RSP", "SPY", "QQQ", "DIA", "IWM", "GLD", "SLV"]:
            sector = "Index / Commodity ETF"
        else:
            sector = sector_map.get(sym, "Technology" if sym in ["DELL", "HPE", "PANW", "GWRE", "TSM"] else "Other")
            
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Determine Asset Class
        if sym.endswith("=F"):
            asset_class = "Futures"
        elif sym in ["BTC", "ETH"]:
            asset_class = "Cryptocurrency"
        elif sym == "IBIT":
            asset_class = "Cryptocurrency ETF"
        elif sym in ["RSP", "SPY", "QQQ", "DIA", "IWM", "GLD", "SLV"]:
            asset_class = "Equity/Commodity ETF"
        else:
            asset_class = "Common Stock"
            
        asset_class_counts[asset_class] = asset_class_counts.get(asset_class, 0) + 1
        
    total_tickers = len(symbols)
    
    for sector, count in sector_counts.items():
        sector_allocations.append({
            "sector": sector,
            "count": count,
            "percentage": round((count / total_tickers) * 100, 1)
        })
    # Sort descending
    sector_allocations = sorted(sector_allocations, key=lambda x: x["percentage"], reverse=True)
    
    for ac, count in asset_class_counts.items():
        asset_class_allocations.append({
            "asset_class": ac,
            "count": count,
            "percentage": round((count / total_tickers) * 100, 1)
        })
    asset_class_allocations = sorted(asset_class_allocations, key=lambda x: x["percentage"], reverse=True)
    
    # 2. Historical Price Correlation (using ThreadPoolExecutor for parallel fetch)
    logger.info(f"Fetching historical daily price series for {len(symbols)} symbols in parallel...")
    price_series = {}
    
    def fetch_single(sym):
        try:
            data = fetch_market_data(sym, days=120)
            if data and not data.get("is_simulated") and len(data.get("prices", [])) > 10:
                return sym, data["prices"][-90:] # take last 90 trading days
        except Exception as e:
            logger.warning(f"Failed to fetch correlation data for {sym}: {e}")
        return sym, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_single, symbols)
        for sym, prices in results:
            if prices:
                price_series[sym] = prices
                
    # Align lengths and compute correlation matrix
    correlation_results = []
    avg_correlation = 0.0
    correlation_warnings = []
    
    if len(price_series) >= 2:
        # Construct DataFrame
        min_len = min(len(p) for p in price_series.values())
        trimmed_series = {sym: p[-min_len:] for sym, p in price_series.items()}
        
        df = pd.DataFrame(trimmed_series)
        log_returns = np.log(df / df.shift(1)).dropna()
        
        corr_matrix = log_returns.corr()
        
        # Extract individual correlations
        corr_values = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                c1 = corr_matrix.columns[i]
                c2 = corr_matrix.columns[j]
                val = corr_matrix.iloc[i, j]
                if not np.isnan(val):
                    corr_values.append(val)
                    if val > 0.75:
                        correlation_warnings.append(f"High Correlation: `{c1}` & `{c2}` ({val:.2f})")
                        
        if corr_values:
            avg_correlation = float(np.mean(corr_values))
            
        # Convert matrix to list of dicts for frontend display
        for col in corr_matrix.columns:
            corr_dict = {"symbol": col}
            for other in corr_matrix.columns:
                corr_dict[other] = round(float(corr_matrix.loc[col, other]), 2)
            correlation_results.append(corr_dict)
            
    # 3. Generate Analysis Review / Summary Recommendation
    tech_alloc = sector_counts.get("Technology", 0) / total_tickers
    crypto_alloc = (sector_counts.get("Crypto / Digital Assets", 0) + sector_counts.get("Financials (Crypto Exposure)", 0)) / total_tickers
    
    score = 100
    recommendations = []
    
    if tech_alloc > 0.30:
        score -= 15
        recommendations.append(f"High Technology Concentration ({tech_alloc*100:.1f}%). Add defensive sectors (Healthcare, Utilities, Staples) to lower systemic risk.")
    if crypto_alloc > 0.10:
        score -= 10
        recommendations.append(f"High Crypto/Digital Asset exposure ({crypto_alloc*100:.1f}%). Watch for crypto volatility correlation across these symbols.")
    if avg_correlation > 0.45:
        score -= 15
        recommendations.append(f"High average asset correlation ({avg_correlation:.2f}). Seek assets with correlation < 0.2 (like commodities or bonds) to build Dalio's 'Holy Grail' portfolio.")
    elif avg_correlation < 0.20 and total_tickers >= 10:
        recommendations.append("Excellent diversification! Your average portfolio correlation is below 0.20, achieving solid risk reduction.")
    else:
        recommendations.append("Moderate diversification. Adding 3-5 uncorrelated assets from different sectors can reduce risk by up to 50% without affecting returns.")
        
        correlation_warnings.append("No highly correlated pairs (>0.75) detected.")
        
    return {
        "portfolio_id": portfolio_id,
        "name": portfolio["name"],
        "diversification_score": max(score, 30),
        "total_tickers": total_tickers,
        "sector_allocations": sector_allocations,
        "asset_class_allocations": asset_class_allocations,
        "average_correlation": round(avg_correlation, 2),
        "correlation_matrix": correlation_results,
        "correlation_warnings": correlation_warnings[:5],
        "recommendations": recommendations
    }


def calculate_portfolio_greeks(
    positions: List[Dict[str, Any]],
    risk_free_rate: float = 0.05
) -> Dict[str, Any]:
    """
    Calculate aggregated Net Delta, Net Gamma, Net Theta, and Net Vega
    for a multi-leg portfolio of stocks and option contracts.
    
    Position structure:
    {
      "type": "stock" | "call" | "put",
      "symbol": "AAPL",
      "quantity": 10 (contracts or stock shares),
      "spot_price": 180.0,
      "strike": 180.0,
      "days_to_expiration": 30,
      "volatility": 0.25
    }
    """
    from engine.black_scholes import black_scholes_greeks
    
    total_delta = 0.0
    total_gamma = 0.0
    total_theta = 0.0
    total_vega = 0.0
    
    leg_greeks = []
    
    for pos in positions:
        pos_type = pos.get("type", "stock").lower()
        qty = float(pos.get("quantity", 1.0))
        spot = float(pos.get("spot_price", 100.0))
        
        if pos_type == "stock":
            leg_delta = qty * 1.0
            leg_gamma = 0.0
            leg_theta = 0.0
            leg_vega = 0.0
        else:
            strike = float(pos.get("strike", spot))
            days = float(pos.get("days_to_expiration", 30))
            T = max(days / 365.0, 0.001)
            vol = float(pos.get("volatility", 0.25))
            
            # Each options contract covers 100 shares
            contract_multiplier = 100.0
            
            bs_g = black_scholes_greeks(spot, strike, T, risk_free_rate, vol, pos_type)
            leg_delta = qty * contract_multiplier * bs_g["delta"]
            leg_gamma = qty * contract_multiplier * bs_g["gamma"]
            leg_theta = qty * contract_multiplier * bs_g["theta"]
            leg_vega = qty * contract_multiplier * bs_g["vega"]
            
        total_delta += leg_delta
        total_gamma += leg_gamma
        total_theta += leg_theta
        total_vega += leg_vega
        
        leg_greeks.append({
            "symbol": pos.get("symbol", "N/A"),
            "type": pos_type.upper(),
            "quantity": qty,
            "delta": round(leg_delta, 2),
            "gamma": round(leg_gamma, 4),
            "theta": round(leg_theta, 2),
            "vega": round(leg_vega, 2)
        })
        
    # Delta-neutral hedge calculation: required underlying shares to offset net delta
    delta_hedge_shares = -round(total_delta, 2)
    
    return {
        "net_greeks": {
            "delta": round(total_delta, 2),
            "gamma": round(total_gamma, 4),
            "theta": round(total_theta, 2),
            "vega": round(total_vega, 2)
        },
        "delta_hedge_recommendation": {
            "required_shares": delta_hedge_shares,
            "action": "BUY" if delta_hedge_shares > 0 else "SELL" if delta_hedge_shares < 0 else "NEUTRAL",
            "explanation": f"{'Buy' if delta_hedge_shares > 0 else 'Sell'} {abs(delta_hedge_shares)} shares of underlying stock to achieve a Delta-Neutral (\u0394 = 0) position."
        },
        "leg_details": leg_greeks
    }

