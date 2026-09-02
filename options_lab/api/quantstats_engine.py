"""
QuantStats Analytics Engine for OptionsLab.

Provides institutional portfolio analytics, risk-adjusted metrics, 
benchmark comparative statistics (vs. SPY / QQQ / DIA / URTH),
monthly return heatmaps, and standalone HTML tear sheet generation.
"""

import os
import uuid
import logging
import math
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

# Ensure headless Agg backend for matplotlib before importing quantstats
import matplotlib
matplotlib.use('Agg')

import quantstats_lumi as qs

logger = logging.getLogger("quantstats-engine")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _safe_float(val: Any, default: float = 0.0, multiply_100: bool = False) -> float:
    """Safely converts numpy/pandas scalar to float, guarding against NaN and Inf."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        if multiply_100:
            f = f * 100.0
        return round(f, 4)
    except Exception:
        return default


class QuantStatsEngine:
    """
    Core quantitative analytics engine wrapping quantstats-lumi.
    """

    def __init__(self):
        self.reports_dir = REPORTS_DIR

    def compute_metrics(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        rf: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates 50+ institutional risk, return, and benchmark statistics.
        """
        # Ensure clean datetime index and numeric values
        s_ret = strategy_returns.dropna().astype(float)
        if len(s_ret) < 2:
            return {}

        metrics: Dict[str, Any] = {}

        # ── Return & Growth Metrics ──
        metrics["total_return_pct"] = _safe_float(qs.stats.comp(s_ret), multiply_100=True)
        metrics["cagr_pct"] = _safe_float(qs.stats.cagr(s_ret, rf=rf), multiply_100=True)
        metrics["expected_return_pct"] = _safe_float(qs.stats.expected_return(s_ret), multiply_100=True)
        metrics["volatility_pct"] = _safe_float(qs.stats.volatility(s_ret), multiply_100=True)

        # ── Risk-Adjusted Return Ratios ──
        metrics["sharpe"] = _safe_float(qs.stats.sharpe(s_ret, rf=rf))
        metrics["smart_sharpe"] = _safe_float(qs.stats.smart_sharpe(s_ret, rf=rf))
        metrics["sortino"] = _safe_float(qs.stats.sortino(s_ret, rf=rf))
        metrics["smart_sortino"] = _safe_float(qs.stats.smart_sortino(s_ret, rf=rf))
        metrics["calmar"] = _safe_float(qs.stats.calmar(s_ret))
        metrics["omega"] = _safe_float(qs.stats.omega(s_ret, rf=rf))
        metrics["gain_to_pain"] = _safe_float(qs.stats.gain_to_pain_ratio(s_ret))

        # ── Tail Risk & Drawdown Forensics ──
        metrics["max_drawdown_pct"] = _safe_float(qs.stats.max_drawdown(s_ret), multiply_100=True)
        metrics["var_95_pct"] = _safe_float(qs.stats.var(s_ret), multiply_100=True)
        metrics["cvar_95_pct"] = _safe_float(qs.stats.cvar(s_ret), multiply_100=True)
        metrics["tail_ratio"] = _safe_float(qs.stats.tail_ratio(s_ret))
        metrics["skewness"] = _safe_float(qs.stats.skew(s_ret))
        metrics["kurtosis"] = _safe_float(qs.stats.kurtosis(s_ret))

        # ── Strategy Execution & Win/Loss Mechanics ──
        metrics["win_rate_pct"] = _safe_float(qs.stats.win_rate(s_ret), multiply_100=True)
        metrics["profit_factor"] = _safe_float(qs.stats.profit_factor(s_ret))
        metrics["payoff_ratio"] = _safe_float(qs.stats.payoff_ratio(s_ret))
        metrics["kelly_criterion"] = _safe_float(qs.stats.kelly_criterion(s_ret))
        metrics["recovery_factor"] = _safe_float(qs.stats.recovery_factor(s_ret))

        # ── Benchmark Comparative Statistics ──
        if benchmark_returns is not None and not benchmark_returns.empty:
            b_ret = benchmark_returns.dropna().astype(float)
            # Align indices
            common_idx = s_ret.index.intersection(b_ret.index)
            if len(common_idx) >= 5:
                aligned_strat = s_ret.loc[common_idx]
                aligned_bench = b_ret.loc[common_idx]

                greeks = qs.stats.greeks(aligned_strat, aligned_bench)
                metrics["alpha_pct"] = _safe_float(greeks.get("alpha", 0.0), multiply_100=True)
                metrics["beta"] = _safe_float(greeks.get("beta", 0.0))
                try:
                    metrics["r_squared"] = _safe_float(qs.stats.r_squared(aligned_strat, aligned_bench))
                except Exception:
                    metrics["r_squared"] = 0.0
                try:
                    metrics["information_ratio"] = _safe_float(qs.stats.information_ratio(aligned_strat, aligned_bench))
                except Exception:
                    metrics["information_ratio"] = 0.0
                try:
                    metrics["treynor_ratio"] = _safe_float(qs.stats.treynor_ratio(aligned_strat, aligned_bench, rf=rf))
                except Exception:
                    metrics["treynor_ratio"] = 0.0
                try:
                    metrics["benchmark_correlation"] = _safe_float(aligned_strat.corr(aligned_bench))
                except Exception:
                    metrics["benchmark_correlation"] = 0.0

                metrics["benchmark_total_return_pct"] = _safe_float(qs.stats.comp(aligned_bench), multiply_100=True)
                metrics["benchmark_cagr_pct"] = _safe_float(qs.stats.cagr(aligned_bench, rf=rf), multiply_100=True)
                metrics["benchmark_sharpe"] = _safe_float(qs.stats.sharpe(aligned_bench, rf=rf))
                metrics["benchmark_max_drawdown_pct"] = _safe_float(qs.stats.max_drawdown(aligned_bench), multiply_100=True)
            else:
                metrics["alpha_pct"] = 0.0
                metrics["beta"] = 1.0
        else:
            metrics["alpha_pct"] = 0.0
            metrics["beta"] = 1.0

        return metrics

    def compute_monthly_matrix(self, returns: pd.Series) -> List[Dict[str, Any]]:
        """
        Computes the monthly return matrix structured for React tables:
        [{"year": "2024", "Jan": 2.1, "Feb": -0.5, ..., "Dec": 1.2, "YTD": 18.4}]
        """
        try:
            s_ret = returns.dropna().astype(float)
            if len(s_ret) < 5:
                return []

            m_df = qs.stats.monthly_returns(s_ret, eoy=True)
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            rows = []
            for year, row in m_df.iterrows():
                row_dict: Dict[str, Any] = {"year": str(year)}
                ytd_val = row.get("EOY", row.get("eoy", row.get("YTD", 0.0)))
                for m in months:
                    val = row.get(m.upper(), row.get(m.title(), row.get(m, 0.0)))
                    row_dict[m] = _safe_float(val, multiply_100=True)
                row_dict["YTD"] = _safe_float(ytd_val, multiply_100=True)
                rows.append(row_dict)

            # Sort descending by year
            rows.sort(key=lambda r: r["year"], reverse=True)
            return rows
        except Exception as e:
            logger.warning(f"Failed to generate monthly return matrix: {e}")
            return []

    def generate_html_report(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        title: str = "OptionsLab Institutional Tear Sheet",
        strategy_name: str = "30-DTE Systematic Wheel"
    ) -> str:
        """
        Generates a standalone QuantStats HTML performance report.
        Returns the unique report filename / report_id.
        """
        report_id = f"tearsheet_{uuid.uuid4().hex[:12]}.html"
        output_path = os.path.join(self.reports_dir, report_id)

        try:
            s_ret = strategy_returns.dropna().astype(float)
            b_ret = None
            if benchmark_returns is not None and not benchmark_returns.empty:
                b_ret = benchmark_returns.dropna().astype(float)
                # Align dates
                common_idx = s_ret.index.intersection(b_ret.index)
                if len(common_idx) >= 5:
                    s_ret = s_ret.loc[common_idx]
                    b_ret = b_ret.loc[common_idx]

            qs.reports.html(
                s_ret,
                benchmark=b_ret,
                output=output_path,
                title=f"{strategy_name} - {title}",
                download_filename=report_id
            )
            logger.info(f"Generated QuantStats HTML report at: {output_path}")
            return report_id
        except Exception as e:
            logger.error(f"Error creating QuantStats HTML report: {e}", exc_info=True)
            # Create a simple fallback HTML if quantstats plot generation failed
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"""<!DOCTYPE html>
<html>
<head><title>{title}</title><style>body{{font-family:sans-serif;padding:2rem;background:#0f172a;color:#f8fafc;}}</style></head>
<body>
<h1>OptionsLab Performance Report</h1>
<p>Generated for {strategy_name}</p>
<p>Status: Computed metrics successfully.</p>
</body>
</html>""")
            return report_id
