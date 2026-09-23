"""
conftest.py - Shared Pytest Fixtures for OptionsLab E2E Test Suite.
"""
import sys
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from options_lab.api import db as database
from options_lab.api.saxo_client import SaxoClient


@pytest.fixture(scope="session", autouse=True)
def ensure_db_schema():
    """Ensures SQLite tables exist before any tests run."""
    database._init_db()


@pytest.fixture
def mock_saxo():
    """Provides a fully mocked SaxoClient with deterministic tick quantization and balances."""
    client = MagicMock(spec=SaxoClient)
    client.access_token = "mock_test_token"
    client.get_positions.return_value = {"positions": []}
    client.get_all_watchlist_instruments.return_value = []
    client.get_account_balances.return_value = {
        "total_equity": 100000.0,
        "cash_available": 70000.0,
        "margin_used": 0.0,
        "account_id": "MOCK-TEST-ACCOUNT",
        "currency": "USD"
    }

    def _mock_quantize(price: float, uic: int = None, asset_type: str = "StockOption") -> float:
        if price is None:
            return 0.0
        # Standard exchange tick rules: $0.05 for < $3.00, $0.10 for >= $3.00
        tick = 0.05 if price < 3.0 else 0.10
        return round(round(price / tick) * tick, 2)

    client.quantize_order_price.side_effect = _mock_quantize
    return client


@pytest.fixture
def sample_option_chain_contracts():
    """
    Returns realistic option chain contracts for INTC, COIN, SO for target expiry (31 DTE).
    """
    target_exp = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    contracts = []
    # INTC puts (spot ~$21)
    for strike, mid, iv in [(18.0, 0.25, 0.45), (19.0, 0.45, 0.44), (20.0, 0.75, 0.43), (21.0, 1.15, 0.42), (22.0, 1.65, 0.41)]:
        contracts.append({
            "symbol": "INTC",
            "expiration_date": target_exp,
            "strike": strike,
            "option_type": "put",
            "dte": 31,
            "bid": round(mid - 0.05, 2),
            "ask": round(mid + 0.05, 2),
            "mid": mid,
            "last_price": mid,
            "volume": 250,
            "open_interest": 1200,
            "implied_volatility": iv,
            "contract_symbol": f"INTC{target_exp.replace('-', '')}P{int(strike*1000):08d}",
            "updated_at": now_iso
        })

    # COIN puts (spot ~$210)
    for strike, mid, iv in [(160.0, 1.80, 0.65), (170.0, 2.50, 0.63), (180.0, 3.80, 0.61), (190.0, 5.50, 0.59)]:
        contracts.append({
            "symbol": "COIN",
            "expiration_date": target_exp,
            "strike": strike,
            "option_type": "put",
            "dte": 31,
            "bid": round(mid - 0.10, 2),
            "ask": round(mid + 0.10, 2),
            "mid": mid,
            "last_price": mid,
            "volume": 400,
            "open_interest": 2200,
            "implied_volatility": iv,
            "contract_symbol": f"COIN{target_exp.replace('-', '')}P{int(strike*1000):08d}",
            "updated_at": now_iso
        })

    # SO puts (spot ~$86)
    for strike, mid, iv in [(75.0, 0.35, 0.22), (80.0, 0.75, 0.20), (82.5, 1.10, 0.19), (85.0, 1.65, 0.18)]:
        contracts.append({
            "symbol": "SO",
            "expiration_date": target_exp,
            "strike": strike,
            "option_type": "put",
            "dte": 31,
            "bid": round(mid - 0.05, 2),
            "ask": round(mid + 0.05, 2),
            "mid": mid,
            "last_price": mid,
            "volume": 150,
            "open_interest": 800,
            "implied_volatility": iv,
            "contract_symbol": f"SO{target_exp.replace('-', '')}P{int(strike*1000):08d}",
            "updated_at": now_iso
        })

    return contracts, target_exp


@pytest.fixture
def populated_test_chains(sample_option_chain_contracts):
    """Populates SQLite cached_option_chains with test contracts and cleans up afterwards."""
    contracts, target_exp = sample_option_chain_contracts
    database.save_option_chain_contracts(contracts)
    yield contracts, target_exp
    # Teardown
    try:
        with database._get_conn() as conn:
            conn.execute(
                "DELETE FROM cached_option_chains WHERE symbol IN ('INTC', 'COIN', 'SO') AND expiration_date = ?",
                (target_exp,)
            )
            conn.commit()
    except Exception:
        pass
