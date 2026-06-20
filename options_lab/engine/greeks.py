import numpy as np
from typing import Dict, Any, List
from .black_scholes import black_scholes_greeks

def generate_greeks_surface(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    spot_range_pct: float = 0.5,
    num_spot_steps: int = 15,
    num_time_steps: int = 15
) -> Dict[str, Any]:
    """
    Generate a 2D surface of Greeks across a range of spot prices and times to maturity.
    Useful for 3D or Heatmap charting.
    
    Parameters:
    - spot_range_pct: e.g. 0.5 means Spot ranges from 50% to 150% of S0.
    """
    spots = np.linspace(S0 * (1 - spot_range_pct), S0 * (1 + spot_range_pct), num_spot_steps)
    # Avoid T = 0 directly to prevent division by zero in analytical equations, use epsilon
    times = np.linspace(0.01, max(T, 0.1), num_time_steps)
    
    surface_data = []
    
    for t in times:
        for s in spots:
            greeks = black_scholes_greeks(s, K, t, r, sigma, option_type)
            surface_data.append({
                "spot": float(round(s, 2)),
                "time_to_expiry": float(round(t, 4)),
                "days_to_expiry": float(round(t * 365.0, 1)),
                "delta": float(round(greeks["delta"], 4)),
                "gamma": float(round(greeks["gamma"], 4)),
                "theta": float(round(greeks["theta"], 4)),
                "vega": float(round(greeks["vega"], 4)),
                "rho": float(round(greeks["rho"], 4))
            })
            
    return {
        "surface": surface_data,
        "spots": spots.tolist(),
        "times": times.tolist(),
        "days": (times * 365.0).tolist(),
        "S0": S0,
        "K": K,
        "T": T,
        "option_type": option_type
    }
