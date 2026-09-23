import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine
from options_lab.api import db as database

engine = WeeklyIntelligenceEngine()
news = engine.collect_weekly_news_events()
res = engine._generate_dual_mode_harvest_blotters(news_items=news, week_label="Test")

m1 = res.get("mode_1", {})
cands = m1.get("candidates", [])
print(f"Mode 1 candidates count: {len(cands)}")
for c in cands:
    print(f"  {c.get('symbol')}: strike={c.get('strike')}, prem={c.get('premium_estimate')}, limit={c.get('limit_price')}, contracts={c.get('contracts')}")
