"""
Hierarchical Orchestrator — coordinates the 3-tier agent pipeline.

Tier 1: Macro Agent + FRED Indicators (parallel)
Tier 2: Fundamental + Technical per stock (parallel)
Tier 3: Portfolio weighting + Risk adjustment                [Phase 3]
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from .agents.macro_agent import MacroAgent
from .agents.fred_indicators_agent import FredIndicatorsAgent
from .agents.technical_agent import TechnicalAgent
from .agents.fundamental_agent import FundamentalAgent
from .agents.base_agent import AgentResult

logger = logging.getLogger(__name__)


class HierarchicalOrchestrator:
    """
    Top-down pipeline coordinator.
    Phase 1: Macro + FRED + Technical
    Phase 2: + Fundamental per stock
    """

    def __init__(self):
        self.macro_agent = MacroAgent()
        self.fred_agent = FredIndicatorsAgent()
        self.technical_agent = TechnicalAgent()
        self.fundamental_agent = FundamentalAgent()

    async def run_full_analysis(self, top_n_sectors: int = 11) -> Dict:
        """
        Execute the full hierarchical analysis pipeline.
        Returns combined results from all tiers.
        """
        start_time = datetime.now()
        logger.info("🎼 Orchestrator: Starting full hierarchical analysis...")

        # ═══ TIER 1: Macro (parallel) ═══
        logger.info("── Tier 1: Top-Down Macro Analysis ──")
        macro_result, fred_result = await asyncio.gather(
            self.macro_agent.analyze(top_n=top_n_sectors),
            self.fred_agent.analyze(lookback_months=12),
        )

        stock_universe = macro_result.data.get("stock_universe", [])
        logger.info(f"📋 Stock universe: {stock_universe}")

        # ═══ TIER 2: Per-stock Technical + Fundamental (parallel) ═══
        logger.info("── Tier 2: Technical + Fundamental Analysis ──")
        technical_results = []
        fundamental_results = []

        if stock_universe:
            # Run both agents in parallel for all stocks
            tech_tasks = [self.technical_agent.analyze(symbol=s) for s in stock_universe]
            fund_tasks = [self.fundamental_agent.analyze(symbol=s) for s in stock_universe]
            all_tasks = tech_tasks + fund_tasks

            all_results = await asyncio.gather(*all_tasks)

            # Split results: first N are technical, last N are fundamental
            n = len(stock_universe)
            technical_results = list(all_results[:n])
            fundamental_results = list(all_results[n:])

        # ═══ TIER 3: Portfolio + Risk (Phase 3 — stub for now) ═══
        logger.info("── Tier 3: Portfolio + Risk (stub) ──")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Orchestrator complete in {duration:.1f}s")

        return {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 1),
            "tier1": {
                "macro": macro_result.to_dict(),
                "fred_indicators": fred_result.to_dict(),
            },
            "tier2": {
                "technical": [r.to_dict() for r in technical_results],
                "fundamental": [r.to_dict() for r in fundamental_results],
            },
            "tier3": {
                "portfolio": "Phase 3 — not yet implemented",
                "risk": "Phase 3 — not yet implemented",
            },
            "stock_universe": stock_universe,
            "selected_sectors": macro_result.data.get("selected_sectors", []),
        }

