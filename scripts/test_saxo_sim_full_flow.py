import sys
import os
import json
import asyncio
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from options_lab.api.saxo_client import SaxoClient
from options_lab.api.saxo_pipeline import SaxoPipeline
from options_lab.api.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    print("=" * 80)
    print("[PHASE 4 VALIDATION] Saxo Full Pipeline Orchestrator & End-to-End SIM Execution")
    print("=" * 80)

    # Initialize Saxo Client with configured token if present
    token = settings.SAXO_ACCESS_TOKEN if hasattr(settings, "SAXO_ACCESS_TOKEN") else None
    saxo_client = SaxoClient(access_token=token)
    pipeline = SaxoPipeline(saxo_client=saxo_client)

    test_universe = ["AAPL", "NVDA", "JPM", "TSLA"]

    print("\nExecuting 7-step full pipeline scan across candidate universe...")
    scan_report = await pipeline.execute_full_pipeline_scan(
        candidate_tickers=test_universe,
        simulate_order_placement=True
    )

    print("\n" + "=" * 80)
    print("[FULL PIPELINE EXECUTION REPORT]")
    print("=" * 80)
    print(f"Timestamp:              {scan_report['scan_timestamp']}")
    print(f"Account Net Equity:     ${scan_report['account_balances'].get('total_equity', 0):,.2f}")
    print(f"Cash Available:         ${scan_report['account_balances'].get('cash_available', 0):,.2f}")
    print(f"Candidates Screened:    {scan_report['candidates_screened']}")
    print(f"Qualified Conviction:   {scan_report['qualified_conviction']}")
    print(f"Signal Qualified:       {scan_report['signal_qualified']}")
    print(f"Orders Staged / Placed: {len(scan_report['orders_placed'])}")
    print(f"Orders Risk-Blocked:    {len(scan_report['orders_blocked'])}")

    print("\n" + "-" * 80)
    print("EXECUTED / STAGED ORDERS DETAILS:")
    print("-" * 80)
    for idx, ord_data in enumerate(scan_report["orders_placed"], 1):
        print(f"\n[{idx}] {ord_data['symbol']} -- {ord_data['action']} ({ord_data['wheel_state']})")
        print(f"    Spot Price:         ${ord_data['spot_price']:.2f}")
        print(f"    Strike Price:       ${ord_data['strike']:.2f} (Delta {ord_data['delta']})")
        print(f"    Option Premium:     ${ord_data['theoretical_price']:.2f}")
        print(f"    Yield % (Ann):      {ord_data['yield_pct']:.2f}% ({ord_data['annualized_yield']:.1f}% APY)")
        print(f"    Collateral Req:     ${ord_data['collateral_required']:,.2f}")
        print(f"    Saxo Order ID:      {ord_data['saxo_order_response'].get('order_id', 'N/A')}")
        print(f"    Saxo Order Payload: {json.dumps(ord_data['saxo_order_payload'])}")

    if scan_report["orders_blocked"]:
        print("\n" + "-" * 80)
        print("RISK-BLOCKED ORDERS DETAILS:")
        print("-" * 80)
        for blk in scan_report["orders_blocked"]:
            print(f"  - Ticker {blk['symbol']}: Violations = {blk['violations']}")

    print("\n" + "=" * 80)
    print("[PHASE 4 SUCCESS] Full pipeline orchestrator executed cleanly.")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
