import numpy as np
from typing import List, Dict, Any, Optional
from .black_scholes import black_scholes_price

class StrategyLeg:
    def __init__(
        self,
        asset_type: str,  # "stock" or "option"
        option_type: Optional[str] = None,  # "call" or "put" (if option)
        position: str = "long",  # "long" or "short"
        strike: Optional[float] = None,
        expiry: Optional[float] = None,  # in years
        entry_price: float = 0.0,
        quantity: int = 1
    ):
        self.asset_type = asset_type.lower()
        self.option_type = option_type.lower() if option_type else None
        self.position = position.lower()
        self.strike = strike
        self.expiry = expiry
        self.entry_price = entry_price
        self.quantity = quantity

    def calculate_pl_at_expiry(self, S_T: float) -> float:
        """
        Calculate P&L of a single leg at its expiration.
        """
        multiplier = 100 if self.asset_type == "option" else 1
        qty_signed = self.quantity if self.position == "long" else -self.quantity
        
        if self.asset_type == "stock":
            # Stock P&L
            return qty_signed * (S_T - self.entry_price) * multiplier
            
        elif self.asset_type == "option":
            # Option payoff at maturity
            if self.option_type == "call":
                payoff = max(S_T - self.strike, 0.0)
            elif self.option_type == "put":
                payoff = max(self.strike - S_T, 0.0)
            else:
                payoff = 0.0
                
            # Net P&L = (Payoff - Premium Paid/Received) * Qty * 100
            # For long, we paid premium (negative flow). For short, we received premium (positive flow).
            if self.position == "long":
                return qty_signed * (payoff - self.entry_price) * multiplier
            else:
                # Qty signed is negative, so: -Qty * (payoff - premium) = Qty * (premium - payoff)
                return qty_signed * (payoff - self.entry_price) * multiplier
                
        return 0.0

    def calculate_value_t(
        self,
        S: float,
        t: float,  # Current time (years)
        r: float,
        sigma: float
    ) -> float:
        """
        Calculate market value of the leg at time t (where t <= expiry).
        """
        if self.asset_type == "stock":
            return S * self.quantity * (1 if self.position == "long" else -1)
            
        elif self.asset_type == "option":
            time_to_maturity = max(self.expiry - t, 0.0)
            opt_price = black_scholes_price(S, self.strike, time_to_maturity, r, sigma, self.option_type)
            multiplier = 100
            qty_signed = self.quantity if self.position == "long" else -self.quantity
            return qty_signed * opt_price * multiplier
            
        return 0.0

def simulate_strategy_payoff(
    legs_data: List[Dict[str, Any]],
    underlying_spot: float,
    r: float,
    sigma: float,
    price_range_pct: float = 0.4,
    steps: int = 50,
    time_to_expiry_pcts: List[float] = [0.0, 0.5, 1.0] # 1.0 = today (entry), 0.5 = midway, 0.0 = expiry
) -> Dict[str, Any]:
    """
    Simulate the composite P&L of a multi-leg strategy across different spot prices.
    
    legs_data keys:
    - asset_type: "stock" or "option"
    - option_type: "call" or "put" (optional)
    - position: "long" or "short"
    - strike: float (optional)
    - expiry: float (optional, years)
    - entry_price: float (market price/premium at entry)
    - quantity: int
    """
    legs = []
    max_expiry = 0.0
    net_premium = 0.0 # positive = net credit, negative = net debit
    
    for l in legs_data:
        leg = StrategyLeg(
            asset_type=l["asset_type"],
            option_type=l.get("option_type"),
            position=l["position"],
            strike=l.get("strike"),
            expiry=l.get("expiry"),
            entry_price=l["entry_price"],
            quantity=l.get("quantity", 1)
        )
        legs.append(leg)
        if leg.expiry and leg.expiry > max_expiry:
            max_expiry = leg.expiry
            
        # Cost tracking
        multiplier = 100 if leg.asset_type == "option" else 1
        flow = leg.entry_price * leg.quantity * multiplier
        if leg.position == "long":
            net_premium -= flow
        else:
            net_premium += flow

    # Generate spot price grid
    spots = np.linspace(underlying_spot * (1 - price_range_pct), underlying_spot * (1 + price_range_pct), steps)
    
    # Calculate P&L matrix for each time slice
    # P&L structure: List of dicts, each containing:
    # {"spot": S, "t_expiry": P&L, "t_half": P&L, "t_entry": P&L}
    plot_data = []
    
    # Max profit, loss and breakevens are calculated numerically over the spot grid at expiry
    expiry_pls = []
    
    for s in spots:
        row = {"spot": float(round(s, 2))}
        
        # Payoff at Expiry (t = max_expiry)
        expiry_pl = sum(leg.calculate_pl_at_expiry(s) for leg in legs)
        row["expiry_pl"] = float(round(expiry_pl, 2))
        expiry_pls.append(expiry_pl)
        
        # P&L before expiry (using Black-Scholes pricing)
        # Entry value
        entry_val = sum(leg.calculate_value_t(underlying_spot, 0.0, r, sigma) for leg in legs)
        
        # Midway value (t = max_expiry * 0.5)
        t_mid = max_expiry * 0.5
        mid_val = sum(leg.calculate_value_t(s, t_mid, r, sigma) for leg in legs)
        # P&L at midway = Current Value - Entry Cost
        # Since Entry value has signs incorporated: Long options have positive value, shorts have negative.
        # So P&L = Value(t) - Value(0)
        row["midway_pl"] = float(round(mid_val - entry_val, 2))
        
        # T-minus-one day or close to entry (t = max_expiry * 0.9)
        t_early = max_expiry * 0.1
        early_val = sum(leg.calculate_value_t(s, t_early, r, sigma) for leg in legs)
        row["early_pl"] = float(round(early_val - entry_val, 2))
        
        plot_data.append(row)

    # Risk metrics estimation based on expiry P&L grid
    expiry_pls = np.array(expiry_pls)
    max_profit = float(np.max(expiry_pls))
    max_loss = float(np.min(expiry_pls))
    
    # Check if max profit/loss is unbounded (look at endpoints)
    is_profit_unbounded = expiry_pls[0] > expiry_pls[1] and expiry_pls[0] > underlying_spot or expiry_pls[-1] > expiry_pls[-2] and expiry_pls[-1] > underlying_spot
    is_loss_unbounded = expiry_pls[0] < expiry_pls[1] or expiry_pls[-1] < expiry_pls[-2]
    
    # Breakeven points (where P&L changes sign)
    breakevens = []
    for i in range(len(spots) - 1):
        pl1, pl2 = expiry_pls[i], expiry_pls[i+1]
        if pl1 * pl2 < 0: # Crossed zero
            # Linear interpolation
            cross_spot = spots[i] - pl1 * (spots[i+1] - spots[i]) / (pl2 - pl1)
            breakevens.append(float(round(cross_spot, 2)))
            
    # Margin requirements (simple logic for educational alerts)
    margin_required = 0.0
    has_naked_short = False
    
    for leg in legs:
        if leg.asset_type == "option" and leg.position == "short":
            has_naked_short = True
            # Basic margin calculation for short call/put (simplified Rule 431 NYSE)
            # Short Option Margin = Option Premium + Max(20% of Spot - OTM Amount, 10% of Strike)
            if leg.option_type == "call":
                otm = max(leg.strike - underlying_spot, 0)
                margin_required += (leg.entry_price + max(0.20 * underlying_spot - otm, 0.10 * leg.strike)) * 100 * leg.quantity
            else:
                otm = max(underlying_spot - leg.strike, 0)
                margin_required += (leg.entry_price + max(0.20 * underlying_spot - otm, 0.10 * leg.strike)) * 100 * leg.quantity

    return {
        "payoff_grid": plot_data,
        "max_profit": "Unlimited" if is_profit_unbounded else max_profit,
        "max_loss": "Unlimited" if is_loss_unbounded else max_loss,
        "breakevens": breakevens,
        "net_premium": float(round(net_premium, 2)),
        "margin_required": float(round(margin_required, 2)),
        "has_naked_short": has_naked_short
    }
