import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any
import yfinance as yf

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
GF_EARNINGS_PATH = os.path.join(DATA_DIR, "google_finance_earnings.html")

def parse_google_finance_earnings_html() -> List[Dict[str, Any]]:
    """
    Parse a user-saved Google Finance earnings HTML page.
    Robustly extracts ticker, company name, date/time, period, EPS est, and Revenue est.
    """
    if not os.path.exists(GF_EARNINGS_PATH):
        logger.info(f"Google Finance earnings HTML not found at {GF_EARNINGS_PATH}. Skipping.")
        return []

    try:
        with open(GF_EARNINGS_PATH, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        
        # Find all quote links in format ./quote/SYMBOL:EXCHANGE
        quote_links = soup.find_all("a", href=re.compile(r'^\./quote/[A-Z0-9\.\-]+:[A-Z0-9]+'))
        logger.info(f"GF parser: Found {len(quote_links)} quote links in HTML.")

        entries = []
        seen_tickers = set()

        for link in quote_links:
            href = link.get("href", "")
            match = re.search(r'^\./quote/([A-Z0-9\.\-]+):([A-Z0-9]+)', href)
            if not match:
                continue
                
            symbol = match.group(1).upper()
            exchange = match.group(2).upper()
            
            # Avoid duplicate tickers within the calendar view
            if symbol in seen_tickers:
                continue
                
            # Look up adjacent elements for names, dates, and estimates
            # We search up to parent container that contains the card details
            # A typical Google Finance card holds the date, company name, period, EPS, and Rev
            # We climb up the tree to find a parent that contains typical labels
            parent = link
            card_content = ""
            for _ in range(6): # climb up to 6 levels to find a suitable card container
                if parent is None:
                    break
                parent_text = parent.get_text()
                if "period" in parent_text.lower() or "eps est" in parent_text.lower() or "rev est" in parent_text.lower():
                    card_content = parent_text
                    break
                parent = parent.parent
                
            if not card_content:
                # If no container found, try siblings of the link
                parent = link.parent
                card_content = parent.get_text() if parent else ""

            # Extract fields using regex on the container text
            # Clean up double whitespaces and newlines
            clean_text = " ".join(card_content.split())
            
            # Extract Company Name
            # Often, the link text itself is the ticker or company name
            link_text = link.get_text().strip()
            company_name = link_text if link_text != symbol else symbol
            
            # Extract Period
            period = None
            period_match = re.search(r'Period\s+([A-Za-z0-9\s]+)', clean_text, re.IGNORECASE)
            if period_match:
                period = period_match.group(1).strip()

            # Extract EPS Estimate
            eps_est = None
            eps_match = re.search(r'EPS est\.\s+([\$0-9\.\-\u2014]+)', clean_text, re.IGNORECASE)
            if eps_match:
                eps_est = eps_match.group(1).strip().replace("—", "")
                if not eps_est or eps_est == "-":
                    eps_est = None

            # Extract Revenue Estimate
            rev_est = None
            rev_match = re.search(r'Rev est\.\s+([A-Za-z0-9\.\-\u2014]+)', clean_text, re.IGNORECASE)
            if rev_match:
                rev_est = rev_match.group(1).strip().replace("—", "")
                if not rev_est or rev_est == "-":
                    rev_est = None
                    
            # Try to identify day of week / date (e.g. "Tue 14", "Wed 22")
            # Usually written in headers above or inside the card
            day_str = None
            day_match = re.search(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\b', clean_text)
            if day_match:
                day_str = day_match.group(0)
            else:
                # Fallback: search adjacent header text or parent text
                day_match_broad = re.search(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b', clean_text)
                if day_match_broad:
                    day_str = day_match_broad.group(0)

            # Construct entry
            entries.append({
                "symbol": symbol,
                "exchange": exchange,
                "name": company_name,
                "period": period,
                "eps_forecast": eps_est,
                "revenue_forecast": rev_est,
                "day_str": day_str or "Upcoming",
                "source": "google_finance"
            })
            seen_tickers.add(symbol)
            
        logger.info(f"Parsed {len(entries)} earnings entries from Google Finance HTML.")
        return entries
    except Exception as e:
        logger.error(f"Error parsing Google Finance HTML: {e}")
        return []

def fetch_nasdaq_calendar_for_date(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetch earnings calendar for a single date from api.nasdaq.com.
    """
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rows = data.get("data", {}).get("rows", [])
            results = []
            for row in rows or []:
                symbol = row.get("symbol", "").strip().upper()
                if not symbol:
                    continue
                results.append({
                    "symbol": symbol,
                    "name": row.get("name"),
                    "eps_forecast": row.get("epsForecast"),
                    "time_of_day": row.get("time"), # e.g. "time-after-hours", "time-pre-market"
                    "date_str": date_str,
                    "source": "nasdaq_api"
                })
            return results
    except Exception as e:
        logger.error(f"Error fetching Nasdaq calendar for {date_str}: {e}")
    return []

def fetch_nasdaq_calendar_for_week(start_date: datetime) -> List[Dict[str, Any]]:
    """
    Fetch upcoming earnings calendar from Nasdaq API for the week starting from start_date.
    Includes Monday through Friday.
    """
    # Find the Monday of the target week
    days_to_monday = start_date.weekday()
    monday = start_date - timedelta(days=days_to_monday)
    
    week_entries = []
    for i in range(5): # Monday to Friday
        day = monday + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        logger.info(f"Fetching Nasdaq calendar for date: {date_str}")
        day_entries = fetch_nasdaq_calendar_for_date(date_str)
        week_entries.extend(day_entries)
        
    logger.info(f"Fetched total of {len(week_entries)} entries from Nasdaq week calendar.")
    return week_entries

def get_upcoming_earnings_calendar() -> List[Dict[str, Any]]:
    """
    Get next week's earnings calendar:
    1. Try parsing Google Finance HTML.
    2. Fall back to Nasdaq Calendar API.
    """
    # 1. Try Google Finance HTML parser first
    gf_entries = parse_google_finance_earnings_html()
    if gf_entries:
        logger.info(f"Using {len(gf_entries)} entries from Google Finance calendar.")
        return gf_entries
        
    # 2. Fall back to Nasdaq calendar API
    logger.info("Google Finance HTML not available or empty. Falling back to Nasdaq Calendar API...")
    # Calculate next week (we assume next Monday)
    today = datetime.now()
    # If today is Saturday/Sunday, next week starts in 2-3 days. Otherwise, starts next Monday.
    next_week = today + timedelta(days=(7 - today.weekday()) if today.weekday() < 5 else (7 - today.weekday() + 7) % 7)
    if today.weekday() >= 5: # weekend
        next_week = today + timedelta(days=(7 - today.weekday()) % 7) # next Monday
    else:
        next_week = today + timedelta(days=7 - today.weekday()) # next Monday
        
    return fetch_nasdaq_calendar_for_week(next_week)

def fetch_historical_earnings_dates(symbol: str) -> List[datetime]:
    """
    Fetch the last 4 earnings announcement dates for a symbol using yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.earnings_dates
        if calendar is None or calendar.empty:
            logger.warning(f"No historical earnings dates found for {symbol} in ticker.earnings_dates.")
            # Fall back to a rough lookup or return empty
            return []
            
        # Get index dates, convert to timezone-naive datetimes
        dates = [d.to_pydatetime() for d in calendar.index]
        # Filter for past dates (earnings dates in yfinance might include upcoming ones)
        now = datetime.now(dates[0].tzinfo) if dates else datetime.now()
        past_dates = [d.replace(tzinfo=None) for d in dates if d < now]
        
        # Return last 4 past earnings dates (most recent first)
        past_dates.sort(reverse=True)
        return past_dates[:4]
    except Exception as e:
        logger.error(f"Failed to fetch historical earnings dates for {symbol}: {e}")
        return []
