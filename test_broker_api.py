import sys
import os
import asyncio

# Ensure paths
sys.path.insert(0, os.path.abspath("."))

from options_lab.api.saxo_client import SaxoClient
from options_lab.api.models import BrokerAccountSummary, BrokerPositionsResponse, BrokerOrdersResponse

async def main():
    print("Testing SaxoClient in sandbox/sim mode...")
    client = SaxoClient()
    
    # 1. Test account balances
    balances = client.get_account_balances()
    print("Balances raw:", balances)
    account_model = BrokerAccountSummary(**balances)
    print("Account Model Validated:", account_model.dict())
    
    # 2. Test positions
    positions = client.get_positions()
    print("Positions count:", len(positions.get("positions", [])))
    positions_model = BrokerPositionsResponse(**positions)
    print("Positions Model Validated:", positions_model.dict()["total_positions_count"], "positions.")
    for p in positions_model.positions:
        print(f"  -> {p.symbol} ({p.asset_type}): amount={p.amount}, open=${p.open_price}, mark=${p.current_price}, PnL=${p.unrealized_pnl} ({p.unrealized_pnl_pct}%)")
    
    # 3. Test orders
    orders = client.get_orders()
    orders_model = BrokerOrdersResponse(**orders)
    print("Orders Model Validated:", orders_model.dict()["total_orders_count"], "orders.")
    for o in orders_model.orders:
        print(f"  -> Order {o.order_id}: {o.buy_sell} {o.symbol} {o.amount} @ ${o.order_price} [{o.status}]")

    # 4. Test Live execution safety guard
    client.environment = "LIVE"
    live_blocked_order = client.place_order(uic=211, order_price=220.0)
    print("Live Order Safety Result:", live_blocked_order)
    assert live_blocked_order["status"] == "LIVE_EXECUTION_BLOCKED_BY_SAFETY_SHIELD", "Safety shield failed!"
    print("[SUCCESS] Live execution safety shield successfully verified!")

if __name__ == "__main__":
    asyncio.run(main())
