import pytest
from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine


def test_dynamic_macro_economic_releases():
    engine = WeeklyIntelligenceEngine()
    releases = engine.fetch_dynamic_macro_economic_releases()

    assert isinstance(releases, list)
    assert len(releases) >= 3

    # Verify zero obsolete hardcoded dates (e.g. Aug 22)
    for r in releases:
        assert "Aug 22" not in r["indicator"], f"Found obsolete Aug 22 in {r['indicator']}"
        assert "215,000" not in str(r.get("actual_prior", "")), f"Found obsolete 215,000 in {r}"
        assert "indicator" in r
        assert "consensus" in r
        assert "actual_prior" in r
        assert "timing" in r

    # Verify Initial Jobless Claims series is present
    icsa = next((r for r in releases if r.get("series_id") == "ICSA"), None)
    assert icsa is not None
    assert "US Initial Jobless Claims" in icsa["indicator"]
    assert "Wk ending" in icsa["indicator"]


def test_render_macro_calendar_markdown_table():
    engine = WeeklyIntelligenceEngine()
    table_md = engine.render_macro_calendar_markdown_table()

    assert "| Economic Indicator / Release | Consensus / Forecast | Actual / Prior | Status / Timing |" in table_md
    assert "| **US Initial Jobless Claims**" in table_md
    assert "Aug 22" not in table_md


def test_dynamic_cross_asset_directional_table():
    engine = WeeklyIntelligenceEngine()
    table = engine.build_cross_asset_directional_table()

    assert isinstance(table, list)
    assert len(table) == 8

    # Verify benchmarks present
    assets = [b["benchmark_code"] for b in table]
    assert "SPY" in assets
    assert "QQQ" in assets
    assert "^TNX" in assets
    assert "USO" in assets
    assert "GLD" in assets
    assert "UUP" in assets
    assert "BTC-USD" in assets
    assert "^VIX" in assets

    table_md = engine.render_cross_asset_markdown_table(table)
    assert "| Asset / Benchmark | Current Level | Daily Change | Market Context / Positioning Bias |" in table_md
    assert "SPY" in table_md
