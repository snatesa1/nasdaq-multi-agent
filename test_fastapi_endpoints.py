import os
import sys

sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from options_lab.api.main import app

def test_endpoints():
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] /health ->", res.json())
    
    # 2. Broker status
    res = client.get("/api/broker/status")
    assert res.status_code == 200, f"Broker status failed: {res.status_code}"
    print("[PASS] /api/broker/status ->", res.json())
    
    # 3. Broker account summary
    res = client.get("/api/broker/account")
    assert res.status_code == 200, f"Broker account failed: {res.status_code}"
    account_data = res.json()
    assert "cash_available" in account_data and "total_equity" in account_data
    print("[PASS] /api/broker/account -> Total Equity:", account_data["total_equity"], "Cash:", account_data["cash_available"])
    
    # 4. Broker positions
    res = client.get("/api/broker/positions")
    assert res.status_code == 200, f"Broker positions failed: {res.status_code}"
    positions_data = res.json()
    assert "positions" in positions_data
    print("[PASS] /api/broker/positions -> Count:", positions_data["total_positions_count"], "Positions:", [p["symbol"] for p in positions_data["positions"]])
    
    # 5. Broker orders
    res = client.get("/api/broker/orders")
    assert res.status_code == 200, f"Broker orders failed: {res.status_code}"
    orders_data = res.json()
    assert "orders" in orders_data
    print("[PASS] /api/broker/orders -> Count:", orders_data["total_orders_count"], "Orders:", [o["order_id"] for o in orders_data["orders"]])

    print("[SUCCESS] All FastAPI Broker Gateway Endpoints Passed with Strict Type Validation!")

if __name__ == "__main__":
    test_endpoints()
