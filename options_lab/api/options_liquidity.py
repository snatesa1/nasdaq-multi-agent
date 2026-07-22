import logging
from typing import Tuple
import yfinance as yf

logger = logging.getLogger(__name__)

def check_options_liquidity(symbol: str, min_open_interest: int = 5000) -> Tuple[bool, int]:
    """
    Get the option chain for the nearest expiration date and sum the open interest.
    Returns (is_liquid, total_open_interest).
    """
    symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(symbol)
        options_dates = ticker.options
        if not options_dates:
            logger.info(f"Options Liquidity Check: {symbol} has NO traded options.")
            return False, 0
            
        # Get nearest expiration date
        nearest_date = options_dates[0]
        opt_chain = ticker.option_chain(nearest_date)
        
        # Sum open interest
        call_oi = 0
        put_oi = 0
        
        if not opt_chain.calls.empty and "openInterest" in opt_chain.calls.columns:
            call_oi = opt_chain.calls["openInterest"].fillna(0).sum()
            
        if not opt_chain.puts.empty and "openInterest" in opt_chain.puts.columns:
            put_oi = opt_chain.puts["openInterest"].fillna(0).sum()
            
        total_oi = int(call_oi + put_oi)
        is_liquid = total_oi >= min_open_interest
        
        logger.info(f"Options Liquidity Check: {symbol} total open interest on {nearest_date} is {total_oi} (Min threshold: {min_open_interest}). Liquid={is_liquid}")
        return is_liquid, total_oi
        
    except Exception as e:
        logger.error(f"Error checking options liquidity for {symbol}: {e}")
        return False, 0
