import numpy as np
from typing import Dict, Any

def std_normal_pdf(x: float) -> float:
    """Standard Normal probability density function."""
    return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)

def std_normal_cdf(x: float) -> float:
    """
    Standard Normal cumulative distribution function.
    Uses Abramowitz and Stegun (1964) approximation (formula 26.2.17).
    Maximum error: 7.5e-8.
    """
    abs_x = abs(x)
    p = 0.2316419
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429
    
    t = 1.0 / (1.0 + p * abs_x)
    Z = std_normal_pdf(abs_x)
    
    cdf_abs = 1.0 - Z * (b1 * t + b2 * t**2 + b3 * t**3 + b4 * t**4 + b5 * t**5)
    
    if x >= 0:
        return float(cdf_abs)
    else:
        return float(1.0 - cdf_abs)


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call"
) -> float:
    """
    Calculate the analytical Black-Scholes price for European options.
    """
    if T <= 0:
        if option_type.lower() == "call":
            return max(0.0, S - K)
        else:
            return max(0.0, K - S)
            
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == "call":
        price = S * std_normal_cdf(d1) - K * np.exp(-r * T) * std_normal_cdf(d2)
    elif option_type.lower() == "put":
        price = K * np.exp(-r * T) * std_normal_cdf(-d2) - S * std_normal_cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

        
    return float(price)

def black_scholes_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call"
) -> Dict[str, float]:
    """
    Calculate analytical Greeks for European Call and Put options.
    - Delta: Price sensitivity to underlying spot price.
    - Gamma: Delta sensitivity to underlying spot price.
    - Theta: Price sensitivity to time passage (decay per day).
    - Vega: Price sensitivity to volatility (change per 1% vol change).
    - Rho: Price sensitivity to risk-free rate.
    """
    if T <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Probability density functions (pdf) and cumulative distribution functions (cdf)
    pdf_d1 = std_normal_pdf(d1)
    cdf_d1 = std_normal_cdf(d1)
    cdf_d2 = std_normal_cdf(d2)
    
    # Delta
    if option_type.lower() == "call":
        delta = cdf_d1
    else:
        delta = cdf_d1 - 1.0
        
    # Gamma (same for call and put)
    gamma = pdf_d1 / (S * sigma * np.sqrt(T))
    
    # Vega (same for call and put) - divide by 100 to show sensitivity per 1 percentage point change
    vega = S * np.sqrt(T) * pdf_d1 / 100.0
    
    # Theta (decay per day, divide by 365)
    term1 = -(S * pdf_d1 * sigma) / (2 * np.sqrt(T))
    if option_type.lower() == "call":
        term2 = r * K * np.exp(-r * T) * cdf_d2
        theta = (term1 - term2) / 365.0
    else:
        term2 = r * K * np.exp(-r * T) * std_normal_cdf(-d2)
        theta = (term1 + term2) / 365.0
        
    # Rho (sensitivity per 1 percentage point change in r, divide by 100)
    if option_type.lower() == "call":
        rho = K * T * np.exp(-r * T) * cdf_d2 / 100.0
    else:
        rho = -K * T * np.exp(-r * T) * std_normal_cdf(-d2) / 100.0

        
    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega),
        "rho": float(rho)
    }

def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> float:
    """
    Find implied volatility using Newton-Raphson method.
    """
    # Initial guess
    sigma = 0.2
    for _ in range(max_iterations):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        diff = price - market_price
        if abs(diff) < tolerance:
            return float(sigma)
        
        # Vega (multiply by 100 to convert from percentage change to fractional)
        greeks = black_scholes_greeks(S, K, T, r, sigma, option_type)
        vega = greeks["vega"] * 100.0
        
        if abs(vega) < 1e-4:
            break
            
        sigma = sigma - diff / vega
        
        # Keep vol in reasonable bounds
        if sigma <= 0.01:
            sigma = 0.01
        elif sigma >= 3.0:
            sigma = 3.0
            
    return float(sigma)
