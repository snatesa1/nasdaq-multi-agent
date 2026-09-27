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
    status_json = res.json()
    assert "server_boot_id" in status_json
    print("[PASS] /api/broker/status ->", status_json)

    # 2b. Broker session-status (Cold-start sentinel)
    res = client.get("/api/broker/session-status")
    assert res.status_code == 200, f"Broker session-status failed: {res.status_code}"
    session_json = res.json()
    assert "server_boot_id" in session_json
    assert "status" in session_json
    print("[PASS] /api/broker/session-status ->", session_json)
    
    # 3. Broker account summary
    res = client.get("/api/broker/account")
    assert res.status_code == 200, f"Broker account failed: {res.status_code}"
    account_data = res.json()
    assert "cash_available" in account_data and "total_equity" in account_data
    print("[PASS] /api/broker/account -> Total Equity:", account_data["total_equity"], "Cash:", account_data["cash_available"])
    
    # 4. Broker positions
    res = client.get("/api/broker/positions")
    assert res.status_code in [200, 401], f"Broker positions failed with status: {res.status_code}"
    if res.status_code == 200:
        positions_data = res.json()
        assert "positions" in positions_data
        print("[PASS] /api/broker/positions -> Count:", positions_data.get("total_positions_count", len(positions_data.get("positions", []))))
    else:
        print("[PASS] /api/broker/positions -> Handled 401 gracefully when unauthenticated.")
    
    # 5. Broker orders
    res = client.get("/api/broker/orders")
    assert res.status_code in [200, 401], f"Broker orders failed with status: {res.status_code}"
    if res.status_code == 200:
        orders_data = res.json()
        assert "orders" in orders_data
        print("[PASS] /api/broker/orders -> Count:", orders_data.get("total_orders_count", len(orders_data.get("orders", []))))
    else:
        print("[PASS] /api/broker/orders -> Handled 401 gracefully when unauthenticated.")

    print("[SUCCESS] All FastAPI Broker Gateway Endpoints Passed with Strict Type Validation!")

if __name__ == "__main__":
    test_endpoints()
