import logging
from typing import Dict, Any, List, Optional
from .campaign_stitcher import CampaignStitcher
from .trade_history_ingest import TradeHistoryIngestEngine

logger = logging.getLogger("behavioral-forensics")


class BehavioralForensicsEngine:
    """
    Trader Psychology, Discipline Forensics & Bias Diagnostic Engine.
    
    Identifies quantitative behavioral flaws from historical execution data:
    1. Short Call Drag on Momentum Stocks (PANW / AMZN capped alpha).
    2. Disposition Effect & Bag-Holding (PLUG -82.7% without mitigation).
    3. Systematic Strike & DTE Adherence (Visa & IBM 95%+ win rate).
    4. Concentration Risk & Leverage Drift.
    """

    def __init__(self, campaign_stitcher: Optional[CampaignStitcher] = None):
        self.stitcher = campaign_stitcher or CampaignStitcher()

    def generate_behavioral_audit(self, report_id: Optional[str] = None) -> Dict[str, Any]:
        """Performs full forensic audit across all campaigns and trades."""
        campaigns = self.stitcher.reconstruct_all_campaigns(report_id)
        
        total_pnl = sum(c["total_pnl"] for c in campaigns)
        total_stock_pnl = sum(c["stock_pnl"] for c in campaigns)
        total_option_pnl = sum(c["option_pnl"] for c in campaigns)

        # Count wins vs losses in options
        all_option_legs = []
        for c in campaigns:
            all_option_legs.extend(c.get("options_legs", []))

        opt_wins = [o for o in all_option_legs if o.get("pnl", 0) >= 0]
        opt_losses = [o for o in all_option_legs if o.get("pnl", 0) < 0]
        total_opt_trades = len(all_option_legs)
        opt_win_rate = (len(opt_wins) / total_opt_trades * 100.0) if total_opt_trades > 0 else 0.0

        # Calculate specific behavioral metrics
        # 1. Option Volatility Drag (Losses on calls of winning stocks)
        high_drag_losses = abs(sum(c["option_pnl"] for c in campaigns if c["stock_pnl"] > 500 and c["option_pnl"] < 0))
        drag_tickers = [c["ticker"] for c in campaigns if c["stock_pnl"] > 500 and c["option_pnl"] < 0]
        
        # 2. Bag-Holding Score (Unrealized stock losses held without options hedge)
        baghold_amount = abs(sum(c["stock_pnl"] for c in campaigns if c["stock_pnl"] < -200 and c["option_pnl"] <= 0))
        baghold_tickers = [c["ticker"] for c in campaigns if c["stock_pnl"] < -200 and c["option_pnl"] <= 0]
        
        # 3. Systematic Discipline Score (Consistent option income harvesting)
        systematic_gains = sum(c["option_pnl"] for c in campaigns if c["option_pnl"] > 0)
        systematic_tickers = [c["ticker"] for c in campaigns if c["option_pnl"] > 0]

        # Composite Discipline Score (0 to 100)
        # Base: 75. Bonus for systematic win rate (+15), Penalty for call drag (-12), Penalty for bagholds (-8)
        discipline_score = max(20, min(95, round(70 + (opt_win_rate * 0.15) + (systematic_gains / 300.0) - (high_drag_losses / 400.0) - (baghold_amount / 300.0))))

        # Behavioral Diagnoses
        diagnoses = [
            {
                "id": "BIAS_CALL_DRAG",
                "name": "Aggressive Short Call Drag on Momentum Stocks",
                "severity": "CRITICAL" if high_drag_losses > 1000 else "MEDIUM",
                "impact": f"-${high_drag_losses:,.2f} Lost Alpha",
                "description": f"Selling tight OTM/ITM calls on explosive growth stocks ({', '.join(drag_tickers) if drag_tickers else 'High-Beta'}) caps upside during bullish surges.",
                "remedy": "Enforce Delta ≤ 0.15 on high-beta growth stocks or switch to ratio collars."
            },
            {
                "id": "BIAS_BAGHOLDING",
                "name": "Unhedged Bag-Holding on Distressed Equities",
                "severity": "HIGH" if baghold_amount > 1000 else "LOW",
                "impact": f"-${baghold_amount:,.2f} Unrealized Loss",
                "description": f"Holding declining non-earning stocks ({', '.join(baghold_tickers) if baghold_tickers else 'Equities'}) indefinitely without executing mechanical stop-losses or selling low-delta covered calls.",
                "remedy": "Automate 15% stop-loss threshold or mandate 5-Pillar Conviction screening prior to equity entry."
            },
            {
                "id": "STRENGTH_SYSTEMATIC_INCOME",
                "name": "Flawless Systematic Covered Calls & Cash-Secured Puts",
                "severity": "STRENGTH",
                "impact": f"+${systematic_gains:,.2f} Realized Theta Yield",
                "description": f"Disciplined OTM strike selection and high-probability decay on blue-chip staples ({', '.join(systematic_tickers[:4]) if systematic_tickers else 'Watchlist'}).",
                "remedy": "Replicate this exact systematic Wheel blueprint into the automated Saxo engine."
            }
        ]

        # Actionable Rulebook for Safety Shield
        rulebook = [
            {"rule_id": "RULE_1", "name": "Momentum Call Cap Guard", "condition": "Beta > 1.3 OR RSI > 65", "action": "Max Delta ≤ 0.15 for Covered Calls", "status": "ACTIVE"},
            {"rule_id": "RULE_2", "name": "Mechanical Stop Loss", "condition": "Position Drawdown > 15%", "action": "Trigger Mandatory Review / Exit Alert", "status": "ACTIVE"},
            {"rule_id": "RULE_3", "name": "50% Profit Rule & 21-DTE Roll", "condition": "Option Profit ≥ 50% OR DTE ≤ 21", "action": "Auto-Close / Roll to next monthly cycle", "status": "ACTIVE"},
            {"rule_id": "RULE_4", "name": "Revenge Trading Cooldown", "condition": "Loss > $1,000 within 24h", "action": "Enforce 24-Hour Capital Lockout", "status": "ACTIVE"}
        ]

        return {
            "discipline_score": discipline_score,
            "grade": "B+" if discipline_score >= 80 else ("B" if discipline_score >= 70 else "C+"),
            "total_pnl": round(total_pnl, 2),
            "stock_pnl": round(total_stock_pnl, 2),
            "option_pnl": round(total_option_pnl, 2),
            "options_win_rate": round(opt_win_rate, 1),
            "total_options_trades": total_opt_trades,
            "winning_options_trades": len(opt_wins),
            "losing_options_trades": len(opt_losses),
            "diagnoses": diagnoses,
            "rulebook": rulebook,
            "campaigns_summary": campaigns
        }
