import os
import sys
import logging
from dotenv import load_dotenv

# Ensure options_lab is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from options_lab.api.saxo_client import SaxoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("saxo_test")

def main():
    load_dotenv()
    print("=" * 70)
    print("BotAlgoTrade - Saxo OpenAPI Feature Exploration & Authorization Probe")
    print("=" * 70)

    saxo = SaxoClient()
    
    auth_url = saxo.get_authorization_url()
    print("\nSTEP 1: OAuth 2.0 Authorization Link")
    print("Open the following URL in your browser to log into Saxo SIM and authorize BotAlgoTrade:")
    print("-" * 70)
    print(auth_url)
    print("-" * 70)
    print("\nAfter logging in, your browser will redirect to:")
    print(f"  {saxo.redirect_url}/?code=YOUR_AUTHORIZATION_CODE")
    print("Copy the 'code' parameter value from the browser URL bar.")
    
    token = os.getenv("SAXO_ACCESS_TOKEN", "").strip()
    auth_code = os.getenv("SAXO_AUTH_CODE", "").strip()

    if not token and not auth_code:
        print("\nTIP: For quick testing without browser redirect, you can also paste a 24-hour Developer Token")
        print("from: https://www.developer.saxo/openapi/token")
        print("\nTo test API endpoints right now:")
        print("  $env:SAXO_ACCESS_TOKEN='<your_24h_token>'; python scripts/test_saxo_integration.py")
        print("Or:")
        print("  $env:SAXO_AUTH_CODE='<authorization_code>'; python scripts/test_saxo_integration.py")
        print("=" * 70)
        return

    if auth_code and not token:
        print("\nExchanging Authorization Code for Access Token...")
        try:
            token_data = saxo.exchange_code_for_token(auth_code)
            print("[SUCCESS] Successfully acquired Access Token!")
        except Exception as e:
            print(f"[ERROR] Token Exchange failed: {e}")
            return
    elif token:
        print("\n[INFO] Using pre-set SAXO_ACCESS_TOKEN for testing...")
        saxo.access_token = token

    print("\nSTEP 2: Testing Account Balances Endpoint (/port/v1/balances/me)...")
    try:
        balances = saxo.get_account_balances()
        print("[SUCCESS] Account Balances Response:")
        print(f"   Currency: {balances.get('Currency')}")
        print(f"   Cash Balance: {balances.get('CashBalance')}")
        print(f"   Total Value: {balances.get('TotalValue')}")
        print(f"   Margin Available: {balances.get('MarginAvailable')}")
    except Exception as e:
        print(f"[WARNING] Balances check failed: {e}")

    print("\nSTEP 3: Testing Instrument Search (/ref/v1/instruments?Keywords=AAPL)...")
    try:
        instruments = saxo.search_instruments("AAPL", asset_types=["Stock"])
        print(f"[SUCCESS] Found {len(instruments.get('Data', []))} matching instruments:")
        for item in instruments.get("Data", [])[:3]:
            print(f"   - UIC: {item.get('Identifier')}, Symbol: {item.get('Symbol')}, Description: {item.get('Description')}")
    except Exception as e:
        print(f"[WARNING] Instrument search failed: {e}")

    print("\nSTEP 4: Testing Price Charts / Momentum Endpoint (/chart/v3/charts)...")
    try:
        chart = saxo.get_chart_data(uic=211, asset_type="Stock", horizon=1440, count=10)
        print("[SUCCESS] Historical Daily Candles Sample (Last 3 days for AAPL):")
        for bar in chart.get("Data", [])[-3:]:
            print(f"   Date: {bar.get('Time')} | Open: {bar.get('Open')} | High: {bar.get('High')} | Low: {bar.get('Low')} | Close: {bar.get('Close')}")
    except Exception as e:
        print(f"[WARNING] Chart data fetch failed: {e}")

    print("\nSTEP 5: Testing Open Positions Endpoint (/port/v1/positions/me)...")
    try:
        positions = saxo.get_positions()
        pos_list = positions.get("Data", [])
        print(f"[SUCCESS] Open Positions Count: {len(pos_list)}")
        for pos in pos_list[:3]:
            print(f"   Position ID: {pos.get('PositionId')}, Symbol: {pos.get('DisplayAndControl', {}).get('Symbol')}, Amount: {pos.get('PositionBase', {}).get('Amount')}")
    except Exception as e:
        print(f"[WARNING] Positions fetch failed: {e}")

    print("\nSTEP 6: Testing Option Contract Lookup (/ref/v1/instruments?Keywords=AAPL)...")
    try:
        opt_instruments = saxo.search_instruments("AAPL", asset_types=["StockOption"])
        opt_data = opt_instruments.get("Data", [])
        print(f"[SUCCESS] Found {len(opt_data)} Option Instruments for AAPL:")
        for opt in opt_data[:3]:
            print(f"   - UIC: {opt.get('Identifier')}, Symbol: {opt.get('Symbol')}, Description: {opt.get('Description')}")
    except Exception as e:
        print(f"[WARNING] Option search failed: {e}")

    print("\n" + "=" * 70)
    print("[DONE] Exploration Probe Execution Complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
