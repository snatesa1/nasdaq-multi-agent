import yfinance as yf
from datetime import datetime

tickers = ["INTC", "COIN", "SO"]
for sym in tickers:
    tk = yf.Ticker(sym)
    opts = tk.options
    print(f"{sym} available option expirations (count: {len(opts)}):")
    oct_expiries = [e for e in opts if "2026-10" in e or "2026-09" in e or "2026-11" in e]
    print(f"  Target window expiries: {oct_expiries}")
    if oct_expiries:
        target_exp = oct_expiries[0]
        chain = tk.option_chain(target_exp)
        print(f"  Puts for {target_exp}: count = {len(chain.puts)}")
        if not chain.puts.empty:
            sample = chain.puts[["strike", "bid", "ask", "lastPrice", "impliedVolatility"]].head(5)
            print(sample)
