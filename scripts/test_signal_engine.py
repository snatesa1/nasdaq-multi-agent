import sys
import os
import asyncio
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from options_lab.api.signal_engine import SignalEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    print("=" * 80)
    print("[PHASE 2 VALIDATION] Multi-Layer Signal Engine")
    print("=" * 80)

    engine = SignalEngine()
    test_tickers = ["AAPL", "NVDA", "JPM", "TSLA"]

    for sym in test_tickers:
        print(f"\nComputing signal for ticker: {sym}...")
        res = await engine.compute_composite_score(sym)
        
        print(f"  Ticker:          {res['symbol']}")
        print(f"  Composite Score: {res['composite_score']:.3f} / 1.000")
        print(f"  Trade Decision:  {res['decision']}")
        print(f"  Strategy Hint:   {res['strategy_hint']}")
        print("  Signal Layers:")
        mom = res["layers"]["momentum"]
        mac = res["layers"]["macro"]
        news = res["layers"]["news"]
        print(f"    - Momentum (50%): Score {mom['score']:.2f} (RSI: {mom['rsi']:.1f}, Above EMA200: {mom['above_ema200']})")
        print(f"    - Macro    (30%): Score {mac['score']:.2f} (VIX: {mac['vix_level']:.1f}, Yield Spread: {mac['yield_spread']:.2f})")
        print(f"    - News     (20%): Score {news['score']:.2f} (Sentiment: {news['sentiment']}, Headlines: {news['headline_count']})")

    print("\n" + "=" * 80)
    print("[PHASE 2 SUCCESS] All signal layers computed cleanly.")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
