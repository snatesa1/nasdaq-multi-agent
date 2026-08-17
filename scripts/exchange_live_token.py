import os
import sys
import json
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

code = "8ad33193-f77f-472e-92dc-debb6683ac8e"
app_key = os.getenv("SAXO_APP_KEY", "086a7ec061b240c49c4d2bc828d6399b")
app_secret = os.getenv("SAXO_APP_SECRET", "c1866b3d04d64e72936e53f1fb803455")
token_endpoint = "https://live.logonvalidation.net/token"
redirect_urls = ["https://Akpegis-Agent.com.sg", "https://akpegis-agent.com.sg"]

print(f">> EXCHANGING SAXO LIVE CODE: {code}")

token_data = None
for redirect_url in redirect_urls:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": app_key,
        "client_secret": app_secret,
        "redirect_uri": redirect_url
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        resp = requests.post(token_endpoint, data=payload, headers=headers, timeout=10)
        print(f"Attempt with redirect_url '{redirect_url}': Status {resp.status_code}")
        if resp.status_code == 200:
            token_data = resp.json()
            print("[SUCCESS] Successfully exchanged OAuth code for Live Token!")
            break
        else:
            print("Response:", resp.text)
    except Exception as e:
        print("Error:", e)

if not token_data and os.getenv("SAXO_APP_SECRET_ALT"):
    # Try alternate secret
    alt_secret = os.getenv("SAXO_APP_SECRET_ALT")
    print(f">> Retrying with alternate secret...")
    for redirect_url in redirect_urls:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": app_key,
            "client_secret": alt_secret,
            "redirect_uri": redirect_url
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            resp = requests.post(token_endpoint, data=payload, headers=headers, timeout=10)
            print(f"Alt attempt with redirect_url '{redirect_url}': Status {resp.status_code}")
            if resp.status_code == 200:
                token_data = resp.json()
                print("[SUCCESS] Successfully exchanged OAuth code with alternate secret!")
                break
            else:
                print("Response:", resp.text)
        except Exception as e:
            print("Error:", e)

if token_data:
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    print(f"\n[LIVE ACCESS TOKEN OBTAINED]: {access_token[:30]}... (Length: {len(access_token)})")
    
    # Query Live Balances
    live_h = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://gateway.saxobank.com/openapi/"
    
    print("\n[1] Querying Live Balances (/port/v1/balances/me)...")
    r_bal = requests.get(f"{base_url}port/v1/balances/me", headers=live_h, timeout=10)
    print(f"Balances Status: {r_bal.status_code}")
    if r_bal.status_code == 200:
        print(json.dumps(r_bal.json(), indent=2))
    else:
        print(r_bal.text)

    print("\n[2] Querying Live Positions (/port/v1/positions/me)...")
    r_pos = requests.get(f"{base_url}port/v1/positions/me", headers=live_h, timeout=10)
    print(f"Positions Status: {r_pos.status_code}")
    if r_pos.status_code == 200:
        print(json.dumps(r_pos.json(), indent=2))
    else:
        print(r_pos.text)

    print("\n[3] Querying Live Orders Blotter (/port/v1/orders/me)...")
    r_ord = requests.get(f"{base_url}port/v1/orders/me", headers=live_h, timeout=10)
    print(f"Orders Status: {r_ord.status_code}")
    if r_ord.status_code == 200:
        print(json.dumps(r_ord.json(), indent=2))
    else:
        print(r_ord.text)

    print("\n[4] Querying Audit Order Activities (/cs/v1/audit/orderactivities)...")
    r_aud = requests.get(f"{base_url}cs/v1/audit/orderactivities", headers=live_h, timeout=10)
    print(f"Audit Status: {r_aud.status_code}")
    if r_aud.status_code == 200:
        print(json.dumps(r_aud.json(), indent=2))
    else:
        print(r_aud.text)
else:
    print("[FAIL] Could not exchange code. Please check code or expiry.")
