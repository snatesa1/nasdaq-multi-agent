# Project: OptionsLab Deterministic Options Harvest Pipeline

## Architecture
OptionsLab provides weekly macro intelligence, wheel candidate generation, dialectical consensus debate between investment personas, and trade staging.
The deterministic harvest pipeline ensures offline reproducibility, pricing transparency, and strict margin safety:
1. **Option Chain Ingestion**: `options_lab/api/market_data.py` interfaces with Yahoo Finance to batch-fetch full option chains for target monthly expirations (30–35 DTE, e.g. 2026-10-23) and caches them into SQLite `cached_option_chains` table (`options_lab/api/db.py`).
2. **Strategy Selection**: `options_lab/api/weekly_intelligence.py` inspects `cached_option_chains` to select put contracts matching delta [-0.22, -0.18] for core user tickers (`INTC`, `COIN`, `SO`) and qualified watchlist candidates, bypassing legacy continuous price heuristics and artificial strike/premium filters.
3. **Middle-Ground Pricing Engine**: Calculates limit prices as a +1.5% seller markup over the average of Black-Scholes benchmark and live quote (`mid`/`last`), quantized to valid exchange ticks ($0.05/$0.10) via `quantize_order_price`.
4. **Trade Staging & Margin Guardian**: `options_lab/api/trade_staging.py` persists `limit_price` into `staged_trades` (`optionslab.db`). `options_lab/api/margin_guardian.py` sizes contracts to achieve >= $1,500/month harvest while enforcing a 75% margin ceiling and accommodating single-position collateral for high-strike candidates like COIN.
5. **Dialectical Debate Arena**: Persona critiques, Mode 2 allocation, and UI badges synchronize with the $1,500 mandate ($375/slot across 4 trades) and utilize active Gemini model names.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Target Expiration Cycle Resolution | Resolve Friday monthly option cycle 30–35 DTE (e.g. 2026-10-23) | M1 | Survey / R1 |
| 2 | Batch Option Chain SQLite Ingestion | Populate `cached_option_chains` from Yahoo Finance with zero redundant queries if fresh | M1 | Survey / R1 |
| 3 | SQLite-Driven Put Contract Selection | Select optimal strike with delta [-0.22, -0.18] directly from cached contracts | M1 | Survey / R2 |
| 4 | Triumvirate Candidate Preservation | Prevent INTC, COIN, SO from being dropped by Mode 1 filters ($0.50-$5.00 prem / $220 strike) | M1 | Survey / R2 |
| 5 | Middle-Ground Limit Price Calculation | Compute limit price from BS price and mid quote with +1.5% markup and tick quantization | M2 | Survey / R3 |
| 6 | Limit Price Staging & SQLite Persistence | Pass `limit_price` in `TradeStagingEngine.stage_recommendation` and store in `staged_trades` | M2 | Survey / R3 |
| 7 | Dynamic Margin Sizing for $1,500 Harvest | Size contracts across candidates to reach >= $1,500/month harvest | M2 | Survey / R4 |
| 8 | High-Strike Single-Trade Collateral Flexibility | Adjust MarginGuardian single-position collateral sub-cap for COIN while <= 75% margin | M2 | Survey / R4 |
| 9 | Dialectical Debate Arena $1,500 Recalibration | Update persona critique statements ($375/slot), Mode 2 targets, options stance, and UI cards | M3 | Survey / R5 |
| 10 | Gemini Model Failover Robustness | Use active models (`gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-3.6-flash`) with non-blocking fallback | M3 | Survey / R5 |
| 11 | End-to-End Pipeline Verification | Pass `verify_middle_ground_pricing.py` and regression pytest suite with zero errors | M4 | Survey / Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Option Chain Ingestion & Deterministic Selection | R1 & R2: Ingestion to SQLite, delta-based strike selection from cache, triage filters | None | PLANNED |
| M2 | Middle-Ground Pricing, Staging & Margin Sizing | R3 & R4: Limit price calculation, trade staging persistence, $1,500 harvest & margin cap | M1 | PLANNED |
| M3 | Dialectical Arena Synchronization & Model Failover | R5: Critique statements, Mode 2 calibration, UI badges, active Gemini models | M2 | PLANNED |
| M4 | Final Integration, Verification & Adversarial Hardening | E2E test suite pass, `verify_middle_ground_pricing.py`, regression tests | M3, E2E Track | PLANNED |

## Interface Contracts
### `market_data.py` ↔ `weekly_intelligence.py`
- `fetch_and_dump_option_chain_from_yahoo(symbol: str, target_expiration_date: str, dte: int) -> bool`:
  Fetches calls and puts from Yahoo Finance for `symbol` and `target_expiration_date`, computes `mid`, and batch-persists into SQLite table `cached_option_chains`. Returns `True` on success.
- `db.get_cached_option_chain(symbol: str, expiration_date: str, option_type: str = "put") -> List[Dict]`:
  Retrieves cached contracts sorted by `strike ASC`. Returns empty list if not found.

### `weekly_intelligence.py` ↔ `trade_staging.py`
- `TradeStagingEngine.stage_recommendation(candidate: Dict, notes: str, ...) -> Dict`:
  Candidate dictionary MUST contain `"limit_price": float`. `stage_recommendation` preserves `"limit_price"` in `staged_record` and passes it to `db.save_staged_trade`.
- `db.save_staged_trade(trade: Dict) -> int`:
  Saves `limit_price` into `staged_trades` table.

### `weekly_intelligence.py` ↔ `margin_guardian.py`
- `MarginGuardian.validate_trade_margin(...)`:
  Validates individual trade collateral against account limits, supporting high-strike candidates (e.g. COIN) without exceeding total cash collateral limit (50%) and margin ceiling (75%).
- `MarginGuardian.validate_cumulative_basket(trades: List[Dict], account_equity: float, cash_available: float) -> Tuple[bool, str, Dict]`:
  Enforces cumulative margin utilization <= 75.0% and collateral within budget.

## Code Layout
- `options_lab/api/db.py`: SQLite schemas and helper functions (`cached_option_chains`, `staged_trades`).
- `options_lab/api/market_data.py`: Yahoo Finance option chain fetching, caching, and quote resolution.
- `options_lab/api/weekly_intelligence.py`: Candidate generation, strategy selection, middle-ground pricing, dynamic basket sizing, dialectical debate arena.
- `options_lab/api/trade_staging.py`: Trade staging engine and staging execution records.
- `options_lab/api/margin_guardian.py`: Account margin, cash collateral, and risk limit validations.
- `options_lab/api/config.py`: Gemini model lists and settings.
- `options_lab/frontend/src/app/weekly-intelligence/page.tsx`: Frontend debate arena cards and badges.
- `scripts/verify_middle_ground_pricing.py`: Verification harness.
- `test_dialectical_consensus.py`, `options_lab/test_wheel_dte_constraints.py`: Regression test suites.
- `tests/e2e/`: Opaque-box E2E test suite directory managed by E2E Testing Track.
