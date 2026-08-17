"""
Wheel State Machine Engine for the Saxo Options Yield Protocol.

Implements a deterministic 2-state state machine:
- STATE_0_CASH_CSP: Cash heavy -> Write Cash-Secured Puts (Delta -0.20 to -0.30, 30-45 DTE)
- STATE_1_EQUITY_CC: Shares assigned -> Write Covered Calls (Delta +0.25 to +0.30, Strike >= Cost Basis)

Enforces institutional quantitative management rules:
1. 50% Profit Target Rule: Capture 50% max profit early to free collateral.
2. 21-DTE Gamma Avoidance Rule: Roll/Close at 21 DTE to eliminate tail risk.
3. Pre-Trade Risk Guards: Max 5% capital allocation per position, earnings buffer.
"""

import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WheelState(str, Enum):
    CASH_READY = "STATE_0_CASH_CSP"
    HOLDING_SHARES = "STATE_1_EQUITY_CC"
    POSITION_OPEN = "STATE_2_MONITORING"


@dataclass
class WheelPosition:
    symbol: str
    state: WheelState
    entry_date: str
    option_type: str           # "put" or "call"
    strike: float
    premium_received: float
    dte_at_entry: int
    expiry_date: str
    shares_held: int = 0
    cost_basis: float = 0.0    # Assignment strike minus net accumulated premiums
    current_option_price: float = 0.0
    saxo_position_id: Optional[str] = None
    saxo_order_id: Optional[str] = None


class WheelEngine:
    """
    Deterministic Wheel state machine and risk governance engine.
    """

    MAX_PORTFOLIO_ALLOCATION_PCT = 0.05   # 5% max capital per underlying
    PROFIT_TARGET_PCT = 0.50             # 50% profit-taking target
    GAMMA_DTE_THRESHOLD = 21             # 21 DTE roll threshold
    EARNINGS_BUFFER_DAYS = 7             # Exclude expiries +-7 days from earnings

    def __init__(self):
        pass

    def evaluate_wheel_state(
        self,
        symbol: str,
        cash_balance: float,
        existing_shares: int = 0,
        existing_position: Optional[WheelPosition] = None
    ) -> WheelState:
        """
        Determines current Wheel state for a ticker symbol.
        """
        if existing_position and existing_position.saxo_position_id:
            return WheelState.POSITION_OPEN
        elif existing_shares >= 100:
            return WheelState.HOLDING_SHARES
        else:
            return WheelState.CASH_READY

    def check_profit_target(self, position: WheelPosition, current_price: float) -> Dict[str, Any]:
        """
        50% Profit-Taking Rule:
        If current option price <= 50% of premium_received,
        close the position immediately to lock in profit.
        """
        premium = position.premium_received
        if premium <= 0:
            return {"trigger": False, "action": "HOLD", "profit_pct": 0.0}

        unrealized_profit = premium - current_price
        profit_pct = (unrealized_profit / premium)

        if profit_pct >= self.PROFIT_TARGET_PCT:
            return {
                "trigger": True,
                "action": "CLOSE_50_PERCENT_PROFIT",
                "profit_pct": round(profit_pct * 100, 1),
                "unrealized_profit_dollars": round(unrealized_profit * 100, 2), # 1 contract = 100 shares
                "rationale": f"Captured {profit_pct * 100:.1f}% of max profit (>= 50% target). Close position."
            }

        return {
            "trigger": False,
            "action": "HOLD",
            "profit_pct": round(profit_pct * 100, 1),
            "unrealized_profit_dollars": round(unrealized_profit * 100, 2),
            "rationale": f"Unrealized profit {profit_pct * 100:.1f}% is below 50% target threshold."
        }

    def check_dte_roll(self, position: WheelPosition, current_dte: int) -> Dict[str, Any]:
        """
        21-DTE Gamma Avoidance Rule:
        If remaining DTE <= 21 days, close or roll to avoid accelerated gamma risks.
        """
        if current_dte <= self.GAMMA_DTE_THRESHOLD:
            return {
                "trigger": True,
                "action": "ROLL_21_DTE_GAMMA_AVOIDANCE",
                "current_dte": current_dte,
                "target_roll_dte": 35,
                "rationale": f"Remaining DTE ({current_dte}d) is <= 21d threshold. Roll to 35 DTE cycle."
            }

        return {
            "trigger": False,
            "action": "HOLD",
            "current_dte": current_dte,
            "rationale": f"Remaining DTE ({current_dte}d) is safe (> 21d threshold)."
        }

    def validate_pre_trade_risk_guards(
        self,
        symbol: str,
        state: WheelState,
        portfolio_value: float,
        collateral_required: float,
        conviction_score: float,
        signal_score: float,
        proposed_strike: float,
        cost_basis: float = 0.0,
        earnings_date: Optional[str] = None,
        expiry_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pre-Trade Risk Validation:
        1. Max 5% capital per trade
        2. Minimum conviction score >= 0.60
        3. Minimum signal score >= 0.55
        4. For Covered Calls: Strike >= cost basis
        5. Earnings buffer +-7 days
        """
        violations = []

        # 1. Capital cap check
        allocation_pct = (collateral_required / portfolio_value) if portfolio_value > 0 else 1.0
        if allocation_pct > self.MAX_PORTFOLIO_ALLOCATION_PCT:
            violations.append(
                f"Collateral requirement (${collateral_required:,.2f}) is {allocation_pct*100:.1f}% "
                f"of portfolio (exceeds max {self.MAX_PORTFOLIO_ALLOCATION_PCT*100:.0f}% cap)."
            )

        # 2. Conviction check
        if conviction_score < 0.60:
            violations.append(f"Conviction score ({conviction_score:.2f}) is below minimum threshold (0.60).")

        # 3. Signal check
        if signal_score < 0.55:
            violations.append(f"Signal score ({signal_score:.2f}) is below minimum threshold (0.55).")

        # 4. Covered Call strike safety
        if state == WheelState.HOLDING_SHARES and cost_basis > 0 and proposed_strike < cost_basis:
            violations.append(
                f"Proposed CC strike (${proposed_strike:.2f}) is below adjusted cost basis (${cost_basis:.2f})."
            )

        # 5. Earnings proximity check
        if earnings_date and expiry_date:
            try:
                dt_earn = datetime.strptime(earnings_date, "%Y-%m-%d")
                dt_exp = datetime.strptime(expiry_date, "%Y-%m-%d")
                days_diff = abs((dt_exp - dt_earn).days)
                if days_diff <= self.EARNINGS_BUFFER_DAYS:
                    violations.append(
                        f"Expiry date ({expiry_date}) is within {days_diff} days of earnings release ({earnings_date})."
                    )
            except Exception:
                pass

        approved = len(violations) == 0

        return {
            "approved": approved,
            "symbol": symbol,
            "state": state.value,
            "allocation_pct": round(allocation_pct * 100, 2),
            "conviction_score": conviction_score,
            "signal_score": signal_score,
            "violations": violations,
            "decision": "APPROVED_FOR_EXECUTION" if approved else "REJECTED_BY_RISK_GUARDS"
        }

    def construct_saxo_order_payload(
        self,
        option_uic: int,
        option_type: str,
        strike: float,
        expiry_date: str,
        limit_price: float,
        amount: int = 1,
        buy_sell: str = "Sell"
    ) -> Dict[str, Any]:
        """
        Constructs Saxo OpenAPI POST /trade/v2/orders payload.
        """
        return {
            "Uic": option_uic,
            "AssetType": "StockOption",
            "Amount": amount,
            "BuySell": buy_sell,
            "OrderType": "Limit",
            "OrderPrice": round(limit_price, 2),
            "OrderDuration": {"DurationType": "DayOrder"},
            "ManualOrder": True,
            "OrderRelation": "StandAlone",
        }
