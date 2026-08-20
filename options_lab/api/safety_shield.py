import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("safety-shield")


class BehavioralSafetyShield:
    """
    Real-Time Behavioral Circuit-Breaker & Execution Safety Shield.
    
    Translates historical behavioral forensics into hard automated execution constraints:
    - Blocks aggressive short call caps on explosive growth stocks.
    - Prevents revenge trading surges following drawdowns.
    - Enforces 21-DTE gamma rules and portfolio concentration caps.
    """

    def __init__(self):
        self.max_single_ticker_exposure_pct = 15.0  # Max 15% of equity per stock
        self.min_dte_entry = 21                     # No selling options < 21 DTE
        self.max_delta_high_beta = 0.18             # Max delta on growth/momentum
        self.revenge_cooldown_hours = 24            # Lockout period after major loss

    def evaluate_order(
        self,
        symbol: str,
        asset_type: str,
        buy_sell: str,
        strike: Optional[float] = None,
        delta: Optional[float] = None,
        dte: Optional[int] = None,
        order_value: float = 0.0,
        portfolio_equity: float = 100000.0,
        current_ticker_exposure: float = 0.0,
        recent_loss_amount: float = 0.0,
        recent_loss_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates an order against all behavioral safety rules.
        Returns {'approved': True/False, 'status': 'PASSED'|'BLOCKED', 'infractions': [...], 'warnings': [...]}
        """
        infractions = []
        warnings = []

        # 1. Revenge Trading Check
        if recent_loss_amount > 1000.0 and recent_loss_timestamp:
            elapsed = datetime.now() - recent_loss_timestamp
            if elapsed < timedelta(hours=self.revenge_cooldown_hours):
                remaining_hrs = round((timedelta(hours=self.revenge_cooldown_hours) - elapsed).total_seconds() / 3600, 1)
                infractions.append(
                    f"REVENGE TRADING COOLDOWN: Major loss of ${recent_loss_amount:,.2f} recorded. Execution locked for {remaining_hrs} more hours to prevent emotional sizing."
                )

        # 2. Gamma Expiration Guard
        if "Option" in asset_type and buy_sell.upper() == "SELL" and dte is not None:
            if dte < self.min_dte_entry:
                infractions.append(
                    f"GAMMA RISK VIOLATION: Selling options with {dte} DTE is prohibited (Minimum requirement: {self.min_dte_entry} DTE)."
                )

        # 3. High-Beta Call Drag Guard (PANW / AMZN Prevention)
        high_beta_growth_tickers = ["PANW", "NVDA", "TSLA", "PLTR", "AMZN", "COIN", "RBLX", "AMD"]
        if symbol.upper() in high_beta_growth_tickers and "Call" in asset_type and buy_sell.upper() == "SELL":
            if delta is not None and abs(delta) > self.max_delta_high_beta:
                infractions.append(
                    f"HIGH-BETA CALL DRAG VIOLATION: {symbol} is a high-beta growth asset. Selling calls with Delta {delta:.2f} (Target ≤ {self.max_delta_high_beta}) risks severe upside capping."
                )

        # 4. Concentration Risk Cap
        new_total_exposure = current_ticker_exposure + order_value
        exposure_pct = (new_total_exposure / portfolio_equity * 100.0) if portfolio_equity > 0 else 0.0
        if exposure_pct > self.max_single_ticker_exposure_pct:
            infractions.append(
                f"CONCENTRATION CAP EXCEEDED: New exposure for {symbol} would reach {exposure_pct:.1f}% (Hard Limit: {self.max_single_ticker_exposure_pct}%)."
            )
        elif exposure_pct > 10.0:
            warnings.append(
                f"Concentration Warning: {symbol} exposure approaching threshold at {exposure_pct:.1f}%."
            )

        # Final Decision
        approved = len(infractions) == 0
        return {
            "approved": approved,
            "status": "APPROVED" if approved else "BLOCKED",
            "symbol": symbol,
            "infractions": infractions,
            "warnings": warnings,
            "evaluated_at": datetime.now().isoformat()
        }
