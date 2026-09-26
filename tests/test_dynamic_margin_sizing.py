import pytest
from options_lab.api.margin_guardian import MarginGuardian

def test_margin_guardian_estimated_slots():
    guardian = MarginGuardian()
    status = guardian.get_current_margin_status()
    assert "estimated_available_slots" in status
    assert "remaining_collateral_headroom" in status
    assert status["estimated_available_slots"] >= 0
    assert status["estimated_available_slots"] <= 5

def test_cumulative_basket_margin_enforcement():
    guardian = MarginGuardian()
    status = guardian.get_current_margin_status()
    
    # Test valid small candidate
    cand_small = {"strategy": "CSP", "strike": 30.0, "contracts": 1, "symbol": "KO"}
    res_small = guardian.validate_cumulative_basket([], new_candidate=cand_small, current_status=status)
    assert res_small["approved"] is True

    # Test giant candidate exceeding collateral
    cand_huge = {"strategy": "CSP", "strike": 5000.0, "contracts": 10, "symbol": "HUGE"}
    res_huge = guardian.validate_cumulative_basket([], new_candidate=cand_huge, current_status=status)
    assert res_huge["approved"] is False
    assert res_huge["status"] in ["COLLATERAL_LIMIT_EXCEEDED", "MARGIN_LIMIT_EXCEEDED"]
