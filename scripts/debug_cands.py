import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine

engine = WeeklyIntelligenceEngine()
for sym in ["INTC", "COIN", "SO"]:
    cand = engine._build_dynamic_trade_candidate(symbol=sym, strategy="CSP")
    if cand:
        print(f"{sym}: spot={cand['spot_price']}, strike={cand['strike']}, prem={cand['premium_estimate']}, limit={cand.get('limit_price')}, dte={cand['dte']}, exp={cand['expiration_date']}, uic={cand['uic']}")
    else:
        print(f"{sym}: returned None")
