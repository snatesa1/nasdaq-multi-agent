import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

from options_lab.api.drive_sync import fetch_sheet_as_csv, parse_portfolio_csv, extract_spreadsheet_id

url = "https://docs.google.com/spreadsheets/d/1MlLfn2RbKaa5yohd09MhqzFJj1HeFTlRUmIbj-5_xMw/edit?usp=sharing"
clean_id = extract_spreadsheet_id(url)
print(f"Clean ID: {clean_id}")

csv_data = fetch_sheet_as_csv(clean_id)
print(f"CSV Data Length: {len(csv_data)}")
print("--- CSV Data Preview ---")
print(csv_data[:500])
print("------------------------")

tickers = parse_portfolio_csv(csv_data)
print(f"Parsed Tickers ({len(tickers)}): {tickers}")
