import numpy as np
from typing import Dict, Any, List
from .black_scholes import black_scholes_price, black_scholes_greeks, implied_volatility

def generate_volatility_surface(
    spot_price: float,
    base_sigma: float = 0.25,
    risk_free_rate: float = 0.05,
    strike_ratios: List[float] = None,
    expirations_days: List[int] = None,
    skew_intensity: float = 0.15,
    smile_convexity: float = 0.10
) -> Dict[str, Any]:
    """
    Constructs a 3D Volatility Surface and Volatility Smile/Skew mesh.
    
    Parameters:
    - spot_price: Current underlying asset spot price ($S_0$)
    - base_sigma: At-the-Money (ATM) volatility baseline
    - risk_free_rate: Annualized risk-free interest rate
    - strike_ratios: List of strike ratios relative to spot price (e.g. [0.8, 0.9, 1.0, 1.1, 1.2])
    - expirations_days: List of times to expiration in days (e.g. [14, 30, 60, 90, 180, 365])
    - skew_intensity: Put-skew slope intensity (downside put demand)
    - smile_convexity: Out-of-the-Money (OTM) wings curvature
    """
    if strike_ratios is None:
        strike_ratios = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
        
    if expirations_days is None:
        expirations_days = [7, 14, 30, 60, 90, 120, 180, 365]

    strikes = [round(spot_price * r, 2) for r in strike_ratios]
    
    # 2D Grid matrices
    iv_matrix = []
    price_matrix = []
    delta_matrix = []

    for days in expirations_days:
        T = max(days / 365.0, 0.001)
        row_ivs = []
        row_prices = []
        row_deltas = []
        
        # Term structure factor: IV skew flattens slightly with longer expiration
        term_factor = 1.0 / np.sqrt(T * 12.0)
        term_factor = float(np.clip(term_factor, 0.5, 2.0))

        for ratio, K in zip(strike_ratios, strikes):
            log_moneyness = np.log(K / spot_price)
            
            # Parametric Volatility Smile / Skew model (Gatheral SVI approximation)
            # Skew component: Negative slope for OTM Puts (log_moneyness < 0)
            # Smile component: Convex quadratic wings for OTM Calls and Puts
            skew_term = -skew_intensity * log_moneyness * term_factor
            smile_term = smile_convexity * (log_moneyness ** 2) * term_factor
            
            node_iv = max(0.05, base_sigma + skew_term + smile_term)
            
            # Price option and get Greeks
            call_price = black_scholes_price(spot_price, K, T, risk_free_rate, node_iv, "call")
            greeks = black_scholes_greeks(spot_price, K, T, risk_free_rate, node_iv, "call")
            
            row_ivs.append(round(node_iv, 4))
            row_prices.append(round(call_price, 4))
            row_deltas.append(round(greeks["delta"], 4))
            
        iv_matrix.append(row_ivs)
        price_matrix.append(row_prices)
        delta_matrix.append(row_deltas)

    # ATM Term Structure (Smile slice at K = spot_price)
    atm_idx = strike_ratios.index(1.00) if 1.00 in strike_ratios else len(strike_ratios) // 2
    term_structure = [
        {"days": d, "term_years": round(d/365.0, 3), "atm_iv": iv_matrix[i][atm_idx]}
        for i, d in enumerate(expirations_days)
    ]

    # Volatility Smile slice for 30-day expiration
    d30_idx = expirations_days.index(30) if 30 in expirations_days else 2
    vol_smile_30d = [
        {"strike": K, "strike_ratio": strike_ratios[i], "iv": iv_matrix[d30_idx][i]}
        for i, K in enumerate(strikes)
    ]

    return {
        "spot_price": spot_price,
        "base_sigma": base_sigma,
        "strikes": strikes,
        "strike_ratios": strike_ratios,
        "expirations_days": expirations_days,
        "iv_matrix": iv_matrix,
        "price_matrix": price_matrix,
        "delta_matrix": delta_matrix,
        "term_structure": term_structure,
        "vol_smile_30d": vol_smile_30d
    }
