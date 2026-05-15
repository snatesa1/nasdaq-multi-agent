"""
Correlation Agent: The "Holy Grail" of investing.
Identifies uncorrelated assets (< 0.2 correlation) using log returns across 
Stocks, Bonds, and Bitcoin to reduce portfolio risk.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import AgentResult, BaseAgent
from ..data_client import YFinanceClient

logger = logging.getLogger(__name__)

# Default basket for "Holy Grail" search
DEFAULT_BASKET = [
    "SPY", "QQQ", "IWM",          # Indices
    "TLT", "BND", "AGG",          # Bonds
    "BTC-USD", "ETH-USD",         # Crypto
    "GLD", "SLV",                 # Commodities
    "XLK", "XLF", "XLV", "XLE",   # Sectors
    "XLY", "XLP", "XLB", "XLU",
    "XLI", "XLRE"
]

class CorrelationAgent(BaseAgent):
    """
    Agent that identifies uncorrelated assets to achieve the 'Holy Grail' 
    of 15-20 independent return streams.
    """

    @property
    def name(self) -> str:
        return "CorrelationAgent"

    async def analyze(self, basket: List[str] = None, lookback_days: int = 252) -> AgentResult:
        """
        Performs correlation analysis on a basket of assets.
        Args:
            basket: List of tickers.
            lookback_days: Number of days for historical data.
        """
        self._log_start()
        basket = basket or DEFAULT_BASKET
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # 1. Fetch data and calculate log returns
        returns_data = {}
        for symbol in basket:
            df = YFinanceClient.get_historical(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            if not df.empty and "Close" in df.columns:
                # Calculate log returns
                df['log_return'] = np.log(df['Close'] / df['Close'].shift(1))
                returns_data[symbol] = df['log_return']
        
        if not returns_data:
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                rationale="No historical data found for correlation analysis.",
            )

        # 2. Build Returns DataFrame
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # 3. Compute Correlation Matrix
        corr_matrix = returns_df.corr()
        
        # 4. Find "Holy Grail" Assets (Uncorrelated with SPY/Market)
        # We look for assets with low correlation to the main market index (SPY)
        target_ref = "SPY"
        if target_ref not in corr_matrix.columns:
            target_ref = returns_df.columns[0]
            
        uncorrelated = []
        for asset in corr_matrix.columns:
            if asset == target_ref:
                continue
            corr_val = corr_matrix.loc[target_ref, asset]
            if abs(corr_val) < 0.2:
                uncorrelated.append({
                    "symbol": asset,
                    "correlation": float(corr_val)
                })
        
        # Sort by lowest absolute correlation
        uncorrelated = sorted(uncorrelated, key=lambda x: abs(x['correlation']))

        # 5. Build Rationale
        count = len(uncorrelated)
        rationale = f"Analyzed {len(basket)} assets. Found {count} assets with < 0.2 correlation to {target_ref}. "
        if count >= 15:
            rationale += "The 'Holy Grail' of 15+ uncorrelated bets is ACHIEVED. Portfolio risk can be reduced by ~80%."
        else:
            rationale += f"Need more uncorrelated assets (currently {count}/15) to reach Dalio's risk reduction target."

        # 6. Final Result
        result = AgentResult(
            agent_name=self.name,
            score=1.0 if count >= 15 else 0.7,
            confidence=0.9,
            rationale=rationale,
            data={
                "reference_asset": target_ref,
                "uncorrelated_assets": uncorrelated,
                "top_5_uncorrelated": uncorrelated[:5],
                "matrix_summary": corr_matrix.to_dict() # Careful with size, but small basket is fine
            }
        )
        
        self._log_done(result)
        return result
