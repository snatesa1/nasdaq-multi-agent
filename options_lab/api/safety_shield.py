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
    - Circuit Breaker #5: Enforces 15% Margin Utilization Hard Cap.
    - Circuit Breaker #6: Enforces Earnings Proximity Blackout Buffer.
    """

    def __init__(self):
        self.max_single_ticker_exposure_pct = 15.0  # Max 15% of equity per stock
        self.min_dte_entry = 21                     # No selling options < 21 DTE (Gamma guard)
        self.max_dte_wheel = 32                     # Strict 30-32 DTE cap for Wheel CSP & CC
        self.max_delta_high_beta = 0.18             # Max delta on growth/momentum
        self.revenge_cooldown_hours = 24            # Lockout period after major loss
        self.max_margin_utilization_pct = 15.0      # Hard 10-15% margin utilization cap
        self.earnings_blackout_days = 7             # Expiry must not fall within ±7 days of earnings

    def evaluate_order(
        self,
        symbol: str,
        asset_type: str = "StockOption",
        buy_sell: str = "Sell",
        option_type: Optional[str] = None,
        strike: Optional[float] = None,
        delta: Optional[float] = None,
        dte: Optional[int] = None,
        order_value: float = 0.0,
        portfolio_equity: float = 100000.0,
        current_ticker_exposure: float = 0.0,
        recent_loss_amount: float = 0.0,
        recent_loss_timestamp: Optional[datetime] = None,
        beta: Optional[float] = None,
        volatility: Optional[float] = None,
        projected_margin_util_pct: float = 0.0,
        earnings_date: Optional[str] = None,
        expiry_date: Optional[str] = None,
        underlying_shares_owned: Optional[float] = None,
        contracts: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluates an order against all behavioral & risk safety rules.
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

        # 2. Gamma Expiration & Strict 30-32 DTE Wheel Guard
        if ("Option" in asset_type or option_type) and buy_sell.upper() == "SELL" and dte is not None:
            if dte < self.min_dte_entry:
                infractions.append(
                    f"GAMMA RISK VIOLATION: Selling options with {dte} DTE is prohibited (Minimum requirement: {self.min_dte_entry} DTE)."
                )
            elif dte > self.max_dte_wheel:
                infractions.append(
                    f"MAX DTE VIOLATION: Selling options with {dte} DTE exceeds strict 30-32 DTE limit (Maximum allowed: {self.max_dte_wheel} DTE)."
                )

        # 3. High-Beta / High-Volatility Call Drag Guard (Dynamic Market Risk Classification)
        # Evaluates quantitative market risk metrics (Beta >= 1.30 or Realized Volatility >= 35%)
        is_high_beta_growth = False
        if beta is not None and beta >= 1.30:
            is_high_beta_growth = True
        elif volatility is not None and volatility >= 0.35:
            is_high_beta_growth = True
        else:
            # Dynamically fetch volatility if not supplied
            try:
                from .market_data import fetch_market_data
                mkt = fetch_market_data(symbol)
                h_vol = mkt.get("historical_volatility", 0.0) if mkt else 0.0
                if h_vol >= 0.35:
                    is_high_beta_growth = True
            except Exception:
                pass

        if option_type and option_type.lower() == "put":
            is_call_option = False
        elif option_type and option_type.lower() == "call":
            is_call_option = True
        else:
            is_call_option = "Call" in asset_type or (delta is not None and delta > 0.0 and "PUT" not in asset_type.upper())
        if is_high_beta_growth and is_call_option and buy_sell.upper() == "SELL":
            if delta is not None and abs(delta) > self.max_delta_high_beta:
                infractions.append(
                    f"HIGH-BETA CALL DRAG VIOLATION: {symbol} exhibits high-beta/high-volatility momentum risk. Selling calls with Delta {delta:.2f} (Target <= {self.max_delta_high_beta}) risks severe upside capping."
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

        # 5. Margin Utilization Hard Cap (15.0%)
        if projected_margin_util_pct > self.max_margin_utilization_pct:
            infractions.append(
                f"MARGIN UTILIZATION CAP EXCEEDED: Projected utilization of {projected_margin_util_pct:.1f}% exceeds your hard limit of {self.max_margin_utilization_pct:.1f}%."
            )

        # 6. Earnings Blackout Buffer Guard
        if earnings_date and expiry_date:
            try:
                e_dt = datetime.strptime(earnings_date.split("T")[0], "%Y-%m-%d")
                exp_dt = datetime.strptime(expiry_date.split("T")[0], "%Y-%m-%d")
                diff_days = abs((exp_dt - e_dt).days)
                if diff_days <= self.earnings_blackout_days:
                    infractions.append(
                        f"EARNINGS BLACKOUT VIOLATION: Option expiry {expiry_date} is within {diff_days} days of earnings announcement ({earnings_date}). Minimum buffer is {self.earnings_blackout_days} days."
                    )
            except Exception as e_parse:
                logger.debug(f"Earnings blackout date check skipped due to date parsing: {e_parse}")

        # 7. Covered Call Underlying Share Ownership Guard
        # Selling a Call option requires owning at least 100 shares of the underlying stock per contract.
        # Otherwise, it is an unhedged/naked short call which is strictly prohibited under the Wheel strategy.
        if is_call_option and buy_sell.upper() == "SELL":
            req_shares = contracts * 100
            if underlying_shares_owned is not None and underlying_shares_owned < req_shares:
                infractions.append(
                    f"UNHEDGED SHORT CALL VIOLATION: Selling a Covered Call requires holding >= {req_shares} shares of {symbol} (Current holding: {underlying_shares_owned:.0f} shares). Selling naked calls is strictly prohibited."
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
