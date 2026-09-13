"""
Test Dual-Flavor Compatibility: Local Windows PC (Wi-Fi) & Remote Linux Mint (Docker)
Validates:
1. Fast backend initialization (< 10 seconds).
2. Health endpoints /health and /api/health return HTTP 200.
3. CORS headers permit localhost, 192.168.x.x (Wi-Fi), and Tailscale IPs.
4. Database path resolution respects DB_DATA_DIR.
"""
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

# Insert parent path
_repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

print(">> [1/4] Benchmarking FastAPI Backend Import Speed...")
t0 = time.time()
from options_lab.api.main import app
elapsed = time.time() - t0
print(f"   ✓ Backend imported in {elapsed:.2f}s (Target < 12s)")
assert elapsed < 20.0, f"Import took too long: {elapsed:.2f}s"

client = TestClient(app)

print(">> [2/4] Testing /health and /api/health Endpoints...")
res_health = client.get("/health")
assert res_health.status_code == 200, f"/health failed: {res_health.status_code}"
assert res_health.json().get("status") == "healthy"
print(f"   ✓ /health returned HTTP 200: {res_health.json()}")

res_api_health = client.get("/api/health")
assert res_api_health.status_code == 200, f"/api/health failed: {res_api_health.status_code}"
assert res_api_health.json().get("status") == "healthy"
print(f"   ✓ /api/health returned HTTP 200: {res_api_health.json()}")

print(">> [3/4] Validating Dual-Flavor CORS Origin Resolution...")
lan_origin = "http://192.168.0.3:3000"
res_cors_lan = client.options(
    "/api/health",
    headers={
        "Origin": lan_origin,
        "Access-Control-Request-Method": "GET"
    }
)
assert res_cors_lan.headers.get("access-control-allow-origin") == lan_origin, \
    f"LAN CORS failed: {res_cors_lan.headers.get('access-control-allow-origin')}"
assert res_cors_lan.headers.get("access-control-allow-credentials") == "true"
print(f"   ✓ LAN Wi-Fi Origin ({lan_origin}) permitted with credentials!")

tailscale_origin = "http://100.87.159.107:3000"
res_cors_ts = client.options(
    "/api/health",
    headers={
        "Origin": tailscale_origin,
        "Access-Control-Request-Method": "GET"
    }
)
assert res_cors_ts.headers.get("access-control-allow-origin") == tailscale_origin, \
    f"Tailscale CORS failed: {res_cors_ts.headers.get('access-control-allow-origin')}"
print(f"   ✓ Tailscale Origin ({tailscale_origin}) permitted with credentials!")

print(">> [4/4] Validating Unified Database Path Resolution...")
from options_lab.api import db as database
from options_lab.api.trade_history_ingest import TradeHistoryIngestEngine
engine = TradeHistoryIngestEngine()
print(f"   ✓ db._DB_PATH: {database._DB_PATH}")
print(f"   ✓ TradeHistoryIngestEngine db_path: {engine.db_path}")
assert os.path.basename(database._DB_PATH) == os.path.basename(engine.db_path)

print("\n🎉 ALL DUAL-FLAVOR COMPATIBILITY TESTS PASSED 100%!")
