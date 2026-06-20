"""
drive_sync.py — Google Drive / Sheets sync for Portfolio CSVs.

Authenticates using Application Default Credentials (the Cloud Run
service account), which means the user just needs to share their Google
Sheets with the service account email address.

Usage:
  1. User shares their portfolio Google Sheets with the SA email.
  2. User provides the Google Sheet IDs (or we auto-discover from Drive).
  3. This module fetches each sheet, parses the Yahoo Finance CSV format,
     and returns a list of ticker dicts.
"""

import csv
import io
import logging
from typing import List, Dict, Any, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth

logger = logging.getLogger(__name__)

# Yahoo Finance CSV columns (from Alpha Finance export):
# Symbol, Current Price, Date, Time, Change, Open, High, Low, Volume, ...
REQUIRED_COLUMNS = {"Symbol", "Current Price"}


def _get_drive_service():
    """Build a Google Drive v3 API service using ADC."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_sheets_service():
    """Build a Google Sheets v4 API service using ADC."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def discover_portfolio_sheets(query: str = "portfolio") -> List[Dict[str, str]]:
    """
    Search Google Drive for spreadsheets matching a query string.
    Returns a list of {id, name, modifiedTime} dicts.
    """
    try:
        drive = _get_drive_service()
        results = drive.files().list(
            q=f"name contains '{query}' and mimeType='application/vnd.google-apps.spreadsheet'",
            spaces="drive",
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=20
        ).execute()
        files = results.get("files", [])
        logger.info(f"Discovered {len(files)} portfolio sheets from Drive")
        return files
    except Exception as e:
        logger.error(f"Drive discovery failed: {e}")
        return []


def fetch_sheet_as_csv(spreadsheet_id: str, sheet_name: str = "Sheet1") -> str:
    """
    Fetch a Google Sheet tab as raw CSV text using the Sheets API.
    """
    sheets = _get_sheets_service()
    try:
        result = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to fetch range '{sheet_name}', trying fallback 'A:Z': {e}")
        try:
            result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="A:Z"
            ).execute()
        except Exception as ex:
            logger.error(f"Failed to fetch sheet even with fallback: {ex}")
            return ""

    rows = result.get("values", [])
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def parse_portfolio_csv(csv_text: str) -> List[Dict[str, Any]]:
    """
    Parse a Google Sheet / CSV export into a list of ticker dicts.
    Supports case-insensitive column headers and synonyms.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    tickers = []
    
    for row in reader:
        # Normalize keys to lowercase for flexible matching
        norm_row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        
        # Try to find symbol
        symbol = None
        for sym_key in ["symbol", "ticker", "symbol/ticker", "ticker symbol"]:
            if sym_key in norm_row and norm_row[sym_key]:
                symbol = str(norm_row[sym_key]).strip().upper()
                break
        
        if not symbol:
            continue
            
        def safe_float(val):
            if val is None:
                return None
            try:
                return float(str(val).replace(",", "").replace("$", "").replace("%", "").strip())
            except (ValueError, TypeError):
                return None

        def safe_int(val):
            if val is None:
                return None
            try:
                return int(float(str(val).replace(",", "").strip()))
            except (ValueError, TypeError):
                return None

        # Try to find price
        price = None
        for price_key in ["current price", "price", "last sale", "value", "close", "last"]:
            if price_key in norm_row:
                price = safe_float(norm_row[price_key])
                if price is not None:
                    break

        # Try to find change
        change = None
        for change_key in ["change", "change%", "% change", "pctchange", "chg", "chg%"]:
            if change_key in norm_row:
                change = safe_float(norm_row[change_key])
                if change is not None:
                    break

        # Try to find high
        high = None
        for high_key in ["high", "max"]:
            if high_key in norm_row:
                high = safe_float(norm_row[high_key])
                if high is not None:
                    break

        # Try to find low
        low = None
        for low_key in ["low", "min"]:
            if low_key in norm_row:
                low = safe_float(norm_row[low_key])
                if low is not None:
                    break

        # Try to find volume
        volume = None
        for vol_key in ["volume", "vol"]:
            if vol_key in norm_row:
                volume = safe_int(norm_row[vol_key])
                if volume is not None:
                    break

        tickers.append({
            "symbol": symbol,
            "name": None,
            "current_price": price if price is not None else 0.0,
            "change": change if change is not None else 0.0,
            "high": high if high is not None else price,
            "low": low if low is not None else price,
            "volume": volume if volume is not None else 0,
        })

    logger.info(f"Parsed {len(tickers)} tickers from CSV")
    return tickers


def sync_portfolio_from_sheet(
    spreadsheet_id: str,
    sheet_name: str = "Sheet1"
) -> List[Dict[str, Any]]:
    """
    End-to-end: fetch a Google Sheet and return parsed tickers.
    """
    csv_text = fetch_sheet_as_csv(spreadsheet_id, sheet_name)
    if not csv_text:
        logger.warning(f"Sheet {spreadsheet_id}/{sheet_name} returned no data")
        return []
    return parse_portfolio_csv(csv_text)


def sync_all_portfolios_from_drive(
    query: str = "portfolio"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Discover all portfolio sheets from Drive, fetch each one,
    and return a dict of {sheet_name: [tickers]}.
    """
    sheets = discover_portfolio_sheets(query)
    results = {}

    for sheet_info in sheets:
        sheet_id = sheet_info["id"]
        sheet_name = sheet_info["name"]
        try:
            tickers = sync_portfolio_from_sheet(sheet_id)
            if tickers:
                results[sheet_name] = {
                    "sheet_id": sheet_id,
                    "tickers": tickers
                }
        except Exception as e:
            logger.error(f"Failed to sync sheet '{sheet_name}' ({sheet_id}): {e}")

    return results
