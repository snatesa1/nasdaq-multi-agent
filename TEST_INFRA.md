# OptionsLab E2E Test Infrastructure & Test Architecture Specification

## 1. Overview & Philosophy
The OptionsLab Deterministic Options Harvest Pipeline provides automated macro intelligence, options chain ingestion, deterministic strike selection, middle-ground limit order pricing, margin guardian risk controls, dynamic harvest sizing, and multi-agent dialectical consensus debate.

The E2E Test Suite (`tests/e2e/`) is authored under an **opaque-box, requirement-driven testing methodology**. Tests verify observable behaviors, state transitions, mathematical correctness, database persistence, and safety contracts strictly derived from authoritative specifications (`ORIGINAL_REQUEST.md` and `PROJECT.md`), completely independent of transient internal implementation details.

### Core Testing Invariants:
1. **Windows Native PowerShell (`pwsh`) Execution**: All tests execute strictly natively in Windows PowerShell (`.\venv_win\Scripts\python.exe -m pytest tests/e2e/`). WSL is strictly prohibited.
2. **Local SQLite Primary**: Tests verify that local SQLite (`optionslab.db`) is the primary, single source of truth for option chain caching and staged trade lifecycle persistence.
3. **Deterministic Verification**: Tests isolate network/external dependencies via reproducible deterministic fixtures while exercising authentic business logic paths.
4. **Adversarial & Boundary Hardening**: Tests actively probe boundary conditions, edge cases, and stress limits across all tiers.

---

## 2. 4-Tier Test Architecture

```
tests/e2e/
├── conftest.py                     # Shared fixtures (isolated DB, mock Saxo, sample option chains)
├── test_tier1_feature_coverage.py   # Tier 1: Core Feature Verification (R1 - R5)
├── test_tier2_boundary_corner.py    # Tier 2: Boundaries, Tick Scheme & Risk Limits
├── test_tier3_cross_feature.py      # Tier 3: Integrated Pipeline Flows & Multi-Agent Consensus
└── test_tier4_real_world.py        # Tier 4: Real-World Harvest Scenarios & SQLite Persistence
```

### Tier 1: Feature Coverage (Requirements R1 - R5)
Validates the fundamental contract of each requirement:
- **R1: Batch Option Chain SQLite Ingestion & Caching**:
  - `cached_option_chains` table schema integrity.
  - Batch upserting calls and puts via `save_option_chain_contracts`.
  - Ascending strike ordering via `get_cached_option_chain`.
  - Same-day freshness checking via `has_fresh_option_chain`.
  - Elimination of redundant API roundtrips when fresh cache is present.
- **R2: Deterministic Strategy Selection from Local SQLite**:
  - Strike selection targeting delta in $[-0.22, -0.18]$ (closest to $-0.20$).
  - Target monthly option cycle resolution for 30–35 DTE window (e.g. `2026-10-23`).
  - Guaranteed inclusion of approved tickers (`INTC`, `COIN`, `SO`) in Mode 1 candidates without rejection by legacy filters ($0.50-$5.00 premium or $220 strike).
- **R3: Middle-Ground Pricing Engine & Quantization**:
  - Calculation formula: `base_anchor = (mid_price + bs_price) / 2.0`, `favorable_premium = base_anchor * 1.015` (+1.5% favorable seller markup within the +1% to +2% specification).
  - Quantization to valid exchange tick increments ($0.05 / $0.10).
  - Preservation of non-null `limit_price` in candidate dictionaries, `TradeStagingEngine.stage_recommendation()`, and SQLite `staged_trades` records.
- **R4: Open-Ended $1,500/Month Harvest & 75% Margin Sizing**:
  - Dynamic contract sizing scaling to hit or exceed the $1,500/month harvest mandate.
  - Cumulative account margin utilization strictly $\le 75.0\%$.
  - Single-position collateral flexibility accommodating higher-strike candidates like `COIN` (e.g., $16,500 collateral) without crowding out portfolio diversification.
- **R5: Dialectical Debate Arena Synchronization**:
  - Executive Allocator trade-off matrix updated to `/ $1,500` for Monthly Harvest Goal.
  - Financial Analyst critique statement updated to reflect dynamic target per slot (~$375/slot).
  - Options stance reflects $1,500/mo harvest and 75% margin ceiling.
  - Non-blocking active Gemini model rotation with offline institutional fallbacks.

### Tier 2: Boundary & Corner Cases
Stresses edge conditions, tick boundary mechanics, and risk constraints:
- **Cache Cold-Start vs. Warm-Hit**:
  - Empty cache scenario: verifies graceful fallback, ingestion trigger, or handling when zero cached contracts exist.
  - Cache staleness: contracts with `updated_at` before today are treated as non-fresh, triggering refresh.
- **Tick Size Boundaries**:
  - Option prices $< \$3.00$: quantized to $\$0.05$ increments (e.g., $\$0.83 \rightarrow \$0.85$, $\$2.98 \rightarrow \$3.00$).
  - Option prices $\ge \$3.00$: quantized to $\$0.10$ increments when standard rules apply (e.g., $\$3.12 \rightarrow \$3.10$, $\$3.17 \rightarrow \$3.20$).
  - Boundary behavior at exact $\$3.00$ threshold.
- **High-Strike Ticker Collateral Stress**:
  - High-strike tickers (e.g., `COIN` at strikes $\$165 - \$220$) requiring $\$16,500 - \$22,000$ collateral validated against single-position sub-caps.
  - Verification that valid single-position collateral does not exceed total account collateral budget ($35,000 / 50% cash) while passing approval.
- **Margin Ceiling Strict Boundary**:
  - Account margin utilization at exactly $75.0\%$ (passes / approved).
  - Account margin utilization at $75.1\%$ (fails / rejected with `MARGIN_LIMIT_EXCEEDED`).
  - Cash collateral utilization at exactly $50.0\%$ vs $50.1\%$.

### Tier 3: Cross-Feature Combinations
Validates end-to-end multi-module integration:
- **Full Ingestion $\rightarrow$ Selection $\rightarrow$ Pricing $\rightarrow$ Staging Flow**:
  - Populates test option contracts in SQLite `cached_option_chains`.
  - Runs candidate generation selecting optimal delta put strike.
  - Evaluates middle-ground price computation with +1.5% markup and quantization.
  - Stages recommendation via `TradeStagingEngine`.
  - Verifies SQLite `staged_trades` row contains identical `limit_price`, `strike`, `contracts`, `expiration_date`, and `pricing_source`.
- **Mode 1 Harvest Blotter + Sub-Agent Consensus Synthesis**:
  - Evaluates dynamic sizing across multiple candidates from distinct GICS sectors.
  - Verifies aggregated harvest meets or exceeds $\$1,500$.
  - Verifies 3-persona consensus metadata (`financial_analyst`, `risk_aggregator`, `executive_allocator`) embedded in staged trades and blotter summary.

### Tier 4: Real-World Scenarios
Validates production readiness and persistent data contracts:
- **End-to-End Monthly Harvest Verification**:
  - Executes full weekly macro & edge analysis with authentic market quotes for target monthly expiry (30–35 DTE, e.g. 2026-10-23).
  - Verifies triumvirate tickers (`INTC`, `COIN`, `SO`) are present in staged candidates.
  - Asserts all staged trades have positive, non-null `limit_price` quantized to valid ticks.
  - Asserts cumulative harvest $\ge \$1,500$ (with tolerance $\ge \$1,490$).
  - Confirms dialectical arena trade-off matrix displays `/ $1,500`.
- **Database Persistence & Lifecycle Auditing**:
  - Verifies persistent records in `cached_option_chains` and `staged_trades`.
  - Confirms trade approval lifecycle transitions correctly update `status`, `approved_at`, and maintain `limit_price`.

---

## 3. Test Runner & Execution Guide

### Run Entire E2E Test Suite:
```powershell
.\venv_win\Scripts\python.exe -m pytest tests/e2e/ -v
```

### Run Specific Tiers:
```powershell
# Tier 1: Feature Coverage
.\venv_win\Scripts\python.exe -m pytest tests/e2e/test_tier1_feature_coverage.py -v

# Tier 2: Boundary & Corner Cases
.\venv_win\Scripts\python.exe -m pytest tests/e2e/test_tier2_boundary_corner.py -v

# Tier 3: Cross-Feature Combinations
.\venv_win\Scripts\python.exe -m pytest tests/e2e/test_tier3_cross_feature.py -v

# Tier 4: Real-World Scenarios
.\venv_win\Scripts\python.exe -m pytest tests/e2e/test_tier4_real_world.py -v
```

### Run With Regression Baselines:
```powershell
.\venv_win\Scripts\python.exe -m pytest tests/e2e/ test_dialectical_consensus.py options_lab/test_wheel_dte_constraints.py -v
```

---

## 4. Authoritative Specifications & Expected Output Derivation

| Requirement | Test File | Test Class / Function | Authoritative Source | Expected Output Derivation |
|:---|:---|:---|:---|:---|
| **R1** | `test_tier1_feature_coverage.py` | `TestR1OptionChainCaching` | `ORIGINAL_REQUEST.md § R1`, `PROJECT.md § Feature 2` | Contracts upserted into `cached_option_chains`; sorted `strike ASC`; `has_fresh_option_chain` returns `True` for $\ge 5$ records updated today. |
| **R2** | `test_tier1_feature_coverage.py` | `TestR2DeterministicSelection` | `ORIGINAL_REQUEST.md § R2`, `PROJECT.md § Feature 3, 4` | Selected put contract has delta in $[-0.22, -0.18]$ (closest to $-0.20$); `INTC`, `COIN`, `SO` staged in Mode 1 without filter rejection. |
| **R3** | `test_tier1_feature_coverage.py` | `TestR3MiddleGroundPricing` | `ORIGINAL_REQUEST.md § R3`, `PROJECT.md § Feature 5, 6` | `base = (mid + BS)/2`; `prem = base * 1.015`; quantized to $\$0.05/\$0.10$; `limit_price` persisted in `staged_trades`. |
| **R4** | `test_tier1_feature_coverage.py` | `TestR4HarvestAndMarginSizing` | `ORIGINAL_REQUEST.md § R4`, `PROJECT.md § Feature 7, 8` | Mode 1 harvest $\ge \$1,500$; account margin utilization $\le 75.0\%$; COIN single-position collateral accommodated. |
| **R5** | `test_tier1_feature_coverage.py` | `TestR5DialecticalArenaSync` | `ORIGINAL_REQUEST.md § R5`, `PROJECT.md § Feature 9, 10` | Trade-off matrix has `/ $1,500`; FA critique contains `~$375/slot`; active model rotation succeeds without unhandled crash. |
| **Boundaries** | `test_tier2_boundary_corner.py` | `TestTier2BoundaryAndCorners` | `PROJECT.md § Interface Contracts`, Exchange Standards | Cold vs warm cache; tick sizes $< \$3$ vs $\ge \$3$; exact $75.0\%$ vs $75.1\%$ margin rejection. |
| **Cross-Feature** | `test_tier3_cross_feature.py` | `TestTier3CrossFeature` | `PROJECT.md § Architecture` | Ingestion $\rightarrow$ Selection $\rightarrow$ Pricing $\rightarrow$ Staging full lifecycle; blotter dynamic sizing + 3-persona consensus. |
| **Real-World** | `test_tier4_real_world.py` | `TestTier4RealWorldScenarios` | `scripts/verify_middle_ground_pricing.py` | Full harvest blotter run; SQLite persistence in `staged_trades` and `cached_option_chains`. |
