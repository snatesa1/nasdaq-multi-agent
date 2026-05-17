import os
import sys
import logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run():
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "nasdaq_screener.csv")

    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        page = context.new_page()

        logger.info("Fetching data from NASDAQ API via Playwright...")
        # Add headers to avoid bot detection
        response = context.request.get(
            "https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&tableonly=true&limit=25&offset=0&download=true",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/"
            }
        )
        
        if response.ok:
            data = response.json()
            rows = data.get("data", {}).get("rows", [])
            if rows:
                import csv
                with open(target_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
                logger.info(f"✅ Successfully downloaded and saved CSV to {target_file}")
            else:
                logger.error("❌ No rows found in the API response data.")
        else:
            logger.error(f"❌ Failed to fetch data: {response.status} {response.status_text}")

        browser.close()

if __name__ == "__main__":
    run()
