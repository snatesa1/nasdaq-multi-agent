import os
import sys
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.auth

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.data_client import NasdaqScreenerClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def get_google_service(service_name, version):
    """Authenticate and return the Google API service client."""
    creds = None
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")
    client_secret_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client_secret.json")
    
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            pass
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        else:
            try:
                creds, _ = google.auth.default(scopes=SCOPES)
            except Exception:
                creds = None
                
    if not creds or not creds.valid:
        if os.path.exists(client_secret_path):
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
        else:
            raise Exception("No Google API credentials found (missing client_secret.json / token.json and ADC).")
            
    return build(service_name, version, credentials=creds)

def select_tickers():
    """Calculate beta and select 20 high market cap, 20 high beta, and 20 low beta tickers."""
    screener = NasdaqScreenerClient()
    df_universe = screener.load_data()
    if df_universe.empty:
        raise Exception("Failed to load Nasdaq screener data")
        
    df = df_universe.copy()
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce").fillna(0)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    
    df = df[df["symbol"].astype(str).str.len() <= 4]
    df = df[df["symbol"].astype(str).str.isalpha()]
    
    # Filter candidates to large liquid stocks
    candidates = df[(df["marketCap"] > 1000000000) & (df["volume"] > 100000)].copy()
    candidate_symbols = candidates["symbol"].tolist()
    
    logger.info(f"Downloading 1-year daily prices for {len(candidate_symbols)} candidates to calculate beta...")
    # Fetch 1 year of daily close data in a single batch
    data = yf.download(candidate_symbols + ["SPY"], period="1y", interval="1d", progress=False)
    if data.empty:
        raise Exception("Failed to download price data for beta calculations")
        
    close_prices = data["Close"] if "Close" in data.columns else data
    returns = close_prices.pct_change().dropna()
    
    spy_var = returns["SPY"].var()
    betas = {}
    for sym in candidate_symbols:
        if sym in returns.columns and sym != "SPY":
            cov = returns[sym].cov(returns["SPY"])
            betas[sym] = cov / spy_var if spy_var > 0 else 1.0
            
    candidates["beta"] = candidates["symbol"].map(betas)
    candidates = candidates.dropna(subset=["beta"])
    
    # 1. Top 20 Market Cap
    top_mcap = candidates.sort_values(by="marketCap", ascending=False).head(20)["symbol"].tolist()
    
    # 2. Top 20 High Beta
    top_beta = candidates.sort_values(by="beta", ascending=False).head(20)["symbol"].tolist()
    
    # 3. Top 20 Low Beta (excluding negative or near-zero outliers)
    low_beta = candidates[candidates["beta"] > 0.05].sort_values(by="beta", ascending=True).head(20)["symbol"].tolist()
    
    selected = list(set(top_mcap + top_beta + low_beta))
    logger.info(f"Selected {len(selected)} unique tickers: {selected}")
    return selected

def create_and_populate_sheet(tickers):
    """Create a Google Sheet and populate it with GOOGLEFINANCE formulas."""
    sheets_service = get_google_service("sheets", "v4")
    drive_service = get_google_service("drive", "v3")
    
    # Create new Spreadsheet
    spreadsheet_body = {
        'properties': {
            'title': 'NASDAQ 10-Year Market Data Cache'
        }
    }
    spreadsheet = sheets_service.spreadsheets().create(
        body=spreadsheet_body,
        fields='spreadsheetId'
    ).execute()
    
    spreadsheet_id = spreadsheet.get('spreadsheetId')
    logger.info(f"Created spreadsheet ID: {spreadsheet_id}")
    
    # Make the Spreadsheet readable to anyone with the link
    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body={
            'role': 'reader',
            'type': 'anyone'
        }
    ).execute()
    logger.info("Shared spreadsheet publicly (read-only link format).")
    
    # Prepare formulas: column index is 1-based (A, B, C, etc.)
    # AAPL Date, AAPL Price, MSFT Date, MSFT Price...
    # `=GOOGLEFINANCE(TICKER, "price", start_date, end_date, "DAILY")`
    # We will write the formulas to row 1 of the sheet dynamically
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y-%m-%d")
    
    values = [[]]
    for ticker in tickers:
        values[0].append(ticker) # Title/Header
        values[0].append("") # Spacer
        
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()
    
    formula_values = [[]]
    for ticker in tickers:
        # GOOGLEFINANCE formula
        formula_values[0].append(f'=GOOGLEFINANCE("{ticker}", "price", DATE({start_date[:4]},{start_date[5:7]},{start_date[8:10]}), DATE({end_date[:4]},{end_date[5:7]},{end_date[8:10]}), "DAILY")')
        formula_values[0].append("")
        
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A2",
        valueInputOption="USER_ENTERED",
        body={"values": formula_values}
    ).execute()
    
    # Save the spreadsheet ID config file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_data_config.json")
    with open(config_path, "w") as f:
        json.dump({"spreadsheet_id": spreadsheet_id}, f)
        
    logger.info(f"Google Sheet populated successfully. Spreadsheet ID saved to {config_path}")
    print(f"Spreadsheet URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

if __name__ == "__main__":
    try:
        tickers = select_tickers()
        create_and_populate_sheet(tickers)
    except Exception as e:
        logger.error(f"Failed to build market data sheet: {e}", exc_info=True)
