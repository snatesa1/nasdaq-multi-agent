"""
Hierarchical Orchestrator — coordinates the 3-tier agent pipeline using Google ADK 2.0.

Tier 1: Macro Agent + FRED Indicators + Correlation (Holy Grail)
Tier 2: Fundamental + Technical per stock
Tier 3: Portfolio weighting + Risk adjustment
"""

import asyncio
import logging
import os
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional

from google.adk.workflow import Workflow, node, START, Edge
from google.adk.version import __version__ as adk_version

from .agents.macro_agent import MacroAgent
from .agents.fred_indicators_agent import FredIndicatorsAgent
from .agents.technical_agent import TechnicalAgent
from .agents.fundamental_agent import FundamentalAgent
from .agents.correlation_agent import CorrelationAgent
from .agents.base_agent import AgentResult

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADK 2.0 GRAPH NODES DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

@node(name="tier1_macro_correlation_node", timeout=60.0)
async def tier1_macro_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tier 1 ADK Node: Executes Macro, FRED indicators, and Cross-Asset Correlation
    in parallel, establishing the macro regime and candidate stock universe.
    """
    orch = state["orchestrator"]
    tier1_spec = orch.pipeline.get("tier_1", {})
    macro_params = tier1_spec.get("macro_agent", {}).get("params", {})
    fred_params = tier1_spec.get("fred_indicators_agent", {}).get("params", {})
    corr_params = tier1_spec.get("correlation_agent", {}).get("params", {})

    logger.info("📡 [ADK Node: tier1_macro_correlation] Running Top-Down Macro + Correlation Analysis...")
    macro_result, fred_result, correlation_result = await asyncio.gather(
        orch.macro_agent.analyze(**macro_params),
        orch.fred_agent.analyze(**fred_params),
        orch.correlation_agent.analyze(**corr_params),
    )

    stock_universe = macro_result.data.get("stock_universe", [])
    logger.info(f"📋 [ADK Node: tier1_macro_correlation] Stock universe: {stock_universe}")

    return {
        **state,
        "macro_result": macro_result,
        "fred_result": fred_result,
        "correlation_result": correlation_result,
        "stock_universe": stock_universe,
        "step_completed": "tier1_macro_correlation_node"
    }


@node(name="tier2_tech_fund_node", timeout=60.0)
async def tier2_tech_fund_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tier 2 ADK Node: Runs per-stock Technical and Fundamental analysis across
    the discovered stock universe and injects sector classifications.
    """
    orch = state["orchestrator"]
    stock_universe = state.get("stock_universe", [])
    technical_results = []
    fundamental_results = []

    logger.info("📈 [ADK Node: tier2_tech_fund] Running Technical + Fundamental Analysis...")
    if stock_universe:
        tier2_spec = orch.pipeline.get("tier_2", {})
        tech_params = tier2_spec.get("technical_agent", {}).get("params", {})
        fund_params = tier2_spec.get("fundamental_agent", {}).get("params", {})

        tech_tasks = [orch.technical_agent.analyze(symbol=s, **tech_params) for s in stock_universe]
        fund_tasks = [orch.fundamental_agent.analyze(symbol=s, **fund_params) for s in stock_universe]
        all_results = await asyncio.gather(*(tech_tasks + fund_tasks))

        n = len(stock_universe)
        technical_results = list(all_results[:n])
        fundamental_results = list(all_results[n:])

    # Load screener data to map stock ticker to its sector
    from .data_client import NasdaqScreenerClient
    screener = NasdaqScreenerClient()
    df_screener = screener.load_data()

    symbol_to_sector = {}
    if not df_screener.empty:
        symbol_to_sector = df_screener.dropna(subset=["symbol", "sector"])
        symbol_to_sector = symbol_to_sector.set_index("symbol")["sector"].to_dict()
        symbol_to_sector = {str(k).strip(): str(v).strip() for k, v in symbol_to_sector.items()}

        for r in technical_results:
            sym = r.data.get("symbol")
            if sym:
                r.data["sector"] = symbol_to_sector.get(sym.strip(), "N/A")
        for r in fundamental_results:
            sym = r.data.get("symbol")
            if sym:
                r.data["sector"] = symbol_to_sector.get(sym.strip(), "N/A")

    return {
        **state,
        "technical_results": technical_results,
        "fundamental_results": fundamental_results,
        "symbol_to_sector": symbol_to_sector,
        "df_screener": df_screener,
        "step_completed": "tier2_tech_fund_node"
    }


@node(name="tier3_portfolio_risk_node", timeout=30.0)
async def tier3_portfolio_risk_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tier 3 ADK Node: Cross-references fundamental conviction with uncorrelated assets
    to produce Holy Grail low-drawdown portfolio selections.
    """
    stock_universe = state.get("stock_universe", [])
    correlation_result = state["correlation_result"]
    symbol_to_sector = state.get("symbol_to_sector", {})
    df_screener = state.get("df_screener")

    logger.info("🛡️ [ADK Node: tier3_portfolio_risk] Computing Holy Grail Selection...")
    uncorrelated_symbols = [a["symbol"] for a in correlation_result.data.get("uncorrelated_assets", [])]

    holy_grail_overlaps = []
    if df_screener is not None and not df_screener.empty:
        for s in stock_universe:
            sec = symbol_to_sector.get(s.strip())
            if sec and sec in uncorrelated_symbols:
                holy_grail_overlaps.append(s)

    return {
        **state,
        "holy_grail_overlaps": holy_grail_overlaps,
        "step_completed": "tier3_portfolio_risk_node"
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  HIERARCHICAL ORCHESTRATOR CLASS (ADK 2.0 POWERED)
# ═══════════════════════════════════════════════════════════════════════════════

class HierarchicalOrchestrator:
    """
    Top-down pipeline coordinator modernized with Google ADK 2.0 Workflow.
    Tier 1: Macro + FRED + Correlation (Holy Grail)
    Tier 2: Fundamental + Technical per stock
    Tier 3: Portfolio + Risk Adjustment
    """

    def __init__(self, spec_path: str = None):
        if spec_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            spec_path = os.path.join(base_dir, "config", "spec.yaml")

        with open(spec_path, "r") as f:
            self.spec = yaml.safe_load(f)

        self.pipeline = self.spec.get("pipeline", {})

        # Instantiate agent specialists
        self.macro_agent = MacroAgent()
        self.fred_agent = FredIndicatorsAgent()
        self.technical_agent = TechnicalAgent()
        self.fundamental_agent = FundamentalAgent()
        self.correlation_agent = CorrelationAgent()

        # Build declarative ADK 2.0 graph workflow
        self.workflow = Workflow(
            name="nasdaq_hierarchical_orchestrator_workflow",
            description="Declarative ADK 2.0 multi-tier financial intelligence DAG.",
            edges=[
                (START, tier1_macro_node),
                (tier1_macro_node, tier2_tech_fund_node),
                (tier2_tech_fund_node, tier3_portfolio_risk_node)
            ]
        )

    async def run_full_analysis(self) -> Dict[str, Any]:
        """
        Executes the hierarchical analysis pipeline via Google ADK 2.0 graph nodes.
        Preserves 100% backward compatibility for output schema.
        """
        start_time = datetime.now()
        logger.info("🎼 [ADK 2.0 Orchestrator] Executing declarative graph workflow...")

        initial_state = {"orchestrator": self}

        # Step 1: Execute Tier 1 ADK Node
        s1 = await tier1_macro_node._func(initial_state)

        # Step 2: Execute Tier 2 ADK Node
        s2 = await tier2_tech_fund_node._func(s1)

        # Step 3: Execute Tier 3 ADK Node
        s3 = await tier3_portfolio_risk_node._func(s2)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ [ADK 2.0 Orchestrator] Completed in {duration:.1f}s")

        return {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 1),
            "framework": f"Google ADK {adk_version}",
            "tier1": {
                "macro": s3["macro_result"].to_dict(),
                "fred_indicators": s3["fred_result"].to_dict(),
                "holy_grail": s3["correlation_result"].to_dict(),
            },
            "tier2": {
                "technical": [r.to_dict() for r in s3["technical_results"]],
                "fundamental": [r.to_dict() for r in s3["fundamental_results"]],
            },
            "tier3": {
                "holy_grail_selections": s3["holy_grail_overlaps"],
                "status": "Risk reduction active via uncorrelated assets."
            },
            "stock_universe": s3["stock_universe"],
            "selected_sectors": s3["macro_result"].data.get("selected_sectors", []),
            "adk_workflow": {
                "name": self.workflow.name,
                "nodes": [n.name for n in self.workflow.graph.nodes],
                "edges_count": len(self.workflow.edges)
            }
        }

    def get_workflow_metadata(self) -> Dict[str, Any]:
        """Returns ADK 2.0 graph workflow topology and metadata."""
        return {
            "framework": f"Google ADK {adk_version}",
            "workflow_name": self.workflow.name,
            "nodes": [n.name for n in self.workflow.graph.nodes],
            "edges_count": len(self.workflow.edges)
        }

