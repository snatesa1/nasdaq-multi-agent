"""
drive_sync.py — Google Drive / Sheets sync for Portfolio CSVs.

Supports:
1. Public / Shared URL Direct CSV Export
2. OAuth 2.0 User Token auto-discovery (from token.json)
3. Application Default Credentials (ADC) fallback
4. Automatic URL / ID sanitization and extraction
5. Flexible CSV column mapping for Yahoo Finance / Google Finance / custom portfolio exports
"""

import csv
import io
import re
import os
import logging
from typing import List, Dict, Any, Optional

import requests
from googleapiclient.discovery import build
import google.auth
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


def extract_spreadsheet_id(input_str: str) -> str:
    """Extracts spreadsheet ID from a full Google Sheets URL or returns cleaned ID."""
    if not input_str:
        return ""
    clean = input_str.strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", clean)
    if match:
        return match.group(1)
    match_d = re.search(r"/d/([a-zA-Z0-9-_]+)", clean)
    if match_d:
        return match_d.group(1)
    # Strip any query parameters if passed
    if "/" not in clean and "?" in clean:
        clean = clean.split("?")[0]
    return clean


def _get_credentials():
    """Loads Google API credentials, prioritizing local token.json over ADC fallback."""
    search_dirs = [
        os.getenv("WORKSPACE_ROOT", ""),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        os.getcwd()
    ]

    for d in search_dirs:
        token_path = os.path.join(d, "token.json")
        if os.path.exists(token_path):
            try:
                # Load without specifying scopes so it uses the token's granted scopes
                creds = Credentials.from_authorized_user_file(token_path)
                if creds:
                    if not creds.valid and creds.expired and creds.refresh_token:
                        logger.info(f"Refreshing expired Google OAuth credentials from {token_path}")
                        creds.refresh(Request())
                        with open(token_path, "w", encoding="utf-8") as f:
                            f.write(creds.to_json())
                    if creds.valid:
                        logger.info(f"Loaded valid Google OAuth credentials from {token_path}")
                        return creds
            except Exception as e:
                logger.warning(f"Failed to load/refresh credentials from {token_path}: {e}")

    # Fallback to Application Default Credentials (ADC)
    try:
        logger.info("Falling back to Application Default Credentials (ADC) for Google services.")
        creds, _ = google.auth.default(scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ])
        return creds
    except Exception as e:
        logger.warning(f"ADC fallback unavailable: {e}")
        return None


def _get_drive_service():
    """Build a Google Drive v3 API service using dynamic credentials."""
    creds = _get_credentials()
    if not creds:
        return None
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_sheets_service():
    """Build a Google Sheets v4 API service using dynamic credentials."""
    creds = _get_credentials()
    if not creds:
        return None
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def discover_portfolio_sheets(query: str = "portfolio") -> List[Dict[str, str]]:
    """
    Search Google Drive for spreadsheets matching a query string.
    Returns a list of {id, name, modifiedTime} dicts.
    """
    try:
        drive = _get_drive_service()
        if not drive:
            return []
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


def fetch_sheet_as_csv(spreadsheet_id: str, sheet_name: Optional[str] = None) -> str:
    """
    Fetch a Google Sheet tab as raw CSV text with multi-tier fallback:
    1. Direct Google Docs CSV Export (fastest, works with shared links)
    2. Authenticated Google Docs CSV Export (using OAuth token)
    3. Google Sheets API v4 with tab auto-discovery
    """
    clean_id = extract_spreadsheet_id(spreadsheet_id)
    if not clean_id:
        logger.error("No valid spreadsheet ID provided.")
        return ""

    logger.info(f"Fetching Google Sheet CSV for ID: {clean_id}")

    # ── Tier 1: Direct Google Export URL (Public / Anyone with Link) ─────────
    export_url = f"https://docs.google.com/spreadsheets/d/{clean_id}/export?format=csv"
    if sheet_name:
        export_url += f"&sheet={sheet_name}"
        
    try:
        resp = requests.get(export_url, timeout=8, allow_redirects=True)
        if resp.status_code == 200 and not resp.text.strip().startswith("<!DOCTYPE html>"):
            logger.info("Successfully fetched sheet via direct CSV export URL.")
            return resp.text
    except Exception as e:
        logger.warning(f"Direct export URL failed: {e}")

    # ── Tier 2: Authenticated CSV Export (Using Bearer Token) ─────────────────
    creds = _get_credentials()
    if creds and creds.token:
        try:
            auth_headers = {"Authorization": f"Bearer {creds.token}"}
            resp = requests.get(export_url, headers=auth_headers, timeout=8, allow_redirects=True)
            if resp.status_code == 200 and not resp.text.strip().startswith("<!DOCTYPE html>"):
                logger.info("Successfully fetched sheet via authenticated CSV export.")
                return resp.text
        except Exception as e:
            logger.warning(f"Authenticated export URL failed: {e}")

    # ── Tier 3: Google Sheets API v4 Discovery & Fetch ────────────────────────
    try:
        sheets = _get_sheets_service()
        if sheets:
            # Discover first tab name if not specified
            target_range = sheet_name or "A:Z"
            if not sheet_name:
                try:
                    sheet_meta = sheets.spreadsheets().get(spreadsheetId=clean_id).execute()
                    sheet_tabs = sheet_meta.get("sheets", [])
                    if sheet_tabs:
                        first_tab_title = sheet_tabs[0]["properties"]["title"]
                        target_range = f"'{first_tab_title}'!A:Z"
                except Exception as meta_err:
                    logger.warning(f"Could not discover tab title: {meta_err}")

            result = sheets.spreadsheets().values().get(
                spreadsheetId=clean_id,
                range=target_range
            ).execute()

            rows = result.get("values", [])
            if rows:
                output = io.StringIO()
                writer = csv.writer(output)
                for row in rows:
                    writer.writerow(row)
                logger.info(f"Successfully fetched {len(rows)} rows via Sheets API v4.")
                return output.getvalue()
    except Exception as api_err:
        logger.error(f"Sheets API v4 fetch failed: {api_err}")

    return ""


def parse_portfolio_csv(csv_text: str) -> List[Dict[str, Any]]:
    """
    Parse a Google Sheet / CSV export into a list of ticker dicts.
    Supports case-insensitive column headers, synonyms, and flexible layouts.
    """
    if not csv_text or not csv_text.strip():
        return []

    lines = [line for line in csv_text.splitlines() if line.strip()]
    if not lines:
        return []

    # Detect header line (find line with 'symbol' or 'ticker' or standard header words)
    header_idx = 0
    for idx, line in enumerate(lines[:10]):
        low = line.lower()
        if "symbol" in low or "ticker" in low or "stock" in low or "company" in low or "asset" in low:
            header_idx = idx
            break

    relevant_csv = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(relevant_csv))
    tickers = []
    
    for row in reader:
        if not row:
            continue
        # Normalize keys to lowercase for flexible matching
        norm_row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
        
        # Try to find symbol
        symbol = None
        for sym_key in ["symbol", "ticker", "symbol/ticker", "ticker symbol", "stock", "code", "asset", "company", "instrument"]:
            if sym_key in norm_row and norm_row[sym_key]:
                val = str(norm_row[sym_key]).strip().upper()
                # Clean extraneous characters like quotes or parentheses
                val = re.sub(r"[^A-Z0-9\.\-]", "", val)
                if val and len(val) <= 10:
                    symbol = val
                    break
        
        # If no header match, check if the first column looks like a ticker
        if not symbol:
            first_val = list(row.values())[0] if row else None
            if first_val:
                clean_first = str(first_val).strip().upper()
                if 1 <= len(clean_first) <= 6 and clean_first.isalpha():
                    symbol = clean_first

        if not symbol:
            continue
            
        def safe_float(val):
            if val is None:
                return None
            try:
                clean_v = str(val).replace(",", "").replace("$", "").replace("%", "").strip()
                return float(clean_v)
            except (ValueError, TypeError):
                return None

        def safe_int(val):
            if val is None:
                return None
            try:
                clean_v = str(val).replace(",", "").replace("$", "").strip()
                return int(float(clean_v))
            except (ValueError, TypeError):
                return None

        # Try to find price / cost
        price = None
        for price_key in ["current price", "price", "last sale", "value", "close", "last", "avg price", "average cost", "cost", "market price"]:
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
        for high_key in ["high", "max", "52w high", "day high"]:
            if high_key in norm_row:
                high = safe_float(norm_row[high_key])
                if high is not None:
                    break

        # Try to find low
        low = None
        for low_key in ["low", "min", "52w low", "day low"]:
            if low_key in norm_row:
                low = safe_float(norm_row[low_key])
                if low is not None:
                    break

        # Try to find volume / quantity
        volume = None
        for vol_key in ["volume", "vol", "shares", "quantity", "qty", "units"]:
            if vol_key in norm_row:
                volume = safe_int(norm_row[vol_key])
                if volume is not None:
                    break

        # Try to find name / description
        name = None
        for name_key in ["name", "company name", "description", "security name"]:
            if name_key in norm_row and norm_row[name_key]:
                name = str(norm_row[name_key]).strip()
                break

        tickers.append({
            "symbol": symbol,
            "name": name,
            "current_price": price if price is not None else 0.0,
            "change": change if change is not None else 0.0,
            "high": high if high is not None else (price or 0.0),
            "low": low if low is not None else (price or 0.0),
            "volume": volume if volume is not None else 0,
        })

    # Deduplicate tickers by symbol
    seen = set()
    deduped = []
    for t in tickers:
        if t["symbol"] not in seen:
            seen.add(t["symbol"])
            deduped.append(t)

    logger.info(f"Parsed {len(deduped)} distinct tickers from CSV")
    return deduped


def sync_portfolio_from_sheet(
    spreadsheet_id: str,
    sheet_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    End-to-end: fetch a Google Sheet and return parsed tickers.
    """
    csv_text = fetch_sheet_as_csv(spreadsheet_id, sheet_name)
    if not csv_text:
        logger.warning(f"Sheet {spreadsheet_id} returned no data")
        return []
    return parse_portfolio_csv(csv_text)


def sync_all_portfolios_from_drive(
    query: str = "portfolio"
) -> Dict[str, Dict[str, Any]]:
    """
    Discover all portfolio sheets from Drive, fetch each one,
    and return a dict of {sheet_name: {sheet_id, tickers}}.
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
