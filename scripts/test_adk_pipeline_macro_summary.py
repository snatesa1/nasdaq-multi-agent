import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_adk_macro")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from options_lab.api.options_adk_workflow import OptionsADKWorkflowEngine

def test_pipeline_macro_summary():
    engine = OptionsADKWorkflowEngine()
    
    print("Testing OptionsADKWorkflowEngine.run_pipeline(force_refresh=True)...")
    res = engine.run_pipeline(force_refresh=True)
    
    # 1. Verify market_summary
    market_summary = res.get("market_summary", [])
    print(f"-> Market summary items count: {len(market_summary)}")
    assert len(market_summary) >= 4, f"Expected at least 4 market summary items, got {len(market_summary)}"
    for item in market_summary:
        print(f"   [{item['category']}] {item['title'][:65]}... ({item.get('sites_count', 1)} sites)")
        assert "title" in item and "context" in item and "sources" in item
    
    # 2. Verify cross_asset_table
    cross_asset = res.get("cross_asset_table", [])
    print(f"\n-> Cross-asset rows count: {len(cross_asset)}")
    assert len(cross_asset) == 8, f"Expected 8 cross-asset rows, got {len(cross_asset)}"
    for row in cross_asset:
        print(f"   {row['asset']}: {row['level']} ({row['change']}) [{row['direction']}] Bias: {row['bias']}")
        assert "asset" in row and "direction" in row and "bias" in row and "driver" in row and "options_stance" in row
    
    # 3. Verify zero memo headers in ai_summary
    ai_summary = res.get("ai_summary", "")
    print(f"\n-> AI summary length: {len(ai_summary)}")
    for line in ai_summary.split("\n"):
        stripped = line.strip().upper()
        assert not stripped.startswith("TO:"), f"Found memo header 'TO:' in: {line}"
        assert not stripped.startswith("FROM:"), f"Found memo header 'FROM:' in: {line}"
        assert not stripped.startswith("SUBJECT:"), f"Found memo header 'SUBJECT:' in: {line}"
        assert not stripped.startswith("DATE:"), f"Found memo header 'DATE:' in: {line}"
    
    print("\nSUCCESS: All pipeline assertions verified cleanly!")

if __name__ == "__main__":
    test_pipeline_macro_summary()
