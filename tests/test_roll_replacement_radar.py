import pytest
from datetime import datetime, timedelta
from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine, resolve_target_monthly_option_cycle

def test_resolve_target_monthly_option_cycle():
    today = datetime(2026, 9, 26)
    target_dt, dte = resolve_target_monthly_option_cycle(ref_date=today, min_dte=28, max_dte=35)
    assert 28 <= dte <= 35
    assert target_dt.weekday() == 4  # Friday expiration

def test_detect_near_term_expiries_and_roll_radar():
    engine = WeeklyIntelligenceEngine()
    
    # Mock positions containing an imminent expiring Google CSP (Oct 2, 2026)
    mock_positions = [
        {
            "symbol": "GOOGL",
            "asset_type": "StockOption",
            "option_type": "put",
            "amount": -1,
            "strike_price": 165.0,
            "expiry_date": "2026-10-02"
        },
        {
            "symbol": "AAPL",
            "asset_type": "Stock",
            "amount": 100,
            "strike_price": 0.0,
            "expiry_date": None
        },
        {
            "symbol": "MSFT",
            "asset_type": "StockOption",
            "option_type": "put",
            "amount": -1,
            "strike_price": 400.0,
            "expiry_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        }
    ]
    
    radar = engine.detect_near_term_expiries_and_roll_radar(positions_list=mock_positions, max_dte=14)
    
    assert radar["radar_status"] == "ROLL_TARGETS_ACTIVE"
    assert radar["expiring_positions_count"] >= 1
    assert radar["total_collateral_liberating"] >= 16500.0
    
    # Check GOOGL is in expiring positions
    googl_exp = next((p for p in radar["expiring_positions"] if p["symbol"] == "GOOGL"), None)
    assert googl_exp is not None
    assert googl_exp["strike"] == 165.0
    assert googl_exp["unlocked_collateral"] == 16500.0
    
    # Check Direct Roll candidate generated
    assert len(radar["direct_roll_candidates"]) >= 1
    roll = next((r for r in radar["direct_roll_candidates"] if r["symbol"] == "GOOGL"), None)
    assert roll is not None
    assert roll["action"] == "ROLL_EXISTING_CSP"
    assert roll["target_dte"] >= 28
    assert roll["estimated_premium"] > 0
    assert "sub_agent_verdict" in roll
    assert "financial_analyst" in roll["sub_agent_verdict"]
    assert "risk_aggregator" in roll["sub_agent_verdict"]
    assert "executive_allocator" in roll["sub_agent_verdict"]
    
    # Check Replacement Candidate generated
    assert len(radar["replacement_candidates"]) >= 1
    rep = radar["replacement_candidates"][0]
    assert rep["action"] == "REPLACE_WITH_NEW_SECTOR_CSP"
    assert rep["collateral_required"] <= googl_exp["unlocked_collateral"]
