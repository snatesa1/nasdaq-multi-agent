import numpy as np
from typing import Dict, Any, List

def simulate_gbm(
    S0: float,
    mu: float,
    sigma: float,
    T: float,
    N: int,
    num_paths: int
) -> Dict[str, Any]:
    """
    Simulate asset price paths using Geometric Brownian Motion (GBM).
    Formula: S_t = S_0 * exp((mu - 0.5 * sigma^2) * t + sigma * W_t)
    
    Parameters:
    - S0: Initial stock price
    - mu: Drift coefficient (annualized rate of return / risk-free rate)
    - sigma: Volatility coefficient (annualized)
    - T: Time to maturity (years, e.g. 100/365.0)
    - N: Number of time steps
    - num_paths: Number of simulated trajectories
    
    Returns:
    - paths: A list of lists containing the simulated price paths
    - time_grid: List of time steps
    - terminal_prices: List of prices at maturity (t=T)
    """
    dt = T / N
    time_grid = np.linspace(0, T, N + 1).tolist()
    
    # Generate random standard normal increments
    # Shape: (N, num_paths)
    Z = np.random.standard_normal((N, num_paths))
    
    # Calculate increments
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * Z
    
    # Log returns
    log_returns = drift + diffusion
    
    # Cumulative log returns
    cum_log_returns = np.vstack([np.zeros(num_paths), np.cumsum(log_returns, axis=0)])
    
    # Price paths
    # Shape: (N + 1, num_paths)
    paths = S0 * np.exp(cum_log_returns)
    
    # Transpose to shape (num_paths, N + 1) for easier frontend ingestion
    paths_list = paths.T.tolist()
    terminal_prices = paths[-1].tolist()
    
    return {
        "paths": paths_list,
        "time_grid": time_grid,
        "terminal_prices": terminal_prices,
        "S0": S0,
        "mu": mu,
        "sigma": sigma,
        "T": T,
        "N": N,
        "num_paths": num_paths
    }
