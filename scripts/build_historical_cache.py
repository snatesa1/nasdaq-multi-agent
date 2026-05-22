import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.data_client import NasdaqScreenerClient, AlpacaOHLCVClient
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_cache():
    screener = NasdaqScreenerClient()
    alpaca = AlpacaOHLCVClient()
    
    df_universe = screener.load_data()
    if df_universe.empty:
        logger.error("Failed to load screener data")
        return
        
    sectors = df_universe["sector"].dropna().unique().tolist()
    sectors = [s.strip() for s in sectors if s.strip()]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2520) # 10 years of trading days approx
    
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical_cache.parquet")
    
    all_data = []
    
    for sector in sectors:
        logger.info(f"Processing sector: {sector}")
        df_sec = df_universe[df_universe["sector"] == sector].dropna(subset=["symbol"])
        df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != '']
        df_sec = df_sec[df_sec["symbol"].astype(str).str.strip() != 'nan']
        
        df_sec["volume"] = pd.to_numeric(df_sec["volume"], errors="coerce").fillna(0)
        df_sec["marketCap"] = pd.to_numeric(df_sec["marketCap"], errors="coerce").fillna(0)
        df_sec = df_sec[df_sec["symbol"].astype(str).str.len() <= 4]
        df_sec = df_sec[df_sec["symbol"].astype(str).str.isalpha()]
        df_sec = df_sec[df_sec["volume"] > 10000]
        df_sec = df_sec[df_sec["marketCap"] > 50000000]
        
        if "pctchange" in df_sec.columns:
            df_sec["pctchange"] = df_sec["pctchange"].astype(str).str.replace("%", "").str.replace("$", "")
            df_sec["pctchange"] = pd.to_numeric(df_sec["pctchange"], errors="coerce")
            df_sec = df_sec.dropna(subset=["pctchange"])
            
            # Select top 10 momentum stocks, prioritizing > 10%
            df_momentum = df_sec[df_sec["pctchange"] > 10.0]
            if len(df_momentum) >= 10:
                df_sec = df_momentum.sort_values(by="pctchange", ascending=False)
            else:
                df_sec = df_sec.sort_values(by="pctchange", ascending=False)
                
        symbols = df_sec["symbol"].tolist()[:10]
        logger.info(f"Selected top 10 momentum symbols for {sector}: {symbols}")
        
        if not symbols:
            continue
            
        try:
            # We fetch using the batch fallback logic (10 years)
            df_prices = alpaca.get_historical_batch(symbols, start_date, end_date)
            if not df_prices.empty and 'close' in df_prices.columns:
                if isinstance(df_prices.index, pd.MultiIndex):
                    df_close = df_prices['close'].unstack(level='symbol')
                else:
                    df_close = df_prices[['close']]
                    df_close.columns = [symbols[0]]
                    
                # Calculate daily price-weighted average index for the sector
                daily_index = df_close.mean(axis=1)
                df_sector_series = daily_index.to_frame(name=sector)
                all_data.append(df_sector_series)
        except Exception as e:
            logger.error(f"Failed to fetch historical batch for {sector}: {e}")
            
    if all_data:
        df_cache = pd.concat(all_data, axis=1)
        df_cache.index.name = "timestamp"
        df_cache.to_parquet(cache_path)
        logger.info(f"Successfully built historical cache with {len(df_cache)} rows and {len(df_cache.columns)} columns at {cache_path}")
    else:
        logger.warning("No data retrieved for cache.")

if __name__ == "__main__":
    build_cache()
