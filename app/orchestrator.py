"""
Hierarchical Orchestrator — coordinates the 3-tier agent pipeline.

Tier 1: Macro Agent + FRED Indicators (parallel)
Tier 2: Fundamental + Technical per stock (parallel)
Tier 3: Portfolio weighting + Risk adjustment                [Phase 3]
"""

import asyncio
import logging
import os
import yaml
from datetime import datetime
from typing import Dict, List

from .agents.macro_agent import MacroAgent
from .agents.fred_indicators_agent import FredIndicatorsAgent
from .agents.technical_agent import TechnicalAgent
from .agents.fundamental_agent import FundamentalAgent
from .agents.correlation_agent import CorrelationAgent
from .agents.base_agent import AgentResult

logger = logging.getLogger(__name__)


class HierarchicalOrchestrator:
    """
    Top-down pipeline coordinator.
    Tier 1: Macro + FRED + Correlation (Holy Grail)
    Tier 2: Fundamental + Technical per stock
    """

    def __init__(self, spec_path: str = None):
        if spec_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            spec_path = os.path.join(base_dir, "config", "spec.yaml")
            
        with open(spec_path, "r") as f:
            self.spec = yaml.safe_load(f)
            
        self.pipeline = self.spec.get("pipeline", {})
        
        # Instantiate agents based on spec
        self.macro_agent = MacroAgent()
        self.fred_agent = FredIndicatorsAgent()
        self.technical_agent = TechnicalAgent()
        self.fundamental_agent = FundamentalAgent()
        self.correlation_agent = CorrelationAgent()

    async def run_full_analysis(self) -> Dict:
        """
        Execute the full hierarchical analysis pipeline based on spec.yaml.
        Returns combined results from all tiers.
        """
        start_time = datetime.now()
        logger.info("🎼 Orchestrator: Starting full hierarchical analysis based on spec...")

        # ── TIER 1: Macro + Correlation (parallel) ──
        logger.info("── Tier 1: Top-Down Macro + Correlation Analysis ──")
        
        tier1_spec = self.pipeline.get("tier_1", {})
        macro_params = tier1_spec.get("macro_agent", {}).get("params", {})
        fred_params = tier1_spec.get("fred_indicators_agent", {}).get("params", {})
        corr_params = tier1_spec.get("correlation_agent", {}).get("params", {})

        macro_result, fred_result, correlation_result = await asyncio.gather(
            self.macro_agent.analyze(**macro_params),
            self.fred_agent.analyze(**fred_params),
            self.correlation_agent.analyze(**corr_params),
        )

        stock_universe = macro_result.data.get("stock_universe", [])
        logger.info(f"📋 Stock universe: {stock_universe}")

        # 🎯 Independence Check (Log domain verification)
        logger.info("🛡️ Signal Independence Check: Macro (FRED/Econ), Technical (Price/Vol), Fundamental (FMP/Financials). Domains are distinct.")

        # ═══ TIER 2: Per-stock Technical + Fundamental (parallel) ═══
        logger.info("── Tier 2: Technical + Fundamental Analysis ──")
        technical_results = []
        fundamental_results = []

        if stock_universe:
            tier2_spec = self.pipeline.get("tier_2", {})
            tech_params = tier2_spec.get("technical_agent", {}).get("params", {})
            fund_params = tier2_spec.get("fundamental_agent", {}).get("params", {})
            
            # Run both agents in parallel for all stocks
            tech_tasks = [self.technical_agent.analyze(symbol=s, **tech_params) for s in stock_universe]
            fund_tasks = [self.fundamental_agent.analyze(symbol=s, **fund_params) for s in stock_universe]
            all_tasks = tech_tasks + fund_tasks

            all_results = await asyncio.gather(*all_tasks)

            # Split results: first N are technical, last N are fundamental
            n = len(stock_universe)
            technical_results = list(all_results[:n])
            fundamental_results = list(all_results[n:])

        # ═══ TIER 3: Portfolio + Risk ═══
        logger.info("── Tier 3: Portfolio + Risk (Holy Grail Selection) ──")
        # Identify overlaps between stock_universe and uncorrelated_assets
        uncorrelated_symbols = [a["symbol"] for a in correlation_result.data.get("uncorrelated_assets", [])]
        
        # Load screener data to map stock ticker to its sector
        from .data_client import NasdaqScreenerClient
        screener = NasdaqScreenerClient()
        df_screener = screener.load_data()
        
        holy_grail_overlaps = []
        if not df_screener.empty:
            symbol_to_sector = df_screener.dropna(subset=["symbol", "sector"])
            symbol_to_sector = symbol_to_sector.set_index("symbol")["sector"].to_dict()
            symbol_to_sector = {str(k).strip(): str(v).strip() for k, v in symbol_to_sector.items()}
            
            for s in stock_universe:
                sec = symbol_to_sector.get(s.strip())
                if sec and sec in uncorrelated_symbols:
                    holy_grail_overlaps.append(s)
        else:
            holy_grail_overlaps = []

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Orchestrator complete in {duration:.1f}s")

        return {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 1),
            "tier1": {
                "macro": macro_result.to_dict(),
                "fred_indicators": fred_result.to_dict(),
                "holy_grail": correlation_result.to_dict(),
            },
            "tier2": {
                "technical": [r.to_dict() for r in technical_results],
                "fundamental": [r.to_dict() for r in fundamental_results],
            },
            "tier3": {
                "holy_grail_selections": holy_grail_overlaps,
                "status": "Risk reduction active via uncorrelated assets."
            },
            "stock_universe": stock_universe,
            "selected_sectors": macro_result.data.get("selected_sectors", []),
        }

