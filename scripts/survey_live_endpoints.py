import os
import sys
import json
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

token = os.getenv("SAXO_ACCESS_TOKEN")
base_url = "https://gateway.saxobank.com/openapi/"
headers = {"Authorization": f"Bearer {token}"}

endpoints = [
    ("Clients Me", "port/v1/clients/me"),
    ("Accounts Me", "port/v1/accounts/me"),
    ("Balances Me", "port/v1/balances/me"),
    ("Positions Me", "port/v1/positions/me"),
    ("Net Positions Me", "port/v1/netpositions/me"),
    ("Orders Me", "port/v1/orders/me"),
    ("Audit Order Activities", "cs/v1/audit/orderactivities?$top=20"),
    ("Exposure Me", "port/v1/exposure/me"),
]

print("=" * 70)
print(">> SAXO OPENAPI READ-ONLY ENDPOINT CAPABILITY SURVEY (LIVE ACCOUNT)")
print("=" * 70)

for name, path in endpoints:
    url = f"{base_url}{path}"
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        print(f"\n[+] {name} (GET {path}) -> Status {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                keys = list(data.keys())
                count = len(data.get("Data", [])) if "Data" in data else len(keys)
                print(f"    Available Fields/Count: {count} items | Keys: {keys[:6]}")
            elif isinstance(data, list):
                print(f"    Returned List: {len(data)} items")
        else:
            print(f"    Message: {resp.text[:120]}")
    except Exception as e:
        print(f"    Error: {e}")
