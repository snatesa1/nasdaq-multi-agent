# [SPEC-SAXO-BAL-001] Account Balance & Collateral Resolution Protocol

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Broker & Execution
- **Owning Modules**: `options_lab.api.saxo_client`, `options_lab.api.margin_guardian`, `options_lab.api.main`

---

## 1. Purpose & Scope
This specification governs portfolio equity, cash availability, and collateral margin resolution across Options Lab. It ensures complete transparency of data lineage and prevents silent numeric fallbacks.

---

## 2. Invariants

### `[SPEC-SAXO-BAL-001]`: Zero Silent Numeric Defaults
- Code must NEVER stage trades, compute margin headroom, or display equity curves using hardcoded magic numbers (e.g. `$100000.0` or `$70000.0`).
- Every balance figure must originate from `resolve_account_balances()` with explicit provenance metadata attached.

### `[SPEC-SAXO-BAL-002]`: 5-Tier Resilient Resolution Hierarchy
Portfolio balances are resolved in strict prioritized waterfall order:
1. **Tier 1 (LIVE_BROKER)**: Live Saxo OpenAPI call (`/port/v1/balances/me`).
2. **Tier 2 (CACHED_BROKER)**: SQLite cache tables (`account_summary` and `balances`), valid if refreshed within TTL.
3. **Tier 3 (HISTORICAL_REPORT)**: Latest authentic ingested Saxo statement records in `saxo_reports`.
4. **Tier 4 (PORTFOLIO_HOLDINGS)**: Bottom-up aggregation of open position market values.
5. **Tier 5 (SIMULATED_BENCHMARK)**: Benchmark reference model (`DEFAULT_PORTFOLIO_EQUITY`), strictly tagged with `is_simulated = True`.

### `[SPEC-SAXO-BAL-003]`: Mandatory Provenance Transparency Badge
All balance endpoints and UI components must surface the provenance badge:
- `LIVE_BROKER` (Green): Real-time live broker data.
- `CACHED_BROKER` (Blue): Authenticated cache from SQLite.
- `HISTORICAL_REPORT` (Yellow): Statement-derived balance.
- `PORTFOLIO_HOLDINGS` (Purple): Calculated from active holdings.
- `SIMULATED_BENCHMARK` (Orange Alert): Benchmark fallback; execution disabled until authenticated.

### `[SPEC-SAXO-BAL-004]`: Available Collateral Headroom Calculation
Available headroom for selling options contracts must be strictly calculated as:
$$\text{Available Margin Headroom} = \max(0, (\text{Total Equity} \times 0.75) - \text{Current Margin Utilized})$$
$$\text{Available Cash Headroom} = \max(0, \text{Uninvested Cash} \times 0.50)$$

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-SAXO-BAL-001]` | `tests/unit/test_margin_guardian_capacity.py` | Verify exception or fallback raised if balances missing | PASS |
| `[SPEC-SAXO-BAL-002]` | `options_lab/test_saxo_live.py` | Verify 5-tier waterfall resolution executes in order | PASS |
| `[SPEC-SAXO-BAL-003]` | `tests/e2e/test_tier1_feature_coverage.py` | Verify provenance badge exists on balance payload | PASS |
| `[SPEC-SAXO-BAL-004]` | `options_lab/test_seasonality_and_collateral_caps.py` | Verify 75% margin / 50% cash ceiling formulas | PASS |
