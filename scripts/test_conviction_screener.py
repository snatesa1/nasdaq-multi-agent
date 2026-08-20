import sys
import os
import json
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from options_lab.api.conviction_screener import ConvictionScreener

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    print("=" * 80)
    print("[PHASE 1 VALIDATION] 5-Pillar Practitioner Conviction Screener")
    print("=" * 80)

    screener = ConvictionScreener()
    test_tickers = ["AAPL", "NVDA", "JPM", "TSLA"]

    results = []

    for sym in test_tickers:
        print(f"\nScanning ticker: {sym}...")
        res = screener.screen(sym)
        results.append(res)
        
        print(f"  Ticker:           {res['symbol']}")
        print(f"  Conviction Score: {res['conviction_score']:.3f} / 1.000")
        print(f"  Decision Tier:    {res['decision']}")
        print(f"  Strongest Pillar: {res['strongest_pillar']} ({res['pillars'].get(res['strongest_pillar'], {}).get('score', 0):.2f})")
        print(f"  Weakest Pillar:   {res['weakest_pillar']} ({res['pillars'].get(res['weakest_pillar'], {}).get('score', 0):.2f})")
        print("  Pillar Breakdown:")
        for p_name, p_data in res.get("pillars", {}).items():
            print(f"    - {p_name:<25}: Score {p_data['score']:.2f}")

    print("\n" + "=" * 80)
    print("[PHASE 1 SUCCESS] All test tickers evaluated cleanly.")
    print("=" * 80)

if __name__ == "__main__":
    main()
