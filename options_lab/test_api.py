import sys
import os
# Add root and parent path to PYTHONPATH so we can import properly
_this_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_this_dir)
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_routes():
    print("[TEST] Running OptionsLab API Route Tests...")
    
    # 1. Health check
    print("1. Testing /health...")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    
    # 2. Market Quote
    print("2. Testing /market/quote/AAPL...")
    resp = client.get("/market/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert "current_price" in data
    assert "historical_volatility" in data
    
    # 3. GBM Simulation
    print("3. Testing /simulate/gbm...")
    resp = client.post("/simulate/gbm", json={
        "S0": 100.0,
        "mu": 0.05,
        "sigma": 0.2,
        "T": 1.0,
        "N": 10,
        "num_paths": 5
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["paths"]) == 5
    assert len(data["time_grid"]) == 11
    
    # 4. Analytical Price
    print("4. Testing /price/analytical...")
    resp = client.post("/price/analytical", json={
        "S": 100.0,
        "K": 100.0,
        "T": 1.0,
        "r": 0.05,
        "sigma": 0.2,
        "option_type": "call"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "price" in data
    assert "greeks" in data
    assert abs(data["price"] - 10.4505) < 0.01 # Standard BS call price for 100,100,1y,5%,20%
    
    # 5. Monte Carlo standard
    print("5. Testing /price/monte-carlo...")
    resp = client.post("/price/monte-carlo", json={
        "S0": 100.0,
        "K": 100.0,
        "T": 1.0,
        "r": 0.05,
        "sigma": 0.2,
        "option_type": "call",
        "num_paths": 100
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "price" in data
    
    # 6. Legacy Lab
    print("6. Testing /price/legacy-lab...")
    resp = client.post("/price/legacy-lab", json={
        "S0": 80.0,
        "sigma": 0.03,
        "r": 0.001,
        "T": 100/365.0,
        "N": 100,
        "K": 100.0
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "price" in data
    
    # 7. Greeks Surface
    print("7. Testing /greeks/surface...")
    resp = client.post("/greeks/surface", json={
        "S": 100.0,
        "K": 100.0,
        "T": 1.0,
        "r": 0.05,
        "sigma": 0.2,
        "option_type": "call"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "surface" in data
    
    # 8. Strategy Payoff
    print("8. Testing /strategy/payoff...")
    resp = client.post("/strategy/payoff", json={
        "underlying_spot": 100.0,
        "r": 0.05,
        "sigma": 0.2,
        "legs": [
            {"asset_type": "stock", "position": "long", "entry_price": 100.0, "quantity": 1},
            {"asset_type": "option", "option_type": "call", "position": "short", "strike": 105.0, "expiry": 0.5, "entry_price": 3.50, "quantity": 1}
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "payoff_grid" in data
    assert "max_profit" in data
    
    # 9. Volatility Surface & Smile
    print("9. Testing /volatility/surface...")
    resp = client.post("/volatility/surface", json={
        "spot_price": 100.0,
        "base_sigma": 0.25,
        "risk_free_rate": 0.05,
        "strike_ratios": [0.8, 0.9, 1.0, 1.1, 1.2],
        "expirations_days": [30, 60, 90]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "iv_matrix" in data
    assert "vol_smile_30d" in data

    # 10. Portfolio Net Greeks Aggregator
    print("10. Testing /portfolio/greeks...")
    resp = client.post("/portfolio/greeks", json={
        "positions": [
            {"type": "stock", "symbol": "AAPL", "quantity": 100, "spot_price": 180.0},
            {"type": "call", "symbol": "AAPL", "quantity": -1, "spot_price": 180.0, "strike": 185.0, "days_to_expiration": 30, "volatility": 0.25}
        ],
        "risk_free_rate": 0.05
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "net_greeks" in data
    assert "delta_hedge_recommendation" in data

    # 11. Socratic Tutor Hint
    print("11. Testing /tutor/hint...")
    resp = client.post("/tutor/hint", json={
        "chat_history": [
            {"role": "user", "content": "How does Theta affect my covered call?"}
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "hint" in data

    # 12. Market Universe
    print("12. Testing /market/universe...")
    resp = client.get("/market/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert "Technology" in data
    assert len(data["Technology"]) == 10
    assert "symbol" in data["Technology"][0]
    assert "name" in data["Technology"][0]

    # 13. Margin Status (clamped & compliant)
    print("13. Testing /api/margin/status...")
    resp = client.get("/api/margin/status")
    assert resp.status_code == 200
    margin_data = resp.json()
    assert "margin_utilization_pct" in margin_data
    assert margin_data["margin_utilization_pct"] >= 0.0
    assert "max_margin_limit_pct" in margin_data

    # 14. Weekly Intelligence Briefing with force_refresh
    print("14. Testing /api/intelligence/weekly-briefing?force_refresh=true...")
    resp = client.get("/api/intelligence/weekly-briefing?force_refresh=true")
    assert resp.status_code == 200
    briefing_data = resp.json()
    assert "week_label" in briefing_data
    assert "generated_at" in briefing_data
    assert "margin_status" in briefing_data
    assert briefing_data["margin_status"]["margin_utilization_pct"] >= 0.0
    assert "potential_trades" in briefing_data
    
    print("[SUCCESS] All OptionsLab API Route Tests Passed successfully!")

if __name__ == "__main__":
    run_tests = test_routes
    run_tests()

