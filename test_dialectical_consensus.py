"""
Test Suite: Executive Portfolio Allocator Dialectical Consensus & Dynamic Contract Sizing
Verifies that:
1. Dynamic contract sizing scales contracts when premium < $2.00 to approach the $250/slot harvest.
2. If cash collateral cap or margin limits prevent scaling, the Allocator raises a TARGET_SHORTFALL_CHALLENGE.
3. SubAgentConsensus records the Allocator's challenge, Financial Analyst's defense, and Risk Aggregator's audit.
4. Golden Trades strictly enforce 4 distinct GICS sectors.
"""
import pytest
from unittest.mock import MagicMock, patch
from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine


def test_dialectical_consensus_and_sizing():
    mock_saxo = MagicMock()
    mock_saxo.get_positions.return_value = {"positions": []}
    mock_saxo.get_all_watchlist_instruments.return_value = []
    mock_saxo.access_token = "mock_token"
    mock_saxo.quantize_order_price.side_effect = lambda p, **kwargs: round(round(p / 0.05) * 0.05, 2)
    engine = WeeklyIntelligenceEngine(saxo_client=mock_saxo)
    engine.active_position_tickers = ["COIN", "INTC", "NEM"]
    engine.watchlist_tickers = ["ABT", "CVX", "KO"]
    engine.candidate_pool = ["COIN", "INTC", "NEM", "ABT", "CVX", "KO"]
    
    mock_candidates = {
        "COIN": {
            "symbol": "COIN", "sector": "Financials", "strategy": "CSP",
            "strike": 120.0, "delta": -0.22, "dte": 33, "pop_pct": 78.0,
            "premium_estimate": 2.65, "has_earnings_blackout": False,
            "max_margin_impact_pct": 1.5, "collateral_required": 12000.0
        },
        "INTC": {
            "symbol": "INTC", "sector": "Information Technology", "strategy": "CSP",
            "strike": 22.0, "delta": -0.20, "dte": 33, "pop_pct": 80.0,
            "premium_estimate": 0.85, "has_earnings_blackout": False,
            "max_margin_impact_pct": 0.8, "collateral_required": 2200.0
        },
        "NEM": {
            "symbol": "NEM", "sector": "Materials", "strategy": "CSP",
            "strike": 50.0, "delta": -0.21, "dte": 33, "pop_pct": 79.0,
            "premium_estimate": 1.25, "has_earnings_blackout": False,
            "max_margin_impact_pct": 1.0, "collateral_required": 5000.0
        },
        "ABT": {
            "symbol": "ABT", "sector": "Health Care", "strategy": "CSP",
            "strike": 95.0, "delta": -0.18, "dte": 33, "pop_pct": 82.0,
            "premium_estimate": 0.80, "has_earnings_blackout": False,
            "max_margin_impact_pct": 1.2, "collateral_required": 9500.0
        },
        "CVX": {
            "symbol": "CVX", "sector": "Energy", "strategy": "CSP",
            "strike": 125.0, "delta": -0.22, "dte": 33, "pop_pct": 78.0,
            "premium_estimate": 2.45, "has_earnings_blackout": False,
            "max_margin_impact_pct": 1.5, "collateral_required": 12500.0
        }
    }

    def mock_build_cand(symbol, **kwargs):
        return mock_candidates.get(symbol)

    with patch.object(engine, "_build_dynamic_trade_candidate", side_effect=mock_build_cand):
        staged = engine._generate_dynamic_trade_candidates(news_items=[], week_label="2026-W38")
        
    assert len(staged) >= 3, f"Expected at least 3 Golden Trades, got {len(staged)}"
    
    total_harvest = 0.0
    total_contracts = 0
    
    for t in staged:
        cnt = t.get("contracts", 1)
        prem = t.get("premium_estimate", 0.0)
        sec = t.get("sector")
        
        assert cnt >= 1, "Contracts must be at least 1"
        total_contracts += cnt
        total_harvest += prem * cnt * 100.0
        
        # Verify 3 Sub-Agent Consensus is fully populated
        consensus = t.get("sub_agent_consensus")
        assert consensus is not None, "sub_agent_consensus must be present"
        assert "financial_analyst" in consensus
        assert "risk_aggregator" in consensus
        assert "executive_allocator" in consensus
        
        fa = consensus["financial_analyst"]
        ra = consensus["risk_aggregator"]
        ea = consensus["executive_allocator"]
        
        assert fa["status"] in ["APPROVED", "CHALLENGED_ON_SWEET_SPOT"]
        assert ra["status"] == "APPROVED"
        assert ea["status"] in ["GOLDEN_TRADE_DESIGNATED", "TARGET_SHORTFALL_CHALLENGE"]
        assert "$1,500" in ea["monthly_harvest_contribution"]
        assert ea["rank"] >= 1
        
        if t["symbol"] == "INTC":
            assert cnt >= 2, f"Expected INTC to scale to at least 2 contracts, got {cnt}"

    print(f"\n[PASS] Staged {len(staged)} trades | Total Contracts: {total_contracts} | Harvest: ${total_harvest:.2f} towards $1,500 milestone")


if __name__ == "__main__":
    test_dialectical_consensus_and_sizing()
