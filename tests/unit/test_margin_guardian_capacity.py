import pytest
from unittest.mock import MagicMock
from options_lab.api.margin_guardian import MarginGuardian
from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine

def test_margin_guardian_capacity_exhausted_with_live_puts():
    mock_saxo = MagicMock()
    # Mock balance: total equity $150,780.66
    mock_saxo.get_balances.return_value = {
        "total_equity": 150780.66,
        "cash_available": 93443.75,
        "margin_used": 0.0,
        "balance_source": "LIVE_BROKER",
        "is_simulated": False
    }
    # Mock 5 short put positions locking $143,500 collateral
    mock_saxo.get_positions.return_value = {
        "positions": [
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 140.0, "symbol": "QCOM"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 310.0, "symbol": "COIN"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 20.0, "symbol": "INTC"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 85.0, "symbol": "NEM"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 180.0, "symbol": "GOOGL"},
        ]
    }
    # Total collateral = (140 + 310 + 20 + 85 + 180) * 100 = 735 * 100 = 73,500, wait, user's strike sum:
    # 73,500? With 2 contracts or higher strikes it reaches 143,500. Let's make strikes match 143,500:
    mock_saxo.get_positions.return_value = {
        "positions": [
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 140.0, "symbol": "QCOM"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 310.0, "symbol": "COIN"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 20.0, "symbol": "INTC"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 85.0, "symbol": "NEM"},
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 880.0, "symbol": "GOOGL"},
        ]
    } # 140+310+20+85+880 = 1435 * 100 = $143,500

    guardian = MarginGuardian(saxo_client=mock_saxo)
    status = guardian.get_current_margin_status()

    assert status["existing_locked_csp_collateral"] == 143500.0
    assert status["live_short_puts_count"] == 5
    assert status["is_capacity_exhausted"] is True
    assert status["remaining_collateral_headroom"] == 0.0

    # Test single trade rejection
    trade_eval = guardian.validate_trade_margin(strategy="CSP", strike=50.0, contracts=1, current_status=status)
    assert trade_eval["approved"] is False
    assert trade_eval["status"] == "COLLATERAL_LIMIT_EXCEEDED"

    # Test cumulative basket rejection
    basket_eval = guardian.validate_cumulative_basket(
        staged_candidates=[],
        new_candidate={"strategy": "CSP", "strike": 50.0, "contracts": 1},
        current_status=status
    )
    assert basket_eval["approved"] is False
    assert basket_eval["status"] == "COLLATERAL_LIMIT_EXCEEDED"
    assert "CUMULATIVE MARGIN CEILING EXCEEDED" in basket_eval["reasons"][0]

def test_weekly_intelligence_gating_when_capacity_exhausted():
    mock_saxo = MagicMock()
    mock_saxo.get_balances.return_value = {
        "total_equity": 150780.66,
        "cash_available": 93443.75,
        "margin_used": 0.0
    }
    mock_saxo.get_positions.return_value = {
        "positions": [
            {"asset_type": "StockOption", "option_type": "put", "amount": -1, "strike_price": 1435.0, "symbol": "TEST"}
        ]
    }
    guardian = MarginGuardian(saxo_client=mock_saxo)
    engine = WeeklyIntelligenceEngine(saxo_client=mock_saxo, margin_guardian=guardian)

    status = guardian.get_current_margin_status()
    assert status["is_capacity_exhausted"] is True

    dual_data = engine._generate_dual_mode_harvest_blotters(
        news_items=[],
        week_label="2026-W39",
        positions_list=[],
        margin_status=status
    )

    assert dual_data.get("portfolio_fully_deployed") is True
    assert len(dual_data.get("staged_trades", [])) == 0
    assert dual_data["mode_1"]["candidates_count"] == 0
    assert dual_data["mode_2"]["candidates_count"] == 0
    assert dual_data["debate_arena"]["executive_allocator"]["recommended_mode"] == "PORTFOLIO_FULLY_DEPLOYED"
    assert dual_data["debate_arena"]["risk_aggregator"]["recommendation"] == "Mandatory Capital Safety Veto: Block all new trade allocations."
