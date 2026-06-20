import sys
import os
# Add root path to PYTHONPATH so we can import properly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    
    # 9. Market Universe
    print("9. Testing /market/universe...")
    resp = client.get("/market/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert "Technology" in data
    assert len(data["Technology"]) == 10
    assert "symbol" in data["Technology"][0]
    assert "name" in data["Technology"][0]
    
    print("[SUCCESS] All OptionsLab API Route Tests Passed successfully!")

if __name__ == "__main__":
    run_tests = test_routes
    run_tests()
