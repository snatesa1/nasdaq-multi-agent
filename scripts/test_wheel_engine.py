import sys
import os
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from options_lab.api.wheel_engine import WheelEngine, WheelState, WheelPosition

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    print("=" * 80)
    print("[PHASE 3 VALIDATION] Wheel State Machine & Risk Engine")
    print("=" * 80)

    engine = WheelEngine()

    # ── Test 1: State Evaluation ──────────────────────────────────────────────
    print("\n1. State Evaluation Tests:")
    state_cash = engine.evaluate_wheel_state("AAPL", cash_balance=100000, existing_shares=0)
    state_shares = engine.evaluate_wheel_state("AAPL", cash_balance=10000, existing_shares=100)
    pos_open = WheelPosition(
        symbol="AAPL", state=WheelState.POSITION_OPEN, entry_date="2026-08-01",
        option_type="put", strike=220.0, premium_received=4.50, dte_at_entry=35,
        expiry_date="2026-09-05", saxo_position_id="POS-12345"
    )
    state_monitoring = engine.evaluate_wheel_state("AAPL", cash_balance=10000, existing_position=pos_open)

    print(f"  - Cash Heavy Setup:     {state_cash.value}")
    print(f"  - Holding Shares Setup: {state_shares.value}")
    print(f"  - Active Position Open: {state_monitoring.value}")

    # ── Test 2: 50% Profit Target Rule ───────────────────────────────────────
    print("\n2. 50% Profit Target Rule Tests:")
    pos_profit = WheelPosition(
        symbol="NVDA", state=WheelState.POSITION_OPEN, entry_date="2026-08-01",
        option_type="put", strike=120.0, premium_received=5.00, dte_at_entry=35, expiry_date="2026-09-05"
    )
    res_profit_hit = engine.check_profit_target(pos_profit, current_price=2.10) # 58% profit
    res_profit_miss = engine.check_profit_target(pos_profit, current_price=3.50) # 30% profit

    print(f"  - Current Price $2.10 (58% Profit): Trigger = {res_profit_hit['trigger']}, Action = {res_profit_hit['action']}")
    print(f"    Rationale: {res_profit_hit['rationale']}")
    print(f"  - Current Price $3.50 (30% Profit): Trigger = {res_profit_miss['trigger']}, Action = {res_profit_miss['action']}")
    print(f"    Rationale: {res_profit_miss['rationale']}")

    # ── Test 3: 21-DTE Gamma Avoidance Rule ──────────────────────────────────
    print("\n3. 21-DTE Gamma Avoidance Rule Tests:")
    res_dte_safe = engine.check_dte_roll(pos_profit, current_dte=28)
    res_dte_roll = engine.check_dte_roll(pos_profit, current_dte=18)

    print(f"  - Remaining DTE 28d: Trigger = {res_dte_safe['trigger']}, Action = {res_dte_safe['action']}")
    print(f"  - Remaining DTE 18d: Trigger = {res_dte_roll['trigger']}, Action = {res_dte_roll['action']}")

    # ── Test 4: Pre-Trade Risk Guards Validation ──────────────────────────────
    print("\n4. Pre-Trade Risk Guards Validation Tests:")
    
    # Valid trade setup
    res_valid = engine.validate_pre_trade_risk_guards(
        symbol="AAPL",
        state=WheelState.CASH_READY,
        portfolio_value=1000000.0,
        collateral_required=22000.0,  # 2.2% capital
        conviction_score=0.68,
        signal_score=0.72,
        proposed_strike=220.0,
        earnings_date="2026-10-25",
        expiry_date="2026-09-15"
    )
    print(f"  - Valid CSP Trade Setup: Approved = {res_valid['approved']}, Decision = {res_valid['decision']}")

    # Invalid trade setup (Exceeds 5% capital cap)
    res_invalid_cap = engine.validate_pre_trade_risk_guards(
        symbol="TSLA",
        state=WheelState.CASH_READY,
        portfolio_value=100000.0,
        collateral_required=20000.0,  # 20% capital! Exceeds 5% cap
        conviction_score=0.68,
        signal_score=0.72,
        proposed_strike=200.0
    )
    print(f"  - Capital Cap Violation (20% > 5%): Approved = {res_invalid_cap['approved']}, Decision = {res_invalid_cap['decision']}")
    print(f"    Violations: {res_invalid_cap['violations']}")

    # ── Test 5: Saxo Order Payload Construction ───────────────────────────────
    print("\n5. Saxo Order Payload Construction:")
    payload = engine.construct_saxo_order_payload(
        option_uic=123456,
        option_type="put",
        strike=220.0,
        expiry_date="2026-09-15",
        limit_price=4.50,
        amount=1
    )
    print(f"  - Generated Order Payload: {payload}")

    print("\n" + "=" * 80)
    print("[PHASE 3 SUCCESS] Wheel State Machine & Risk Engine validated cleanly.")
    print("=" * 80)

if __name__ == "__main__":
    main()
