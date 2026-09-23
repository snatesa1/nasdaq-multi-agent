import yfinance as yf

for sym in ["INTC", "COIN", "SO"]:
    tk = yf.Ticker(sym)
    chain = tk.option_chain("2026-10-23")
    puts = chain.puts
    print(f"=== {sym} Puts for 2026-10-23 (Count: {len(puts)}) ===")
    # Print strikes with valid bid or lastPrice
    active = puts[(puts["bid"] > 0) | (puts["lastPrice"] > 0.10)][["strike", "bid", "ask", "lastPrice", "volume", "openInterest", "impliedVolatility"]]
    print(active.tail(15))
