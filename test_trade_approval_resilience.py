import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))

from options_lab.api.main import app
from options_lab.api import db as database
from options_lab.api.trade_staging import TradeStagingEngine
from options_lab.api.weekly_intelligence import WeeklyIntelligenceEngine

def test_candidate_trade_id_generation():
    engine = WeeklyIntelligenceEngine()
    cand = engine._build_dynamic_trade_candidate(symbol="INTC", strategy="CSP", dte=30)
    assert cand is not None
    assert "trade_id" in cand and cand["trade_id"].startswith("TRD-")
    assert cand["id"] == cand["trade_id"]
    assert cand["staged_trade_id"] == cand["trade_id"]

def test_trade_staging_preserves_id():
    staging = TradeStagingEngine()
    cand = {
        "trade_id": "TRD-TEST1234",
        "symbol": "KO",
        "strategy": "CSP",
        "strike": 60.0,
        "spot_price": 65.0,
        "delta": -0.20,
        "dte": 30,
        "premium_estimate": 2.50
    }
    staged = staging.stage_recommendation(cand, week_label="2026-W38")
    assert staged["trade_id"] == "TRD-TEST1234"
    assert cand["trade_id"] == "TRD-TEST1234"
    assert cand["id"] == "TRD-TEST1234"
    
    fetched = database.get_staged_trade_by_id("TRD-TEST1234")
    assert fetched is not None
    assert fetched["symbol"] == "KO"

def test_approve_endpoint_with_direct_id():
    client = TestClient(app)
    staging = TradeStagingEngine()
    cand = {
        "symbol": "BAC",
        "strategy": "CSP",
        "strike": 35.0,
        "spot_price": 40.0,
        "delta": -0.18,
        "dte": 30,
        "premium_estimate": 1.50
    }
    staged = staging.stage_recommendation(cand, week_label="2026-W38")
    tid = staged["trade_id"]
    
    # 1. Approve using trade_id key
    res = client.post("/api/trades/approve", json={"trade_id": tid})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["APPROVED", "PLACED", "FILLED", "BLOCKED_SAFETY_CONFIG", "BLOCKED_NO_CONTRACT", "UNCONFIRMED_TIMEOUT"]

def test_approve_endpoint_with_id_alias():
    client = TestClient(app)
    staging = TradeStagingEngine()
    cand = {
        "symbol": "CSCO",
        "strategy": "CSP",
        "strike": 45.0,
        "spot_price": 50.0,
        "delta": -0.15,
        "dte": 30,
        "premium_estimate": 1.25
    }
    staged = staging.stage_recommendation(cand, week_label="2026-W38")
    tid = staged["trade_id"]
    
    # Approve using id alias
    res = client.post("/api/trades/approve", json={"id": tid})
    assert res.status_code == 200

def test_approve_endpoint_self_heal_on_unstaged_payload():
    client = TestClient(app)
    # Provide candidate payload without existing database record
    unstaged_cand = {
        "trade_id": "TRD-UNSTAGED-99",
        "symbol": "SO",
        "strategy": "CSP",
        "strike": 75.0,
        "spot_price": 85.0,
        "delta": -0.12,
        "dte": 30,
        "premium_estimate": 2.10
    }
    res = client.post("/api/trades/approve", json=unstaged_cand)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") is not None
