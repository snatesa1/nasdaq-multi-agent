import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import AgentResult, BaseAgent
from ..data_client import FMPClient, YFinanceClient

logger = logging.getLogger(__name__)

# Core defensive assets that often provide uncorrelated returns
DEFENSIVE_BASKET = [
    "TLT", "BND", "AGG",          # Bonds
    "BTC-USD", "ETH-USD",         # Crypto
    "GLD", "SLV",                 # Commodities
    "UUP", "FXF",                 # Currencies (USD, CHF)
]

class CorrelationAgent(BaseAgent):
    """
    Agent that identifies uncorrelated assets to achieve the 'Holy Grail' 
    of 15-20 independent return streams. 
    Now pulls dynamically from S&P 500 and NASDAQ.
    """

    @property
    def name(self) -> str:
        return "CorrelationAgent"

    async def analyze(self, lookback_days: int = 252) -> AgentResult:
        """
        Performs correlation analysis on a massive basket of assets.
        """
        self._log_start()
        
        fmp = FMPClient()
        
        # 1. Fetch Tickers from Indices
        logger.info("📡 Fetching S&P 500 and NASDAQ tickers...")
        sp500 = fmp.get_sp500_constituents()
        nasdaq = fmp.get_nasdaq_constituents()
        
        sp_tickers = [item.get("symbol") for item in sp500 if item.get("symbol")]
        nq_tickers = [item.get("symbol") for item in nasdaq if item.get("symbol")]
        
        # Combine and deduplicate
        full_basket = list(set(sp_tickers + nq_tickers + DEFENSIVE_BASKET))
        logger.info(f"📋 Total candidates for Holy Grail search: {len(full_basket)}")

        # 2. Fetch Data in Batches (to avoid timeout/memory issues)
        # We'll take the first 600 tickers to keep it manageable but comprehensive
        analysis_limit = 600
        target_tickers = full_basket[:analysis_limit]
        if "SPY" not in target_tickers:
            target_tickers.append("SPY")
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        logger.info(f"📥 Batch downloading data for {len(target_tickers)} assets...")
        try:
            data = yf.download(
                target_tickers, 
                start=start_date.strftime("%Y-%m-%d"), 
                end=end_date.strftime("%Y-%m-%d"),
                group_by='column',
                progress=False
            )
            
            if data.empty or "Close" not in data:
                return AgentResult(
                    agent_name=self.name,
                    score=0.5,
                    rationale="Failed to download historical data for analysis.",
                )
                
            close_data = data["Close"]
        except Exception as e:
            logger.error(f"❌ Batch download failed: {e}")
            return AgentResult(agent_name=self.name, score=0.5, rationale=f"Error: {str(e)}")

        # 3. Calculate Log Returns
        log_returns = np.log(close_data / close_data.shift(1)).dropna()
        
        # 4. Compute Correlation Matrix
        corr_matrix = log_returns.corr()
        
        # 5. Identify Uncorrelated Assets (to SPY)
        target_ref = "SPY"
        if target_ref not in corr_matrix.columns:
            target_ref = log_returns.columns[0]
            
        uncorrelated = []
        for asset in corr_matrix.columns:
            if asset == target_ref:
                continue
            corr_val = corr_matrix.loc[target_ref, asset]
            if not np.isnan(corr_val) and abs(corr_val) < 0.2:
                uncorrelated.append({
                    "symbol": asset,
                    "correlation": float(corr_val)
                })
        
        # Sort by lowest absolute correlation
        uncorrelated = sorted(uncorrelated, key=lambda x: abs(x['correlation']))

        # 6. Build Rationale
        count = len(uncorrelated)
        rationale = f"Analyzed {len(target_tickers)} assets across S&P 500, NASDAQ, and Macro. Found {count} uncorrelated assets (< 0.2) to {target_ref}. "
        if count >= 15:
            rationale += "The 'Holy Grail' of 15+ uncorrelated bets is ACHIEVED. Portfolio risk can be reduced by ~80%."
        else:
            rationale += f"Need more uncorrelated assets (currently {count}/15) to reach Dalio's risk reduction target."

        # 7. Final Result
        result = AgentResult(
            agent_name=self.name,
            score=1.0 if count >= 15 else 0.7,
            confidence=0.9,
            rationale=rationale,
            data={
                "reference_asset": target_ref,
                "uncorrelated_assets": uncorrelated,
                "top_10_uncorrelated": uncorrelated[:10],
                "total_analyzed": len(target_tickers)
            }
        )
        
        self._log_done(result)
        return result
