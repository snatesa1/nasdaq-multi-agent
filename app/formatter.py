"""
Premium presentation layer for Slack (Block Kit) and Email (HTML).

Modular design — each tier is a separate section builder so new agents
can plug in without touching existing sections.

Phase 1: Macro + FRED + Technical
Phase 2: + Fundamental + News sections
Phase 3: + Portfolio + Risk sections
"""

from datetime import datetime
from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════
#  Score Badge Helpers
# ═══════════════════════════════════════════════════════════

def _score_emoji(score: float) -> str:
    """Map 0→1 score to colored emoji."""
    if score is None:
        return "⚪"
    if score >= 0.75:
        return "🟢"
    elif score >= 0.55:
        return "🟡"
    elif score >= 0.35:
        return "🟠"
    else:
        return "🔴"


def _score_bar(score: float, length: int = 10) -> str:
    """ASCII progress bar: ████████░░ 0.80"""
    if score is None:
        return "░" * length
    filled = int(score * length)
    return "█" * filled + "░" * (length - filled)


def _score_label(score: float) -> str:
    """Human-readable trend label for a 0→1 score."""
    if score is None:
        return "N/A"
    if score >= 0.80:
        return "Strong Uptrend"
    elif score >= 0.65:
        return "Emerging Uptrend"
    elif score >= 0.50:
        return "Neutral / Consolidating"
    elif score >= 0.35:
        return "Weakening / Caution"
    else:
        return "Downtrend"


def _market_inference(macro_score: float, fred_score: float, tech_avg: float) -> str:
    """Generate a one-line market inference from the three tier scores."""
    avg = (macro_score + fred_score + tech_avg) / 3
    if avg >= 0.75:
        return "🟢 Strong risk-on environment — NASDAQ favored for growth exposure."
    elif avg >= 0.60:
        return "🟡 Moderate tailwinds — selective long positions in trending names."
    elif avg >= 0.45:
        return "⚪ Mixed signals — reduce position sizes, favor quality over momentum."
    elif avg >= 0.30:
        return "🟠 Defensive posture — macro headwinds building, trim speculative longs."
    else:
        return "🔴 Risk-off regime — capital preservation, consider hedges."


# ═══════════════════════════════════════════════════════════
#  SLACK BLOCK KIT FORMATTER
# ═══════════════════════════════════════════════════════════

def format_slack_blocks(result: Dict) -> List[Dict]:
    """
    Build Slack Block Kit blocks for rich, structured messages.
    Returns list of blocks to pass to chat_postMessage(blocks=...).
    """
    blocks = []

    # ── Header ───────────────────────────────────────────
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": "📊 NASDAQ Multi-Agent Analysis", "emoji": True}
    })
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"🕐 {_format_timestamp(result.get('timestamp'))}  •  ⏱️ {result.get('duration_seconds', 0)}s  •  Phase 1"}
        ]
    })
    blocks.append({"type": "divider"})

    # ── Market Inference (top-level) ──────────────────────
    tier1 = result.get("tier1", {})
    macro_s = tier1.get("macro", {}).get("score", 0) or 0
    fred_s = tier1.get("fred_indicators", {}).get("score", 0) or 0
    tech_results = result.get("tier2", {}).get("technical", [])
    tech_avg = sum(t.get("score", 0) or 0 for t in tech_results) / max(len(tech_results), 1) if tech_results else 0
    inference = _market_inference(macro_s, fred_s, tech_avg)

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Market Inference:* {inference}"}
    })
    blocks.append({"type": "divider"})

    # ── Tier 1: Macro Analysis ───────────────────────────
    blocks.extend(_build_macro_blocks(result))
    blocks.append({"type": "divider"})

    # ── Tier 1: FRED Indicators ──────────────────────────
    blocks.extend(_build_fred_blocks(result))
    blocks.append({"type": "divider"})

    # ── Tier 2: Technical Analysis ───────────────────────
    blocks.extend(_build_technical_blocks(result))
    blocks.append({"type": "divider"})

    # ── Tier 2: Fundamental Analysis (Phase 2) ──────────
    blocks.extend(_build_fundamental_blocks(result))
    blocks.append({"type": "divider"})

    # ── Phase Roadmap ────────────────────────────────────
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "🔜 *Phase 2:* News Sentiment  •  *Phase 3:* Portfolio + Risk"}
    })

    # ── Footer ───────────────────────────────────────────
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "Multi-agent research system."}
        ]
    })

    return blocks


def format_slack_message(result: Dict) -> str:
    """
    Fallback plain-text format (used as `text` parameter for notifications).
    Also used when Block Kit is unavailable.
    """
    tier1 = result.get("tier1", {})
    macro = tier1.get("macro", {})
    fred = tier1.get("fred_indicators", {})
    tier2 = result.get("tier2", {})
    tech_results = tier2.get("technical", [])

    macro_score = macro.get("score", 0)
    fred_score = fred.get("score", 0)
    sectors = macro.get("data", {}).get("selected_sectors", [])

    lines = [
        "📊 *NASDAQ Multi-Agent Analysis*",
        f"🕐 {_format_timestamp(result.get('timestamp'))} | ⏱️ {result.get('duration_seconds', 0)}s",
        "",
        f"🌍 *Macro* {_score_emoji(macro_score)} {_score_bar(macro_score)} {macro_score:.2f}",
        f"🏆 {', '.join(sectors)}",
        "",
        f"📈 *FRED* {_score_emoji(fred_score)} {_score_bar(fred_score)} {fred_score:.2f}",
    ]

    # FRED key metrics inline
    fred_data = fred.get("data", {})
    leading = fred_data.get("leading_indicators", {})
    yc = leading.get("T10Y2Y", {})
    indpro = leading.get("INDPRO", {})
    if yc:
        lines.append(f"  Yield Curve: {yc.get('latest', 'N/A')} ({yc.get('trend', '')})")
    if indpro:
        lines.append(f"  Industrial Production: {indpro.get('latest', 'N/A')} ({indpro.get('trend', '')})")

    # Technical summary
    if tech_results:
        lines.append("")
        lines.append("⚡ *Technical Scores:*")
        lines.append("```")
        lines.append(f"{'Symbol':<7} {'Score':>5} {'Regime':<12} {'RSI':>5} {'ADX':>5} {'Hurst':>6}")
        lines.append("─" * 48)
        for tr in tech_results:
            sym = tr.get("data", {}).get("symbol", "?")
            sc = tr.get("score", 0)
            reg = tr.get("data", {}).get("regime", "?")
            ind = tr.get("data", {}).get("indicators", {})
            lines.append(
                f"{sym:<7} {sc:>5.2f} {reg:<12} {ind.get('rsi', 0):>5.1f} {ind.get('adx', 0):>5.1f} {ind.get('hurst', 0):>6.3f}"
            )
        lines.append("```")

    lines.append("")
    lines.append("_Multi-Agent System v1.0 — Phase 1_")
    return "\n".join(lines)


# ── Slack Block Builders ─────────────────────────────────

def _build_macro_blocks(result: Dict) -> List[Dict]:
    """Build Slack blocks for Macro Agent section."""
    tier1 = result.get("tier1", {})
    macro = tier1.get("macro", {})
    score = macro.get("score", 0)
    sectors = macro.get("data", {}).get("selected_sectors", [])
    sliding = macro.get("data", {}).get("sliding_window_comparison", {})

    blocks = []

    # Section header — clean: emoji + score only (no bars or trend labels)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"🌍 *Macro Analysis*  {_score_emoji(score)} *{score:.2f}*"
        }
    })

    # Top sectors as fields
    sector_fields = []
    sector_scores = macro.get("data", {}).get("sector_scores", {})
    for sector in sectors:
        s = sector_scores.get(sector, 0)
        sector_fields.append({
            "type": "mrkdwn",
            "text": f"*{sector}*\n{_score_emoji(s)} {s:.3f}"
        })

    if sector_fields:
        blocks.append({"type": "section", "fields": sector_fields[:6]})  # Max 6 fields

    # Sliding window comparison — dynamic year columns
    if sliding:
        # Collect all unique years across all sectors, sorted
        all_years = set()
        for sector_data in sliding.values():
            all_years.update(sector_data.keys())
        sorted_years = sorted(y for y in all_years if y.isdigit())

        # Identify the "current" year (most recent)
        current_year_str = str(datetime.now().year) if datetime else sorted_years[-1] if sorted_years else ""

        # Build header row dynamically
        header = f"{'Sector':<15}"
        for yr in sorted_years:
            label = "Now" if yr == current_year_str else yr
            header += f" {label:>7}"

        sw_text = "*📊 Historical Comparison (sliding window):*\n```\n"
        sw_text += header + "\n"
        sw_text += "─" * (15 + 8 * len(sorted_years)) + "\n"

        for sector in sectors:
            sw = sliding.get(sector, {})
            row = f"{sector[:14]:<15}"
            for yr in sorted_years:
                ret = sw.get(yr, {}).get("return_pct", "—")
                row += f" {ret if isinstance(ret, str) else f'{ret:>+.1f}':>7}"
            sw_text += row + "\n"

        sw_text += "```"
        sw_text += "\n_*Some sectors may lack data in older years due to ETF inception dates._"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": sw_text}})

    return blocks


def _build_fred_blocks(result: Dict) -> List[Dict]:
    """Build Slack blocks for FRED Indicators section."""
    tier1 = result.get("tier1", {})
    fred = tier1.get("fred_indicators", {})
    score = fred.get("score", 0)
    data = fred.get("data", {})
    leading_score = data.get("leading_score", 0)
    lagging_score = data.get("lagging_score", 0)

    blocks = []

    # Header with score — clean: emoji + score only
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"📈 *FRED Economic Indicators*  {_score_emoji(score)} *{score:.2f}*"
        }
    })

    # Leading vs Lagging scores
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Leading (65%)*\n{_score_emoji(leading_score)} {leading_score:.3f}"},
            {"type": "mrkdwn", "text": f"*Lagging (35%)*\n{_score_emoji(lagging_score)} {lagging_score:.3f}"},
        ]
    })

    # Key indicators table
    leading = data.get("leading_indicators", {})
    lagging = data.get("lagging_indicators", {})

    indicator_text = "*Key Readings:*\n```\n"
    indicator_text += f"{'Indicator':<28} {'Value':>8} {'Trend':>8}\n"
    indicator_text += "─" * 46 + "\n"

    # Show most important indicators
    key_series = [
        ("T10Y2Y", leading),
        ("INDPRO", leading),
        ("T5YIFR", leading),
        ("UMCSENT", leading),
        ("UNRATE", lagging),
        ("FEDFUNDS", lagging),
    ]
    for sid, source in key_series:
        ind = source.get(sid, {})
        if ind:
            name = ind.get("name", sid)[:27]
            val = ind.get("latest", 0)
            trend = ind.get("trend", "?")
            trend_emoji = "📈" if trend == "rising" else "📉" if trend == "falling" else "➡️"
            indicator_text += f"{name:<28} {val:>8.2f} {trend_emoji} {trend:<6}\n"

    indicator_text += "```"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": indicator_text}})

    # Rationale
    rationale = fred.get("rationale", "")
    if rationale:
        # Show first 2 lines of assessment
        assessment = rationale.split("\n")[0]
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": assessment}]
        })

    return blocks


def _build_technical_blocks(result: Dict) -> List[Dict]:
    """Build Slack blocks for Technical Analysis section."""
    tier2 = result.get("tier2", {})
    tech_results = tier2.get("technical", [])

    blocks = []

    if not tech_results:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "⚡ *Technical Analysis* — no stocks analyzed"}
        })
        return blocks

    # Overall header
    avg_score = sum(t.get("score", 0) or 0 for t in tech_results) / max(len(tech_results), 1)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"⚡ *Technical Analysis*  ({len(tech_results)} stocks)  •  Avg: {_score_emoji(avg_score)} *{avg_score:.2f}*"
        }
    })

    # Scoreboard table
    table_text = "```\n"
    table_text += f"{'':>2} {'Symbol':<7} {'Score':>5} {'Regime':<13} {'RSI':>5} {'ADX':>5} {'Hurst':>6} {'MACD':>6}\n"
    table_text += "─" * 55 + "\n"

    for tr in tech_results:
        sym = tr.get("data", {}).get("symbol", "?")
        sc = tr.get("score") or 0
        regime = tr.get("data", {}).get("regime", "?")
        momentum = tr.get("data", {}).get("momentum_regime", "?")
        ind = tr.get("data", {}).get("indicators", {})

        emoji = _score_emoji(sc)
        rsi = ind.get("rsi", 0)
        adx = ind.get("adx", 0)
        hurst = ind.get("hurst", 0)
        macd_bull = "✅" if ind.get("macd_bullish") else "❌"

        table_text += f"{emoji:>2} {sym:<7} {sc:>5.2f} {regime:<13} {rsi:>5.1f} {adx:>5.1f} {hurst:>6.3f} {macd_bull:>6}\n"

    table_text += "```"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": table_text}})

    # Top 3 highlights with details
    sorted_tech = sorted(tech_results, key=lambda t: t.get("score", 0) or 0, reverse=True)
    top3 = sorted_tech[:3]

    if top3:
        detail_fields = []
        for tr in top3:
            sym = tr.get("data", {}).get("symbol", "?")
            ind = tr.get("data", {}).get("indicators", {})
            sc = tr.get("score") or 0
            momentum = tr.get("data", {}).get("momentum_regime", "?")
            vol = ind.get("volatility_level", "?")
            atr_pct = ind.get("atr_pct", 0)
            bb_zone = ind.get("bb_zone", "?")
            hurst_class = ind.get("hurst_classification", "?")

            detail = (
                f"*{sym}* {_score_emoji(sc)} {sc:.2f}\n"
                f"${ind.get('price', 0):.2f} • {momentum.replace('_', ' ').title()}\n"
                f"Vol: {vol} ({atr_pct:.1f}%) • BB: {bb_zone}\n"
                f"Hurst: {hurst_class}"
            )
            detail_fields.append({"type": "mrkdwn", "text": detail})

        blocks.append({"type": "section", "fields": detail_fields[:3]})

    return blocks


def _build_fundamental_blocks(result: Dict) -> List[Dict]:
    """Build Slack blocks for Fundamental Analysis section (Phase 2)."""
    tier2 = result.get("tier2", {})
    fund_results = tier2.get("fundamental", [])

    blocks = []

    if not fund_results:
        return blocks  # Silently skip if no data yet

    avg_score = sum(f.get("score", 0) or 0 for f in fund_results) / max(len(fund_results), 1)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"📊 *Fundamental Analysis*  ({len(fund_results)} stocks)  •  Avg: {_score_emoji(avg_score)} *{avg_score:.2f}*"
        }
    })

    # Fundamental scoreboard
    table_text = "```\n"
    table_text += f"{'':>2} {'Symbol':<7} {'Score':>5} {'PE':>7} {'PB':>6} {'ROE':>7} {'Margin':>7} {'F-Sc':>5} {'Z-Sc':>5}\n"
    table_text += "─" * 58 + "\n"

    for fr in fund_results:
        sym = fr.get("data", {}).get("symbol", "?")
        sc = fr.get("score") or 0
        d = fr.get("data", {}).get("metrics", {})
        emoji = _score_emoji(sc)
        pe = d.get("pe_ratio", 0)
        pb = d.get("pb_ratio", 0)
        roe = d.get("roe", 0) * 100 if d.get("roe") else 0
        margin = d.get("net_margin", 0) * 100 if d.get("net_margin") else 0
        f_score = d.get("piotroski_score", 0)
        z_score = d.get("altman_z_score", 0)

        table_text += f"{emoji:>2} {sym:<7} {sc:>5.2f} {pe:>7.1f} {pb:>6.1f} {roe:>6.1f}% {margin:>6.1f}% {f_score:>5.0f} {z_score:>5.1f}\n"

    table_text += "```"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": table_text}})

    # ── 📖 Metric Guide (layman explanations) ────────────
    explanations = _extract_metric_explanations(fund_results)
    if explanations:
        # Show key metrics used in the table
        guide_metrics = [
            ("P/E", "pe_ratio"),
            ("P/B", "pb_ratio"),
            ("ROE", "roe"),
            ("Net Margin", "net_margin"),
            ("F-Score", "piotroski_score"),
            ("Z-Score", "altman_z_score"),
        ]
        guide_text = "📖 *Metric Guide — What Do These Numbers Mean?*\n"
        for label, key in guide_metrics:
            desc = explanations.get(key, "")
            if desc:
                guide_text += f"• *{label}*: {desc}\n"

        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": guide_text}})

    return blocks

# ── Helpers ──────────────────────────────────────────────


def _extract_metric_explanations(fund_results: List[Dict]) -> Dict:
    """Extract metric_explanations from the first fund result that has them."""
    for fr in fund_results:
        explanations = fr.get("data", {}).get("metrics", {}).get("metric_explanations")
        if explanations:
            return explanations
    return {}

def _format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format."""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%b %d, %Y %I:%M %p SGT")
    except Exception:
        return ts[:19]


# ═══════════════════════════════════════════════════════════
#  HTML EMAIL FORMATTER
# ═══════════════════════════════════════════════════════════

def format_email(result: Dict) -> str:
    """
    Premium dark-theme HTML email with the full analysis report.
    Designed for Gmail/Outlook rendering.
    """
    tier1 = result.get("tier1", {})
    macro = tier1.get("macro", {})
    fred = tier1.get("fred_indicators", {})
    tier2 = result.get("tier2", {})
    tech_results = tier2.get("technical", [])

    macro_score = macro.get("score", 0) or 0
    fred_score = fred.get("score", 0) or 0
    sectors = macro.get("data", {}).get("selected_sectors", [])

    # Pre-compute values
    avg_tech = sum(t.get("score", 0) or 0 for t in tech_results) / max(len(tech_results), 1) if tech_results else 0
    timestamp = _format_timestamp(result.get("timestamp"))
    duration = result.get("duration_seconds", 0)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#0d1117; font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;">
<tr><td align="center" style="padding:20px 10px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#161b22; border-radius:12px; overflow:hidden; border:1px solid #30363d;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#1a73e8,#667eea); padding:28px 30px;">
  <h1 style="margin:0; color:white; font-size:22px; font-weight:600;">📊 NASDAQ Multi-Agent Analysis</h1>
  <p style="margin:6px 0 0; color:rgba(255,255,255,0.8); font-size:13px;">
    {timestamp}  •  {duration}s  •  Phase 1
  </p>
</td></tr>

<!-- Score Summary + Inference -->
<tr><td style="padding:20px 30px 10px;">
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="33%" style="text-align:center; padding:10px 6px; background:#1c2128; border-radius:8px 0 0 8px; border-right:1px solid #30363d;">
      <div style="color:#8b949e; font-size:10px; text-transform:uppercase; letter-spacing:1px;">Macro</div>
      <div style="color:{_score_color(macro_score)}; font-size:16px; font-weight:700; margin-top:2px;">{_score_emoji(macro_score)} {macro_score:.2f}</div>
      <div style="color:#8b949e; font-size:10px;">{_score_label(macro_score)}</div>
    </td>
    <td width="33%" style="text-align:center; padding:10px 6px; background:#1c2128; border-right:1px solid #30363d;">
      <div style="color:#8b949e; font-size:10px; text-transform:uppercase; letter-spacing:1px;">FRED</div>
      <div style="color:{_score_color(fred_score)}; font-size:16px; font-weight:700; margin-top:2px;">{_score_emoji(fred_score)} {fred_score:.2f}</div>
      <div style="color:#8b949e; font-size:10px;">{_score_label(fred_score)}</div>
    </td>
    <td width="33%" style="text-align:center; padding:10px 6px; background:#1c2128; border-radius:0 8px 8px 0;">
      <div style="color:#8b949e; font-size:10px; text-transform:uppercase; letter-spacing:1px;">Technical</div>
      <div style="color:{_score_color(avg_tech)}; font-size:16px; font-weight:700; margin-top:2px;">{_score_emoji(avg_tech)} {avg_tech:.2f}</div>
      <div style="color:#8b949e; font-size:10px;">{_score_label(avg_tech)}</div>
    </td>
  </tr>
  </table>
  <div style="background:#0d1117; border-radius:6px; padding:8px 12px; margin-top:8px; border-left:3px solid {_score_color((macro_score + fred_score + avg_tech) / 3)};">
    <span style="color:#e6edf3; font-size:12px;">{_market_inference(macro_score, fred_score, avg_tech)}</span>
  </div>
</td></tr>

<!-- Macro Section -->
<tr><td style="padding:15px 30px 5px;">
  <h2 style="margin:0; color:#e6edf3; font-size:16px; border-bottom:1px solid #30363d; padding-bottom:8px;">
    🌍 Macro — Top Sectors
  </h2>
</td></tr>
<tr><td style="padding:5px 30px 15px;">
  {_email_sector_pills(sectors, macro.get("data", {}).get("sector_scores", {}))}
  {_email_sliding_window(macro.get("data", {}).get("sliding_window_comparison", {}), sectors)}
</td></tr>

<!-- FRED Section -->
<tr><td style="padding:15px 30px 5px;">
  <h2 style="margin:0; color:#e6edf3; font-size:16px; border-bottom:1px solid #30363d; padding-bottom:8px;">
    📈 FRED Economic Indicators
  </h2>
</td></tr>
<tr><td style="padding:5px 30px 15px;">
  {_email_fred_table(fred)}
  <p style="color:#8b949e; font-size:13px; margin:8px 0 0; font-style:italic;">
    {(fred.get("rationale", "") or "").split(chr(10))[0]}
  </p>
</td></tr>

<!-- Technical Section -->
<tr><td style="padding:15px 30px 5px;">
  <h2 style="margin:0; color:#e6edf3; font-size:16px; border-bottom:1px solid #30363d; padding-bottom:8px;">
    ⚡ Technical Analysis ({len(tech_results)} stocks)
  </h2>
</td></tr>
<tr><td style="padding:5px 30px 15px;">
  {_email_tech_table(tech_results)}
</td></tr>

<!-- Fundamental Section (Phase 2) -->
{_email_fundamental_section(result)}

<!-- Universe -->
<tr><td style="padding:10px 30px;">
  <div style="background:#1c2128; border-radius:8px; padding:12px 16px; border:1px solid #30363d;">
    <span style="color:#8b949e; font-size:12px;">📋 Stock Universe: </span>
    <span style="color:#c9d1d9; font-size:12px;">{', '.join(result.get('stock_universe', []))}</span>
  </div>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 30px; text-align:center; border-top:1px solid #30363d; margin-top:10px;">
  <p style="color:#484f58; font-size:11px; margin:0;">
    ⚠️ Not financial advice. Multi-agent research system for educational purposes only.
  </p>
  <p style="color:#30363d; font-size:10px; margin:4px 0 0;">
    NASDAQ Multi-Agent System v1.0
  </p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html


# ── Email HTML Helpers ───────────────────────────────────

def _score_color(score: float) -> str:
    """Score → CSS color for email."""
    if score is None:
        return "#8b949e"
    if score >= 0.75:
        return "#3fb950"
    elif score >= 0.55:
        return "#d29922"
    elif score >= 0.35:
        return "#db6d28"
    else:
        return "#f85149"


def _email_sector_pills(sectors: List[str], scores: Dict) -> str:
    """Render sector score pills."""
    pills = ""
    for sector in sectors:
        s = scores.get(sector, 0)
        color = _score_color(s)
        pills += f"""<span style="display:inline-block; background:#1c2128; border:1px solid {color};
            border-radius:16px; padding:4px 14px; margin:3px 4px; font-size:12px; color:{color}; font-weight:600;">
            {sector} {s:.3f}</span>"""
    return f'<div style="margin:8px 0;">{pills}</div>'


def _email_sliding_window(sliding: Dict, sectors: List[str]) -> str:
    """Render sliding window comparison table for email — dynamic year columns."""
    if not sliding:
        return ""

    # Collect all unique years across all sectors, sorted
    from datetime import datetime as _dt
    all_years = set()
    for sector_data in sliding.values():
        all_years.update(sector_data.keys())
    sorted_years = sorted(y for y in all_years if y.isdigit())
    current_year_str = str(_dt.now().year)

    # Build header row dynamically
    year_headers = ""
    for yr in sorted_years:
        label = "NOW" if yr == current_year_str else yr
        year_headers += f'<th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">{label}</th>'

    rows = ""
    for sector in sectors:
        sw = sliding.get(sector, {})
        if not sw:
            continue
        cells = f'<td style="padding:6px 8px; color:#c9d1d9; font-weight:600; font-size:12px;">{sector[:15]}</td>'
        for yr in sorted_years:
            ret = sw.get(yr, {}).get("return_pct")
            if ret is not None:
                color = "#3fb950" if ret > 0 else "#f85149"
                weight = "font-weight:700;" if yr == current_year_str else ""
                cells += f'<td style="padding:6px 8px; text-align:center; color:{color}; font-size:12px; {weight}">{ret:+.1f}%</td>'
            else:
                cells += '<td style="padding:6px 8px; text-align:center; color:#484f58; font-size:12px;">—</td>'
        rows += f"<tr style='border-bottom:1px solid #21262d;'>{cells}</tr>"

    return f"""
    <table style="width:100%; border-collapse:collapse; margin-top:8px; background:#0d1117; border-radius:6px; overflow:hidden;">
    <tr style="background:#161b22; border-bottom:1px solid #30363d;">
        <th style="padding:8px; text-align:left; color:#8b949e; font-size:11px; text-transform:uppercase;">Sector</th>
        {year_headers}
    </tr>
    {rows}
    </table>
    <p style="color:#484f58; font-size:10px; margin:4px 0 0;">Sliding window indexed to 100 at start • Some sectors lack data in older years due to ETF inception dates</p>
    """


def _email_fred_table(fred: Dict) -> str:
    """Render FRED indicators table for email."""
    data = fred.get("data", {})
    leading = data.get("leading_indicators", {})
    lagging = data.get("lagging_indicators", {})

    rows = ""
    key_indicators = [
        ("T10Y2Y", leading, "leading"),
        ("INDPRO", leading, "leading"),
        ("T5YIFR", leading, "leading"),
        ("UMCSENT", leading, "leading"),
        ("UNRATE", lagging, "lagging"),
        ("FEDFUNDS", lagging, "lagging"),
        ("CP", lagging, "lagging"),
    ]

    for sid, source, category in key_indicators:
        ind = source.get(sid, {})
        if ind:
            name = ind.get("name", sid)
            val = ind.get("latest", 0)
            trend = ind.get("trend", "?")
            trend_icon = "↗️" if trend == "rising" else "↘️" if trend == "falling" else "→"
            trend_color = "#3fb950" if trend == "rising" else "#f85149" if trend == "falling" else "#8b949e"
            cat_color = "#58a6ff" if category == "leading" else "#8b949e"

            rows += f"""<tr style="border-bottom:1px solid #21262d;">
                <td style="padding:6px 8px; color:#c9d1d9; font-size:12px;">{name[:30]}</td>
                <td style="padding:6px 8px; text-align:center; color:{cat_color}; font-size:10px; text-transform:uppercase;">{category}</td>
                <td style="padding:6px 8px; text-align:right; color:#c9d1d9; font-size:12px; font-weight:600;">{val:.2f}</td>
                <td style="padding:6px 8px; text-align:center; color:{trend_color}; font-size:12px;">{trend_icon} {trend}</td>
            </tr>"""

    return f"""
    <table style="width:100%; border-collapse:collapse; background:#0d1117; border-radius:6px; overflow:hidden;">
    <tr style="background:#161b22; border-bottom:1px solid #30363d;">
        <th style="padding:8px; text-align:left; color:#8b949e; font-size:11px;">Indicator</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Type</th>
        <th style="padding:8px; text-align:right; color:#8b949e; font-size:11px;">Value</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Trend</th>
    </tr>
    {rows}
    </table>
    """


def _email_tech_table(tech_results: List[Dict]) -> str:
    """Render technical analysis scoreboard for email."""
    if not tech_results:
        return '<p style="color:#8b949e;">No technical data available.</p>'

    rows = ""
    for i, tr in enumerate(sorted(tech_results, key=lambda t: t.get("score", 0) or 0, reverse=True)):
        sym = tr.get("data", {}).get("symbol", "?")
        sc = tr.get("score") or 0
        regime = tr.get("data", {}).get("regime", "?")
        momentum = tr.get("data", {}).get("momentum_regime", "?")
        ind = tr.get("data", {}).get("indicators", {})
        bg = "#161b22" if i % 2 == 0 else "#0d1117"
        sc_color = _score_color(sc)

        rsi = ind.get("rsi", 0)
        rsi_color = "#f85149" if rsi > 70 else "#3fb950" if rsi < 30 else "#c9d1d9"

        macd_icon = "✅" if ind.get("macd_bullish") else "❌"
        price = ind.get("price", 0)

        rows += f"""<tr style="background:{bg};">
            <td style="padding:8px; color:#c9d1d9; font-weight:700; font-size:13px;">{sym}</td>
            <td style="padding:8px; text-align:right; color:#8b949e; font-size:12px;">${price:.2f}</td>
            <td style="padding:8px; text-align:center;">
                <span style="background:{sc_color}22; color:{sc_color}; padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600;">{sc:.2f}</span>
            </td>
            <td style="padding:8px; text-align:center; color:#c9d1d9; font-size:11px;">{regime}</td>
            <td style="padding:8px; text-align:center; color:{rsi_color}; font-size:12px;">{rsi:.1f}</td>
            <td style="padding:8px; text-align:center; color:#c9d1d9; font-size:12px;">{ind.get('adx', 0):.1f}</td>
            <td style="padding:8px; text-align:center; color:#c9d1d9; font-size:12px;">{ind.get('hurst', 0):.3f}</td>
            <td style="padding:8px; text-align:center; font-size:12px;">{macd_icon}</td>
        </tr>"""

    return f"""
    <table style="width:100%; border-collapse:collapse; background:#0d1117; border-radius:6px; overflow:hidden;">
    <tr style="background:#161b22; border-bottom:1px solid #30363d;">
        <th style="padding:8px; text-align:left; color:#8b949e; font-size:11px;">Stock</th>
        <th style="padding:8px; text-align:right; color:#8b949e; font-size:11px;">Price</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Score</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Regime</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">RSI</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">ADX</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Hurst</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">MACD</th>
    </tr>
    {rows}
    </table>
    """


def _email_fundamental_section(result: Dict) -> str:
    """Render fundamental analysis section for email (Phase 2)."""
    tier2 = result.get("tier2", {})
    fund_results = tier2.get("fundamental", [])

    if not fund_results:
        return ""  # Silently skip if not yet available

    rows = ""
    for i, fr in enumerate(sorted(fund_results, key=lambda f: f.get("score", 0) or 0, reverse=True)):
        sym = fr.get("data", {}).get("symbol", "?")
        sc = fr.get("score") or 0
        d = fr.get("data", {}).get("metrics", {})
        bg = "#161b22" if i % 2 == 0 else "#0d1117"
        sc_color = _score_color(sc)

        pe = d.get("pe_ratio", 0)
        pb = d.get("pb_ratio", 0)
        roe = d.get("roe", 0) * 100 if d.get("roe") else 0
        margin = d.get("net_margin", 0) * 100 if d.get("net_margin") else 0
        f_score = d.get("piotroski_score", 0)
        z_score = d.get("altman_z_score", 0)

        # Z-Score zone color
        z_color = "#3fb950" if z_score > 2.99 else "#d29922" if z_score > 1.81 else "#f85149"

        rows += f"""<tr style="background:{bg};">
            <td style="padding:7px 8px; color:#c9d1d9; font-weight:700; font-size:13px;">{sym}</td>
            <td style="padding:7px 4px; text-align:center;">
                <span style="background:{sc_color}22; color:{sc_color}; padding:2px 8px; border-radius:10px; font-size:12px; font-weight:600;">{sc:.2f}</span>
            </td>
            <td style="padding:7px 4px; text-align:center; color:#c9d1d9; font-size:12px;">{pe:.1f}</td>
            <td style="padding:7px 4px; text-align:center; color:#c9d1d9; font-size:12px;">{pb:.1f}</td>
            <td style="padding:7px 4px; text-align:center; color:#c9d1d9; font-size:12px;">{roe:.1f}%</td>
            <td style="padding:7px 4px; text-align:center; color:#c9d1d9; font-size:12px;">{margin:.1f}%</td>
            <td style="padding:7px 4px; text-align:center; color:#c9d1d9; font-size:12px;">{f_score:.0f}/9</td>
            <td style="padding:7px 4px; text-align:center; color:{z_color}; font-size:12px;">{z_score:.1f}</td>
        </tr>"""

    # ── 📖 Metric Guide (layman explanations) ────────────
    explanations = _extract_metric_explanations(fund_results)
    guide_html = ""
    if explanations:
        guide_metrics = [
            ("P/E", "pe_ratio"),
            ("P/B", "pb_ratio"),
            ("ROE", "roe"),
            ("Net Margin", "net_margin"),
            ("F-Score", "piotroski_score"),
            ("Z-Score", "altman_z_score"),
        ]
        guide_rows = ""
        for label, key in guide_metrics:
            desc = explanations.get(key, "")
            if desc:
                guide_rows += f"""<tr style="border-bottom:1px solid #21262d;">
                    <td style="padding:6px 10px; color:#58a6ff; font-weight:600; font-size:12px; white-space:nowrap; vertical-align:top;">{label}</td>
                    <td style="padding:6px 10px; color:#c9d1d9; font-size:11px; line-height:1.5;">{desc}</td>
                </tr>"""

        guide_html = f"""
        <div style="margin-top:12px;">
            <div style="color:#8b949e; font-size:12px; font-weight:600; margin-bottom:6px;">📖 Metric Guide — What Do These Numbers Mean?</div>
            <table style="width:100%; border-collapse:collapse; background:#0d1117; border-radius:6px; overflow:hidden; border:1px solid #21262d;">
            {guide_rows}
            </table>
        </div>"""

    return f"""
<tr><td style="padding:15px 30px 5px;">
  <h2 style="margin:0; color:#e6edf3; font-size:16px; border-bottom:1px solid #30363d; padding-bottom:8px;">
    📊 Fundamental Analysis ({len(fund_results)} stocks)
  </h2>
</td></tr>
<tr><td style="padding:5px 30px 15px;">
    <table style="width:100%; border-collapse:collapse; background:#0d1117; border-radius:6px; overflow:hidden;">
    <tr style="background:#161b22; border-bottom:1px solid #30363d;">
        <th style="padding:8px; text-align:left; color:#8b949e; font-size:11px;">Stock</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Score</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">P/E</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">P/B</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">ROE</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Margin</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">F-Score</th>
        <th style="padding:8px; text-align:center; color:#8b949e; font-size:11px;">Z-Score</th>
    </tr>
    {rows}
    </table>
    {guide_html}
</td></tr>
"""

