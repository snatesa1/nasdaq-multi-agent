import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import yfinance as yf

from .base_agent import BaseAgent, AgentResult
from ..earnings_calendar import fetch_historical_earnings_dates

logger = logging.getLogger(__name__)

class EarningsVolAgent(BaseAgent):
    """
    Earnings Volatility Agent.
    Calculates historical daily volatility patterns and return magnitudes
    around past 4 earnings dates across specific windows.
    """

    @property
    def name(self) -> str:
        return "EarningsVolAgent"

    async def analyze(self, symbol: str, **kwargs) -> AgentResult:
        """
        Run volatility analysis on a symbol around its past 4 earnings dates.
        Returns volatility matrix and composite score.
        """
        symbol = symbol.strip().upper()
        logger.info(f"📊 EarningsVolAgent: Analyzing historical earnings volatility for {symbol}...")

        try:
            # 1. Fetch past earnings dates
            past_dates = fetch_historical_earnings_dates(symbol)
            if not past_dates:
                return AgentResult(
                    agent_name=self.name,
                    score=0.5,
                    confidence=0.2,
                    rationale=f"No historical earnings dates found for {symbol}.",
                    data={"symbol": symbol, "quarters": []}
                )

            logger.info(f"Found {len(past_dates)} historical earnings dates for {symbol}: {past_dates}")

            # 2. Get 1.5 years of price history to cover all past earnings windows
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=500)
            df_prices = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

            if df_prices.empty or len(df_prices) < 20:
                return AgentResult(
                    agent_name=self.name,
                    score=0.5,
                    confidence=0.2,
                    rationale=f"Insufficient price history for {symbol}.",
                    data={"symbol": symbol, "quarters": []}
                )

            # Ensure index is datetime-naive for matching
            df_prices.index = df_prices.index.tz_localize(None)
            
            quarters_data = []
            vol_5d_before_list = []
            move_1d_before_list = []
            move_1d_after_list = []
            abs_move_1d_after_list = []

            # 3. Process each earnings date
            for idx, earn_date in enumerate(past_dates):
                # We need to find the trading day index for earn_date in df_prices
                # Find the closest trading day that is >= earn_date
                trading_days = df_prices.index
                
                # Check if earn_date falls within trading range
                if earn_date < trading_days[0] or earn_date > trading_days[-1]:
                    logger.warning(f"Earnings date {earn_date} is out of trading range.")
                    continue
                    
                # Find index of the trading day on or right after earn_date
                pos_list = np.where(trading_days >= earn_date)[0]
                if len(pos_list) == 0:
                    continue
                t0_idx = pos_list[0]
                
                # We need windows:
                # Pre-earnings window (T-5 to T-1): index range [t0_idx-5, t0_idx-1]
                # Pre-earnings day (T-1): index [t0_idx-1]
                # Post-earnings day (T+1): index [t0_idx+1]
                # Ensure we have enough indexes
                if t0_idx < 6 or t0_idx >= len(trading_days) - 1:
                    logger.warning(f"Insufficient window indexes around earnings date {earn_date} (t0_idx={t0_idx}).")
                    continue
                
                # Extract Close prices
                t5_to_t1_prices = df_prices["Close"].iloc[t0_idx-6 : t0_idx].values # 6 prices to get 5 returns
                t1_close = float(df_prices["Close"].iloc[t0_idx-1])
                t2_close = float(df_prices["Close"].iloc[t0_idx-2])
                t1_after_close = float(df_prices["Close"].iloc[t0_idx+1])
                t0_close = float(df_prices["Close"].iloc[t0_idx])
                
                # Calculate returns
                # Pre-earnings 5d returns:
                returns_5d = np.log(t5_to_t1_prices[1:] / t5_to_t1_prices[:-1])
                vol_5d_before = float(np.std(returns_5d) * np.sqrt(252))
                
                # Pre-earnings day return (T-1 Close vs T-2 Close)
                move_1d_before = float(((t1_close - t2_close) / t2_close) * 100)
                
                # Post-earnings reaction: Close on T+1 vs Close on T-1 (the day before earnings release)
                move_1d_after = float(((t1_after_close - t1_close) / t1_close) * 100)
                
                # We also track T_0 vs T-1 in case earnings was BMO
                # Let's save both for detailed matrix
                quarter_label = f"Q{4 - (idx % 4)} '{earn_date.strftime('%y')}"
                
                quarters_data.append({
                    "quarter": quarter_label,
                    "earnings_date": earn_date.strftime("%Y-%m-%d"),
                    "vol_5d_before_pct": round(vol_5d_before * 100, 1),
                    "move_t_minus_1_pct": round(move_1d_before, 2),
                    "move_t_plus_1_pct": round(move_1d_after, 2),
                    "abs_move_t_plus_1_pct": round(abs(move_1d_after), 2)
                })
                
                vol_5d_before_list.append(vol_5d_before)
                move_1d_before_list.append(move_1d_before)
                move_1d_after_list.append(move_1d_after)
                abs_move_1d_after_list.append(abs(move_1d_after))

            if not quarters_data:
                return AgentResult(
                    agent_name=self.name,
                    score=0.5,
                    confidence=0.2,
                    rationale=f"Could not compute volatility windows for {symbol}.",
                    data={"symbol": symbol, "quarters": []}
                )

            # 4. Calculate Averages
            avg_vol_5d_before = float(np.mean(vol_5d_before_list))
            avg_move_1d_before = float(np.mean([abs(x) for x in move_1d_before_list]))
            avg_move_1d_after = float(np.mean(abs_move_1d_after_list))
            
            # 5. Composite Scoring
            # Score logic: we want high post-earnings move (higher option strategy yield)
            # A stock with avg reaction > 8% is very attractive (score near 1.0)
            # A stock with avg reaction < 2% has low volatility (score near 0.2)
            vol_score = min(1.0, avg_move_1d_after / 10.0) # 10% move = max score
            
            # Combine with optional 52-week low context if provided
            pct_above_low = kwargs.get("pct_above_low", 15.0)
            # Closer to 52W low = higher score
            value_score = max(0.0, 1.0 - (pct_above_low / 30.0)) # 0% above low = 1.0, 30% above low = 0.0
            
            composite_score = 0.6 * vol_score + 0.4 * value_score
            
            rationale = (
                f"Historical earnings moves for {symbol} average ±{avg_move_1d_after:.1f}% on earnings release. "
                f"Pre-earnings annualized volatility averages {avg_vol_5d_before*100:.1f}%. "
                f"Stock is currently {pct_above_low:.1f}% above its 52-week low, representing a high-potential value play."
            )

            return AgentResult(
                agent_name=self.name,
                score=round(composite_score, 3),
                confidence=0.8,
                rationale=rationale,
                data={
                    "symbol": symbol,
                    "avg_vol_5d_before_pct": round(avg_vol_5d_before * 100, 1),
                    "avg_move_t_minus_1_pct": round(avg_move_1d_before, 2),
                    "avg_move_t_plus_1_pct": round(avg_move_1d_after, 2),
                    "quarters": quarters_data
                }
            )

        except Exception as e:
            logger.error(f"EarningsVolAgent failed for {symbol}: {e}")
            return AgentResult(
                agent_name=self.name,
                score=0.5,
                confidence=0.2,
                rationale=f"Volatility analysis failed: {e}",
                data={"symbol": symbol, "error": str(e)}
            )
