import os
import sys
import time
import requests
import subprocess

print("=" * 75)
print(">> EXECUTING MANDATORY RIGOROUS END-TO-END VALIDATION SUITE")
print("=" * 75)

# Step 1: Static Bundle String Inspection
out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'options_lab', 'frontend', 'out'))
index_html = os.path.join(out_dir, 'index.html')

with open(index_html, 'r', encoding='utf-8') as f:
    content = f.read()

assert 'Anna Adame' not in content, "Validation Failed: 'Anna Adame' still found in static bundle!"
assert 'Sathish' in content, "Validation Failed: 'Sathish' profile not found in static bundle!"
print("[+] Test 1 PASSED: Static bundle verified -> 'Anna Adame' is GONE, 'Sathish' is PRESENT.")

# Step 2: Test FastAPI Server serving static bundle and Live Saxo API
# We test endpoints against port 8000
try:
    health_resp = requests.get('http://127.0.0.1:8000/health', timeout=3)
    server_running = health_resp.status_code == 200
except Exception:
    server_running = False

server_process = None
if not server_running:
    print("[*] Starting backend uvicorn server on port 8000...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "options_lab.api.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    )
    time.sleep(4)

# Test root serving static files
root_resp = requests.get('http://127.0.0.1:8000/', timeout=5)
assert root_resp.status_code == 200, f"Root static page failed with {root_resp.status_code}"
assert 'Sathish' in root_resp.text, "Served HTTP root response missing 'Sathish'!"
assert 'Anna Adame' not in root_resp.text, "Served HTTP root response contains 'Anna Adame'!"
print("[+] Test 2 PASSED: FastAPI is actively serving production static bundle with 200 OK.")

# Test Live Broker Endpoints
status_resp = requests.get('http://127.0.0.1:8000/api/broker/status', timeout=5)
assert status_resp.status_code == 200, f"Broker status endpoint failed: {status_resp.status_code}"
status_data = status_resp.json()
print(f"[+] Test 3 PASSED: Broker Status -> Environment: {status_data.get('environment')}, Connected: {status_data.get('connected')}")

pos_resp = requests.get('http://127.0.0.1:8000/api/broker/positions', timeout=8)
assert pos_resp.status_code == 200, f"Broker positions failed: {pos_resp.status_code}"
pos_data = pos_resp.json()
print(f"[+] Test 4 PASSED: Live Broker Positions -> {len(pos_data.get('positions', []))} Open Positions retrieved successfully.")

orders_resp = requests.get('http://127.0.0.1:8000/api/broker/orders', timeout=8)
assert orders_resp.status_code == 200, f"Broker orders failed: {orders_resp.status_code}"
orders_data = orders_resp.json()
print(f"[+] Test 5 PASSED: Live Broker Orders Blotter -> {len(orders_data.get('orders', []))} Historical Orders retrieved successfully.")

# Test Disconnect Endpoint
disconnect_resp = requests.post('http://127.0.0.1:8000/api/broker/oauth/disconnect', timeout=5)
assert disconnect_resp.status_code == 200, f"Disconnect endpoint failed: {disconnect_resp.status_code}"
print("[+] Test 6 PASSED: Bot Disconnect & Sign Out endpoint returned 200 OK.")

print("\n" + "=" * 75)
print(">> ALL 6 RIGOROUS END-TO-END VALIDATION TESTS PASSED WITH 100% SUCCESS!")
print("=" * 75)
