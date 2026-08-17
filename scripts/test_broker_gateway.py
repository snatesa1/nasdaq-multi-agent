import os
import sys
import asyncio

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from fastapi.testclient import TestClient
from options_lab.api.main import app
from options_lab.api.saxo_client import SaxoClient
from options_lab.api.models import (
    BrokerAccountSummary,
    BrokerPositionsResponse,
    BrokerOrdersResponse
)

def run_tests():
    print("==================================================")
    print(">> RUNNING BROKER GATEWAY & HARNESS TEST SUITE")
    print("==================================================")

    # 1. SaxoClient direct unit tests
    client = SaxoClient()
    
    balances = client.get_account_balances()
    acc = BrokerAccountSummary(**balances)
    print(f"[PASS] SaxoClient.get_account_balances() -> Equity: ${acc.total_equity:,.2f}, Cash: ${acc.cash_available:,.2f} [{acc.status}]")
    
    positions = client.get_positions()
    pos = BrokerPositionsResponse(**positions)
    print(f"[PASS] SaxoClient.get_positions() -> {pos.total_positions_count} open positions validated.")

    orders = client.get_orders()
    ords = BrokerOrdersResponse(**orders)
    print(f"[PASS] SaxoClient.get_orders() -> {ords.total_orders_count} orders validated.")

    # 2. Live safety shield test
    client.environment = "LIVE"
    blocked = client.place_order(uic=211, order_price=220.0)
    assert blocked["status"] == "LIVE_EXECUTION_BLOCKED_BY_SAFETY_SHIELD", "Live safety shield failed to block order!"
    print(f"[PASS] Live Execution Safety Shield successfully blocked unauthorized trade.")

    # 3. FastAPI endpoint tests
    test_client = TestClient(app)
    
    r_status = test_client.get("/api/broker/status")
    assert r_status.status_code == 200
    print(f"[PASS] GET /api/broker/status -> {r_status.json()}")

    r_acc = test_client.get("/api/broker/account")
    assert r_acc.status_code == 200
    print(f"[PASS] GET /api/broker/account -> Total Equity: ${r_acc.json()['total_equity']:,.2f}")

    r_pos = test_client.get("/api/broker/positions")
    assert r_pos.status_code == 200
    print(f"[PASS] GET /api/broker/positions -> {r_pos.json()['total_positions_count']} positions returned.")

    r_ords = test_client.get("/api/broker/orders")
    assert r_ords.status_code == 200
    print(f"[PASS] GET /api/broker/orders -> {r_ords.json()['total_orders_count']} orders returned.")

    print("\n[SUCCESS] ALL BROKER GATEWAY TESTS COMPLETED WITH 100% PASS RATE!")

if __name__ == "__main__":
    run_tests()
