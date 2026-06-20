import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import AgentResult, BaseAgent
from ..data_client import NasdaqScreenerClient, AlpacaOHLCVClient

logger = logging.getLogger(__name__)

class CorrelationAgent(BaseAgent):
    """
    Agent that identifies uncorrelated assets to achieve Ray Dalio's 'Holy Grail'
    of independent return streams, calculated directly on custom sector indexes.
    """

    @property
    def name(self) -> str:
        return "CorrelationAgent"

    async def analyze(self, **kwargs) -> AgentResult:
        """
        Performs cross-sector correlation analysis on price-weighted indexes
        to identify Ray Dalio's 'Holy Grail' of uncorrelated return streams.
        Uses rolling correlations to ensure resilience across regimes.
        """
        self._log_start()
        
        # Load parameters from spec
        lookback_days = kwargs.get("lookback_days", 2520) # 10 years default now
        rolling_window = kwargs.get("rolling_window", 252) # 1 year rolling window
        correlation_threshold = kwargs.get("correlation_threshold", 0.3) # Slightly relaxed for 90th percentile
        reference_sector = kwargs.get("reference_sector", "Technology")
        selection_criteria = kwargs.get("selection_criteria", "momentum")
        
        screener = NasdaqScreenerClient()
        alpaca = AlpacaOHLCVClient()
        
        # 1. Fetch Universe and Sectors
        logger.info("📡 Loading NASDAQ screener sectors...")
        df_universe = screener.load_data()
        if df_universe.empty:
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                rationale="Failed to load Nasdaq screener database.",
            )
            
        sectors = df_universe["sector"].dropna().unique().tolist()
        sectors = [s.strip() for s in sectors if s.strip()]
        logger.info(f"📋 Found {len(sectors)} sectors for Holy Grail index analysis: {sectors}")
 
        # 2. Fetch daily index series for each sector
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        logger.info(f"📥 Generating historical daily index series over {lookback_days} days...")
        sector_series = {}
        for sector in sectors:
            try:
                series = alpaca.get_sector_index_series(
                    sector, start_date, end_date, selection_criteria=selection_criteria
                )
                if not series.empty:
                    sector_series[sector] = series
                    logger.info(f"✅ Generated daily index for sector: {sector} ({len(series)} days)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to generate index for sector {sector}: {e}")

        if not sector_series:
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                rationale="Could not construct historical index series for any sector.",
            )

        # 3. Combine to DataFrame and calculate log returns
        df_indexes = pd.DataFrame(sector_series).dropna()
        if df_indexes.empty:
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                rationale="No overlapping calendar dates between sector indexes.",
            )
            
        log_returns = np.log(df_indexes / df_indexes.shift(1)).dropna()
        
        # 4. Compute 1-Year Rolling Correlation Matrix (90th percentile to measure worst-case correlation)
        logger.info(f"🧮 Computing {rolling_window}-day rolling correlations across 10 years...")
        # Initialize an empty matrix for the worst-case (90th percentile) correlations
        cols = log_returns.columns
        worst_case_corr_matrix = pd.DataFrame(index=cols, columns=cols, dtype=float)
        
        for col1 in cols:
            for col2 in cols:
                if col1 == col2:
                    worst_case_corr_matrix.loc[col1, col2] = 1.0
                elif pd.isna(worst_case_corr_matrix.loc[col1, col2]):
                    # Compute rolling correlation series
                    roll_corr = log_returns[col1].rolling(window=rolling_window).corr(log_returns[col2]).dropna()
                    if not roll_corr.empty:
                        # 90th percentile absolute correlation (to catch high negative OR positive correlation)
                        # Actually, Dalio wants uncorrelated (near 0), so we look at the absolute max/90th
                        val = np.percentile(roll_corr.abs(), 90)
                        worst_case_corr_matrix.loc[col1, col2] = val
                        worst_case_corr_matrix.loc[col2, col1] = val
                    else:
                        worst_case_corr_matrix.loc[col1, col2] = 1.0
                        worst_case_corr_matrix.loc[col2, col1] = 1.0
                        
        corr_matrix = worst_case_corr_matrix
        
        # 5. Find sectors uncorrelated to the reference sector (Technology by default)
        if reference_sector not in corr_matrix.columns:
            reference_sector = corr_matrix.columns[0]
            
        uncorrelated_assets = []
        for sector in corr_matrix.columns:
            if sector == reference_sector:
                continue
            corr_val = corr_matrix.loc[reference_sector, sector]
            if not np.isnan(corr_val) and abs(corr_val) < correlation_threshold:
                uncorrelated_assets.append({
                    "symbol": sector,
                    "correlation": float(corr_val)
                })
                
        # Sort by absolute lowest correlation
        uncorrelated_assets = sorted(uncorrelated_assets, key=lambda x: abs(x['correlation']))

        # 6. Find Ray Dalio's Holy Grail mutually uncorrelated basket (greedy clique selection)
        holy_grail_basket = []
        # Sort sectors by absolute average correlation to others to pick the most independent ones first
        avg_corrs = corr_matrix.abs().mean().sort_values()
        for sector in avg_corrs.index:
            is_mutually_uncorrelated = True
            for selected in holy_grail_basket:
                val = corr_matrix.loc[sector, selected]
                if np.isnan(val) or abs(val) >= correlation_threshold:
                    is_mutually_uncorrelated = False
                    break
            if is_mutually_uncorrelated:
                holy_grail_basket.append(sector)

        # 7. Build beautiful, high-energy rationale
        basket_str = ", ".join([f"`{s}`" for s in holy_grail_basket])
        count = len(holy_grail_basket)
        rationale = (
            f"Analyzed {rolling_window}-day rolling cross-correlations over 10 years for {len(corr_matrix.columns)} dynamic momentum sector indexes. "
            f"Found {len(uncorrelated_assets)} sectors consistently uncorrelated (90th pctl < {correlation_threshold}) to reference `{reference_sector}`. "
            f"Ray Dalio's Holy Grail basket contains {count} mutually independent sectors: {basket_str}."
        )

        # 8. Return AgentResult
        result = AgentResult(
            agent_name=self.name,
            score=1.0 if count >= 3 else 0.7,
            confidence=0.95,
            rationale=rationale,
            data={
                "reference_asset": reference_sector,
                "uncorrelated_assets": uncorrelated_assets,
                "top_10_uncorrelated": uncorrelated_assets[:10],
                "holy_grail_basket": holy_grail_basket,
                "total_analyzed": len(corr_matrix.columns)
            }
        )
        
        self._log_done(result)
        return result
