import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_integration")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine

def test_engine_outputs():
    engine = WeeklyIntelligenceEngine()
    
    # 1. Test curated Google News fetch
    print("Testing fetch_curated_google_news()...")
    news = engine.fetch_curated_google_news(max_items=6)
    print(f"-> Fetched {len(news)} clustered news items")
    assert len(news) > 0
    sample = news[0]
    print(f"   Sample: '{sample['headline']}' | Outlets: {', '.join(sample['sources'])} ({sample['sites_count']} sites)")
    
    # 2. Test market summary accordions
    print("\nTesting build_market_summary_accordions()...")
    accordions = engine.build_market_summary_accordions(news)
    print(f"-> Generated {len(accordions)} accordion cards:")
    for acc in accordions:
        print(f"   * [{acc['category']}] {acc['title'][:65]}... ({acc['sites_count']} sites)")
    assert len(accordions) >= 4
    
    # 3. Test cross-asset directional table
    print("\nTesting build_cross_asset_directional_table()...")
    table = engine.build_cross_asset_directional_table()
    print(f"-> Generated {len(table)} cross-asset benchmarks:")
    for row in table:
        print(f"   * {row['asset']}: {row['level']} ({row['change']}) -> [{row['direction']}] Bias: {row['bias']}")
    assert len(table) == 8
    
    print("\n[SUCCESS] All WeeklyIntelligenceEngine methods tested successfully!")

if __name__ == "__main__":
    test_engine_outputs()
