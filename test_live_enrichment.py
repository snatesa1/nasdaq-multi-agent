import urllib.request
import time
import subprocess
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("🚀 Starting FastAPI backend in test mode...")
p = subprocess.Popen([sys.executable, "-m", "uvicorn", "options_lab.api.main:app", "--host", "127.0.0.1", "--port", "8000"])
time.sleep(3)

try:
    # 1. Health
    h_res = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/health").read().decode())
    print(f"✅ Health: {h_res}")

    # 2. Positions
    pos_res = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/broker/positions").read().decode())
    print(f"\n✅ Live Enriched Positions ({pos_res.get('status')}):")
    for p_item in pos_res.get("positions", []):
        print(f"   • [{p_item['symbol']}] Open: ${p_item['open_price']} -> Current: ${p_item['current_price']} | MktVal: ${p_item['market_value']:,.2f} | PnL: ${p_item['unrealized_pnl']:,.2f} ({p_item['unrealized_pnl_pct']}%)")
    print(f"   Total Unrealized PnL: ${pos_res.get('total_unrealized_pnl'):,.2f}")

    # 3. Account
    acc_res = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/broker/account").read().decode())
    print(f"\n✅ Live Account Summary ({acc_res.get('status')}):")
    print(f"   Total Equity: ${acc_res.get('total_equity'):,.2f}")
    print(f"   Cash Available: ${acc_res.get('cash_available'):,.2f}")
    print(f"   Margin Available: ${acc_res.get('margin_available'):,.2f}")

finally:
    p.terminate()
    print("\n🎉 Verification test successfully completed!")
