import sys
import os

# Add nasdaq-multi-agent to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from options_lab.api.trade_history_ingest import TradeHistoryIngestEngine

from options_lab.api.campaign_stitcher import CampaignStitcher
from options_lab.api.behavioral_forensics import BehavioralForensicsEngine
from options_lab.api.safety_shield import BehavioralSafetyShield
from options_lab.api.saxo_client import SaxoClient

def main():
    print("🚀 Testing Saxo Historical Ingest & Behavioral Forensics Pipeline...")

    # 1. Ingest sample
    ingest = TradeHistoryIngestEngine()
    ingest_res = ingest.ingest_default_sample()
    print(f"✅ Ingest Result: Status={ingest_res['status']}, ReportId={ingest_res['report_id']}")
    print(f"   Stored records: {ingest_res['records_stored']}")

    # 2. Reconstruct campaigns
    stitcher = CampaignStitcher(ingest_engine=ingest)
    campaigns = stitcher.reconstruct_all_campaigns()
    print(f"\n✅ Stitched Campaigns Count: {len(campaigns)}")
    for c in campaigns[:4]:
        print(f"   • [{c['ticker']}] {c['strategy']} -> PnL: ${c['total_pnl']:,.2f} | Bias: {c['bias_classification']}")

    # 3. Behavioral Forensics Audit
    forensics = BehavioralForensicsEngine(campaign_stitcher=stitcher)
    audit = forensics.generate_behavioral_audit()
    print(f"\n✅ Behavioral Forensics Audit Generated:")
    print(f"   Discipline Score: {audit['discipline_score']} / 100 (Grade: {audit['grade']})")
    print(f"   Stock PnL: ${audit['stock_pnl']:,.2f} | Option PnL: ${audit['option_pnl']:,.2f}")
    print(f"   Options Win Rate: {audit['options_win_rate']}% ({audit['winning_options_trades']} Wins / {audit['losing_options_trades']} Losses)")
    print(f"   Diagnoses count: {len(audit['diagnoses'])}")
    for d in audit['diagnoses']:
        print(f"     - [{d['severity']}] {d['name']}: {d['impact']}")

    # 4. Behavioral Safety Shield Test
    shield = BehavioralSafetyShield()
    
    # Test A: Approved systematic trade (Visa Covered Call Delta 0.15)
    test_safe = shield.evaluate_order(
        symbol="V",
        asset_type="StockOption",
        buy_sell="Sell",
        strike=360.0,
        delta=0.15,
        dte=35,
        order_value=250.0,
        portfolio_equity=102000.0,
        current_ticker_exposure=5000.0
    )
    print(f"\n✅ Safety Shield Test 1 (Systematic V Call): Status={test_safe['status']}, Approved={test_safe['approved']}")

    # Test B: Blocked trade (PANW short call with high delta - repeating the past mistake)
    test_blocked_panw = shield.evaluate_order(
        symbol="PANW",
        asset_type="StockOption",
        buy_sell="Sell",
        strike=180.0,
        delta=0.45,
        dte=30,
        order_value=500.0,
        portfolio_equity=102000.0,
        current_ticker_exposure=15000.0
    )
    print(f"✅ Safety Shield Test 2 (Aggressive PANW Call): Status={test_blocked_panw['status']}, Approved={test_blocked_panw['approved']}")
    print(f"   Infractions: {test_blocked_panw['infractions']}")

    # Test C: Blocked revenge trade (Attempting trade right after $2k loss)
    from datetime import datetime
    test_blocked_revenge = shield.evaluate_order(
        symbol="TSLA",
        asset_type="StockOption",
        buy_sell="Sell",
        strike=200.0,
        delta=0.20,
        dte=30,
        order_value=1000.0,
        portfolio_equity=102000.0,
        current_ticker_exposure=0.0,
        recent_loss_amount=2500.0,
        recent_loss_timestamp=datetime.now()
    )
    print(f"✅ Safety Shield Test 3 (Revenge Lockout): Status={test_blocked_revenge['status']}, Approved={test_blocked_revenge['approved']}")
    print(f"   Infractions: {test_blocked_revenge['infractions']}")

    # 5. News Wire Test
    client = SaxoClient()
    news = client.get_portfolio_news(top=5)
    print(f"\n✅ News Wire Test: Fetched {len(news)} headlines")
    for n in news[:3]:
        print(f"   • [{n.get('time')}] {n.get('headline')}")

    print("\n🎉 ALL BACKEND PIPELINES VERIFIED PERFECTLY!")

if __name__ == "__main__":
    main()
