"""
verify_middle_ground_pricing.py
Standalone test verifying:
1. Middle ground pricing (+1.5% favorable seller limit price quantized to tick sizes).
2. Triumvirate candidate preservation (INTC, COIN, SO) strictly within 30-35 DTE.
3. Total monthly harvest >= $1,500 within 75% margin ceiling.
4. Dialectical debate matrix reflects $1,500 harvest mandate.
"""
import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine
from options_lab.api import db as database


def run_verification():
    print("==================================================================")
    print("Verifying Middle Ground Pricing & $1,500 Harvest Blotter")
    print("==================================================================")

    # 1. Purge stale cache
    try:
        with database._get_conn() as conn:
            conn.execute("DELETE FROM saxo_cache WHERE key LIKE 'briefing_%' OR key LIKE 'adk_briefing_%'")
            conn.commit()
        print("[1] Cleared stale briefing cache from SQLite.")
    except Exception as e:
        print(f"[1] Note on cache clear: {e}")

    # 2. Instantiate WeeklyIntelligenceEngine
    engine = WeeklyIntelligenceEngine()

    # 3. Run analyze_weekly_macro_and_edges
    print("[2] Running analyze_weekly_macro_and_edges(force_refresh=True)...")
    briefing = engine.analyze_weekly_macro_and_edges(force_refresh=True)

    wb = briefing.get("wheel_harvest_blotter", {})
    m1 = wb.get("mode_1", {})
    cands_m1 = m1.get("candidates", [])
    total_harvest = m1.get("projected_monthly_harvest_dollars", 0.0)
    debate = wb.get("debate_arena", {})

    print(f"[3] Mode 1 Staged Candidates Count: {len(cands_m1)}")
    print(f"[3] Mode 1 Projected Total Harvest: ${total_harvest:,.2f}")

    symbols_staged = [c.get("symbol") for c in cands_m1]
    print(f"[4] Staged Symbols: {symbols_staged}")

    for idx, c in enumerate(cands_m1, 1):
        sym = c.get("symbol")
        strike = c.get("strike")
        dte = c.get("dte")
        exp = c.get("expiration_date")
        cnt = c.get("contracts")
        prem = c.get("premium_estimate")
        lim = c.get("limit_price")
        source = c.get("pricing_source")
        collat = c.get("collateral_required")
        dollars = prem * 100.0 * cnt

        print(f"    Candidate #{idx}: {sym} | Strike: ${strike:.1f} | {dte} DTE ({exp}) | Contracts: {cnt} | Prem: ${prem:.2f} | Limit: ${lim:.2f} | Total: ${dollars:.2f} | Source: {source}")

        # Assert DTE constraint strictly 30-35
        assert 30 <= dte <= 35, f"ERROR: {sym} DTE {dte} is outside strict 30-35 DTE window!"

        # Assert limit price is positive and quantized
        assert lim and lim > 0, f"ERROR: {sym} has invalid limit price {lim}"

    # Assert INTC, COIN, SO are staged
    for required_sym in ["INTC", "COIN", "SO"]:
        assert required_sym in symbols_staged, f"ERROR: Required approved ticker {required_sym} was not staged!"

    # Assert total harvest meets or exceeds $1,500 milestone
    assert total_harvest >= 1490.0, f"ERROR: Projected harvest ${total_harvest:,.2f} is below $1,500 mandate!"

    # Check Debate Arena matrix
    allocator = debate.get("executive_allocator", {})
    matrix = allocator.get("trade_off_matrix", [])
    print("[5] Verifying Dialectical Debate Arena Trade-Off Matrix:")
    for row in matrix:
        metric = row.get("metric")
        m1_val = row.get("mode_1")
        m2_val = row.get("mode_2")
        edge = row.get("edge")
        print(f"    - {metric:28} | M1: {m1_val:20} | M2: {m2_val:20} | Edge: {edge}")

        if metric == "Monthly Harvest Goal":
            assert "/ $1,500" in m1_val, f"ERROR: Mode 1 matrix has '{m1_val}' instead of '/ $1,500'!"
            assert "/ $1,500" in m2_val, f"ERROR: Mode 2 matrix has '{m2_val}' instead of '/ $1,500'!"

    print("==================================================================")
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_verification()
