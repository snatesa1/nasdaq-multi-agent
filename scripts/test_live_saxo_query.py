import os
import sys
import json
from dotenv import load_dotenv

# Ensure root package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env
load_dotenv()

from options_lab.api.config import settings
from options_lab.api.saxo_client import SaxoClient


def main():
    print("=" * 60)
    print(">> SAXO LIVE ACCOUNT READ-ONLY VERIFICATION")
    print("=" * 60)
    print(f"Environment: {settings.SAXO_ENV}")
    print(f"Base URL: {settings.SAXO_OPENAPI_BASE_URL}")
    print(f"App Name: {settings.SAXO_APP_NAME}")
    print(f"Live Execution Shield Active: {not settings.BROKER_ALLOW_LIVE_EXECUTION}")
    
    client = SaxoClient()
    print(f"Access Token Loaded: {bool(client.access_token)} (Length: {len(client.access_token) if client.access_token else 0})")
    
    # 1. Test Account Balances
    print("\n[1/3] Fetching Live Account Balances...")
    balances = client.get_account_balances()
    print("Account Summary Result:")
    print(json.dumps(balances, indent=2))
    
    # 2. Test Open Positions
    print("\n[2/3] Fetching Live Open Positions...")
    positions = client.get_positions()
    print(f"Total Positions Count: {positions.get('total_positions_count', 0)}")
    print(f"Status: {positions.get('status')}")
    if positions.get("positions"):
        for p in positions["positions"]:
            print(f"  -> {p.get('symbol')} ({p.get('description')}): Qty={p.get('amount')}, Mark=${p.get('current_price')}, PnL=${p.get('unrealized_pnl')}")
            
    # 3. Test Order Blotter History
    print("\n[3/3] Fetching Live Order Blotter History...")
    orders = client.get_orders()
    print(f"Total Orders Count: {orders.get('total_orders_count', 0)}")
    print(f"Status: {orders.get('status')}")
    if orders.get("orders"):
        for o in orders["orders"][:10]:
            print(f"  -> Order #{o.get('order_id')} | {o.get('buy_sell')} {o.get('symbol')} | Status: {o.get('status')} | Price: ${o.get('order_price')} | Placed: {o.get('placed_at')}")

    print("\n[SUCCESS] Live account read-only verification completed!")

if __name__ == '__main__':
    main()
