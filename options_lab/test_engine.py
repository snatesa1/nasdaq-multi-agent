import numpy as np
from engine.gbm_engine import simulate_gbm
from engine.black_scholes import black_scholes_price, black_scholes_greeks
from engine.monte_carlo import pricing_monte_carlo_standard, pricing_monte_carlo_lab_legacy
from engine.greeks import generate_greeks_surface
from engine.strategy_simulator import simulate_strategy_payoff

def run_tests():
    print("[TEST] Running OptionsLab Engine Tests...")
    
    # 1. GBM
    print("\n1. Testing GBM Simulation...")
    gbm = simulate_gbm(S0=80.0, mu=0.001, sigma=0.03, T=100/365.0, N=1000, num_paths=100)
    print(f"Generated {len(gbm['paths'])} paths with {len(gbm['time_grid'])} steps.")
    assert len(gbm['paths']) == 100
    assert len(gbm['time_grid']) == 1001
    
    # 2. Black-Scholes pricing
    print("\n2. Testing Black-Scholes Analytical Pricing...")
    call = black_scholes_price(S=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03, option_type="call")
    put = black_scholes_price(S=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03, option_type="put")
    print(f"BS Call: {call:.6f}, Put: {put:.6f}")
    
    # 3. Monte Carlo Standard
    print("\n3. Testing Monte Carlo Standard Pricing...")
    mc_call = pricing_monte_carlo_standard(S0=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03, option_type="call", num_paths=5000)
    mc_put = pricing_monte_carlo_standard(S0=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03, option_type="put", num_paths=5000)
    print(f"MC Standard Call: {mc_call['price']:.6f} +/- {mc_call['standard_error']:.6f}")
    print(f"MC Standard Put:  {mc_put['price']:.6f}  +/- {mc_put['standard_error']:.6f}")
    
    # 4. Monte Carlo Lab Legacy
    print("\n4. Testing Monte Carlo Lab Legacy pricing (matching user's lab formulation)...")
    legacy = pricing_monte_carlo_lab_legacy(S0=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03, N=1000)
    print(f"Legacy Lab Put Price: {legacy['price']:.6f}")
    
    # 5. Greeks Surface
    print("\n5. Testing Greeks Surface Generator...")
    surf = generate_greeks_surface(S0=80.0, K=100.0, T=100/365.0, r=0.001, sigma=0.03)
    print(f"Surface generated with {len(surf['surface'])} nodes.")
    
    # 6. Strategy Payoff
    print("\n6. Testing Strategy Payoff Simulator (Covered Call)...")
    legs = [
        {"asset_type": "stock", "position": "long", "entry_price": 80.0, "quantity": 1},
        {"asset_type": "option", "option_type": "call", "position": "short", "strike": 85.0, "expiry": 100/365.0, "entry_price": 1.5, "quantity": 1}
    ]
    payoff = simulate_strategy_payoff(legs, 80.0, 0.001, 0.03)
    print(f"Max Profit: {payoff['max_profit']}, Max Loss: {payoff['max_loss']}, Breakevens: {payoff['breakevens']}")
    
    print("\n[SUCCESS] All Engine Tests Passed successfully!")


if __name__ == "__main__":
    run_tests()
