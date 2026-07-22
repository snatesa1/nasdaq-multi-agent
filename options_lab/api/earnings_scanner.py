import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from .earnings_calendar import get_upcoming_earnings_calendar
from .universe import get_combined_universe, screen_52w_low, check_fundamental_quality
from .options_liquidity import check_options_liquidity
from .agents.earnings_vol_agent import EarningsVolAgent

logger = logging.getLogger(__name__)

async def run_earnings_scan(
    low_threshold_pct: float = 0.20,
    min_open_interest: int = 5000
) -> Dict[str, Any]:
    """
    Runs the multi-stage investor funnel to find upcoming earnings plays:
    1. Fetch next-week earners.
    2. Filter to S&P 500 + NASDAQ universe.
    3. Filter for stocks near 52-week low range (run concurrently).
    4. Filter for high fundamental quality (run concurrently).
    5. Filter for liquid options chains (run concurrently).
    6. Compute historical earnings volatility matrix.
    """
    logger.info("🚀 Starting multi-stage Earnings Volatility Scan...")
    
    # --- Step 1: Calendar & Universe Filter ---
    raw_calendar = get_upcoming_earnings_calendar()
    if not raw_calendar:
        logger.warning("No upcoming earnings calendar entries found.")
        return {"candidates": []}
        
    combined_universe = get_combined_universe()
    logger.info(f"Loaded combined universe with {len(combined_universe)} symbols.")

    universe_earners = []
    for entry in raw_calendar:
        sym = entry["symbol"].strip().upper()
        if sym in combined_universe:
            # Create a copy to prevent mutation issues
            universe_earners.append(dict(entry))
            
    logger.info(f"Filtered upcoming earners to universe: {len(universe_earners)} / {len(raw_calendar)} symbols.")
    if not universe_earners:
        return {"candidates": []}

    # --- Step 2: 52-Week Low Screen (Concurrent) ---
    value_candidates = []
    logger.info(f"Concurrently screening {len(universe_earners)} earners for proximity to 52-week lows...")
    
    def run_52w_check(entry):
        sym = entry["symbol"]
        try:
            res = screen_52w_low(sym, low_threshold_pct)
            if res.get("pass"):
                # Enrich entry with 52W low details
                entry.update({
                    "current_price": res["current_price"],
                    "low_52w": res["low_52w"],
                    "high_52w": res["high_52w"],
                    "pct_above_low": res["pct_above_low"]
                })
                return entry
        except Exception as e:
            logger.error(f"Error in 52W check for {sym}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(run_52w_check, universe_earners)
        for res in results:
            if res is not None:
                value_candidates.append(res)
            
    logger.info(f"Screened for 52W low: {len(value_candidates)} candidates.")
    if not value_candidates:
        return {"candidates": []}

    # --- Step 3: Exhaustive Fundamental Filter (Concurrent) ---
    quality_candidates = []
    logger.info(f"Concurrently screening {len(value_candidates)} candidates for fundamental quality...")
    
    def run_fundamental_check(entry):
        sym = entry["symbol"]
        try:
            res = check_fundamental_quality(sym)
            if res.get("pass"):
                entry.update({
                    "fundamental_metrics": res["metrics"],
                    "pass_ratio": res.get("pass_ratio")
                })
                return entry
        except Exception as e:
            logger.error(f"Error in fundamental check for {sym}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(run_fundamental_check, value_candidates)
        for res in results:
            if res is not None:
                quality_candidates.append(res)
            
    logger.info(f"Screened for fundamental quality: {len(quality_candidates)} candidates.")
    if not quality_candidates:
        return {"candidates": []}

    # --- Step 4: Options Open Interest (Liquidity) (Concurrent) ---
    liquid_candidates = []
    logger.info(f"Concurrently screening {len(quality_candidates)} candidates for option open interest...")
    
    def run_liquidity_check(entry):
        sym = entry["symbol"]
        try:
            is_liquid, total_oi = check_options_liquidity(sym, min_open_interest)
            if is_liquid:
                entry.update({
                    "options_open_interest": total_oi
                })
                return entry
        except Exception as e:
            logger.error(f"Error in options check for {sym}: {e}")
        return None

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(run_liquidity_check, quality_candidates)
        for res in results:
            if res is not None:
                liquid_candidates.append(res)
            
    logger.info(f"Screened for option liquidity: {len(liquid_candidates)} candidates.")
    if not liquid_candidates:
        return {"candidates": []}

    # --- Step 5: Volatility Agent Matrix Calculation ---
    vol_agent = EarningsVolAgent()
    final_plays = []
    
    logger.info(f"Running EarningsVolAgent for final {len(liquid_candidates)} plays...")
    
    for entry in liquid_candidates:
        sym = entry["symbol"]
        agent_res = await vol_agent.analyze(sym, pct_above_low=entry["pct_above_low"])
        if agent_res.score is not None:
            entry.update({
                "score": agent_res.score,
                "rationale": agent_res.rationale,
                "volatility_metrics": agent_res.data
            })
            final_plays.append(entry)

    # Rank plays: Sort by score descending (score balances volatility move + deep value proximity)
    final_plays.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    
    logger.info(f"Finished scan. Found {len(final_plays)} high-quality earnings plays.")
    return {
        "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_earners_scraped": len(raw_calendar),
        "universe_earners": len(universe_earners),
        "passed_52w_low": len(value_candidates),
        "passed_fundamentals": len(quality_candidates),
        "passed_liquidity": len(liquid_candidates),
        "plays": final_plays
    }
