import numpy as np
from random import gauss
from typing import Dict, Any, List, Tuple

def pricing_monte_carlo_standard(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
    num_paths: int = 10000
) -> Dict[str, Any]:
    """
    Standard Monte Carlo Option Pricing for European Call and Put.
    Simulates the asset price at maturity T directly.
    """
    # Vectorized simulation at maturity T
    Z = np.random.standard_normal(num_paths)
    ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)
    
    # Payoffs
    if option_type.lower() == "call":
        payoffs = np.maximum(ST - K, 0.0)
    else:
        payoffs = np.maximum(K - ST, 0.0)
        
    # Expected payoff under risk-neutral measure
    mean_payoff = np.mean(payoffs)
    
    # Discount back to present value
    discount_factor = np.exp(-r * T)
    price = discount_factor * mean_payoff
    
    # Standard error of the estimate
    standard_error = np.std(payoffs) / np.sqrt(num_paths)
    
    # Convergence curve for UI display (cumulative average price)
    # Take a sample of points to make the response size manageable
    cum_average = np.cumsum(payoffs) / (np.arange(num_paths) + 1)
    cum_prices = discount_factor * cum_average
    
    # Sample 100 points for graphing
    sample_indices = np.linspace(0, num_paths - 1, min(100, num_paths), dtype=int)
    convergence_curve = [
        {"iteration": int(idx + 1), "price": float(cum_prices[idx])}
        for idx in sample_indices
    ]
    
    return {
        "price": float(price),
        "standard_error": float(standard_error),
        "convergence_curve": convergence_curve,
        "option_type": option_type,
        "S0": S0,
        "K": K,
        "T": T,
        "r": r,
        "sigma": sigma
    }

def pricing_monte_carlo_lab_legacy(
    S0: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    N: int = 1000,
    iterations: int = 1000
) -> Dict[str, Any]:
    """
    Replication of the user's specific lab simulation.
    This simulates a single path step-by-step and calculates expected payoff.
    
    Note: The original lab code runs a path simulation over 'time_steps' and
    computes payoff at each time step. Let's replicate it precisely:
    """
    delta_t = T / N
    time_steps = int(T / delta_t)
    discount_factor = np.exp(-r * T)
    
    price_path = [S0]
    put_expected_payoff = []
    St = S0
    prob_space = np.arange(-50, 51, 1)
    
    # We will record the path and payoffs for educational display
    for i in range(time_steps):
        # GBM step simulation
        # Note the T in the original code: S_t = S_t * exp((r - 0.5 * sigma^2)*T + sigma * sqrt(T)*gauss(0,1))
        # Usually, this should use delta_t instead of T for step-by-step, but we use the exact lab formulation:
        St = St * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * gauss(0, 1))
        price_path.append(St)
        
        # Original lab inner loop:
        put_payoff = 0
        for prob in range(len(prob_space)):
            S_new = St * (1 + (prob - 50) * 0.01)
            if K - S_new >= 0:
                put_payoff = K - S_new
            else:
                put_payoff = 0
        put_expected_payoff.append(put_payoff)
        
    price = discount_factor * (sum(put_expected_payoff) / float(time_steps))
    
    return {
        "price": float(price),
        "price_path": price_path,
        "put_expected_payoff": put_expected_payoff,
        "formula_used": "Legacy Lab Conditional Expectation Payoff",
        "parameters": {
            "S0": S0,
            "sigma": sigma,
            "r": r,
            "T": T,
            "N": N,
            "K": K,
            "iterations": iterations
        }
    }
