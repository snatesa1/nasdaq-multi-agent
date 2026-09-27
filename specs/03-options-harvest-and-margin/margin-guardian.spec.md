# [SPEC-MARGIN-001] Margin Guardian & Capital Collateral Specification

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Options Harvest & Margin
- **Owning Modules**: `options_lab.api.margin_guardian`, `options_lab.api.main`

---

## 1. Purpose & Scope
This specification governs institutional portfolio margin protection, cash collateral limits, and dynamic candidate capacity sizing in Options Lab.

---

## 2. Invariants

### `[SPEC-MARGIN-001]`: 75.0% Portfolio Margin Ceiling
- The cumulative account margin utilization across all open and proposed option positions must NEVER exceed 75.0% of total portfolio equity:
  $$\text{Margin Utilization} = \frac{\text{Current Margin Used} + \text{Synthetic Basket Margin Impact}}{\text{Total Equity}} \le 0.75$$
- If projected utilization $> 75.0\%$, the candidate must be rejected with status `MARGIN_LIMIT_EXCEEDED`.

### `[SPEC-MARGIN-002]`: 50.0% Available Cash Collateral Cap
- Total cumulative cash collateral committed to Cash-Secured Puts (CSPs) must not exceed 50.0% of available uninvested cash buffer:
  $$\text{Cumulative Collateral} = \sum (\text{Strike}_i \times 100 \times \text{Contracts}_i) \le (\text{Available Cash} \times 0.50)$$
- If exceeded, the candidate is blocked with status `COLLATERAL_LIMIT_EXCEEDED`.

### `[SPEC-MARGIN-003]`: Dynamic Sizing Capacity (1 to 5 Candidates)
- The harvest desk dynamically sizes the candidate count between 1 and 5 positions strictly based on available collateral headroom:
  $$\text{Remaining Headroom} = \max(0, (\text{Total Equity} \times 0.75) - \text{Current Margin Used})$$
- If headroom is insufficient for 4 or 5 trades, the desk stages only 1, 2, or 3 trades that safely fit without breaching the ceiling.

### `[SPEC-MARGIN-004]`: Cumulative Basket Audit (`validate_cumulative_basket`)
- Every proposed trade must be audited in the context of the entire active basket before staging.
- The evaluation must return exact remaining headroom, projected margin %, and granular rejection reasons if non-compliant.

### `[SPEC-MARGIN-005]`: Sector Concentration Ceiling
- In Mode 1 (Multi-Sector Harvest), no single GICS sector may exceed 1 staged candidate or 2 total contracts to prevent correlated drawdowns.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-MARGIN-001]` | `tests/unit/test_margin_guardian_capacity.py` | Verify 75% margin ceiling enforces rejection | PASS |
| `[SPEC-MARGIN-002]` | `options_lab/test_seasonality_and_collateral_caps.py` | Verify 50% cash collateral cap formula | PASS |
| `[SPEC-MARGIN-003]` | `tests/test_dynamic_margin_sizing.py` | Verify dynamic slot scaling between 1 and 5 trades | PASS |
| `[SPEC-MARGIN-004]` | `options_lab/test_candidate_summary.py` | Verify cumulative basket validation | PASS |
| `[SPEC-MARGIN-005]` | `options_lab/test_seasonality_and_collateral_caps.py` | Verify GICS sector concentration limit | PASS |
