# [SPEC-WHEEL-001] Wheel Harvest Strategy & Strike Selection Engine

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Options Harvest & Margin
- **Owning Modules**: `options_lab.api.wheel_engine`, `options_lab.api.conviction_screener`

---

## 1. Purpose & Strategy Architecture
The Wheel Strategy is an institutional systematic yield-harvesting mechanism designed to generate steady, compounding cash flow through two complementary phases:
- **Phase 1 (Cash-Secured Put)**: Sell out-of-the-money puts on high-conviction mega-cap and large-cap leaders to collect premium.
- **Phase 2 (Covered Call)**: If assigned, sell out-of-the-money covered calls against the 100 acquired shares until called away at a profit.

---

## 2. Invariants

### `[SPEC-WHEEL-001]`: Two-Phase State Machine Integrity
- A trade recommendation must belong strictly to Phase 1 (`CSP`) or Phase 2 (`CC`).
- Phase 2 Covered Calls may only be staged if authentic share ownership ($\ge 100$ shares) is confirmed via Saxo OpenAPI holdings.

### `[SPEC-WHEEL-002]`: Sweet-Spot Premium Target
- Candidates should target a sweet-spot premium of **\$2.00 to \$3.00 per share** (\$200 to \$300 per contract) for optimal risk-adjusted yield.
- Premiums below \$1.00 are flagged as sub-optimal and trigger an explicit Allocator challenge.

### `[SPEC-WHEEL-003]`: Delta Selection Bounds (0.15 to 0.25 Delta)
- Strike selection for short puts must target an absolute Delta $|\Delta| \in [0.15, 0.25]$.
- This corresponds to an institutional **Probability of Profit (PoP) of 75% to 85%**.

### `[SPEC-WHEEL-004]`: DTE Horizon (30 to 45 Days)
- Option expiration dates must fall within 30 to 45 Days to Expiration (DTE).
- This window captures the steep acceleration in theta time decay while maintaining adequate gamma safety.

### `[SPEC-WHEEL-005]`: Quality Fundamental Moat
- Universe constituents must pass fundamental screening:
  - Market capitalization $> \$10\text{B}$.
  - Positive operating cash flow.
  - Debt-to-Equity $\le 2.0$.
  - Free Cash Flow Yield $> 0\%$.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-WHEEL-001]` | `options_lab/test_candidate_summary.py` | Verify CSP and CC strategy states | PASS |
| `[SPEC-WHEEL-002]` | `options_lab/test_candidate_summary.py` | Verify sweet-spot premium scoring | PASS |
| `[SPEC-WHEEL-003]` | `tests/test_dynamic_margin_sizing.py` | Verify strike selection within 0.15-0.25 Delta | PASS |
| `[SPEC-WHEEL-004]` | `options_lab/test_wheel_dte_constraints.py` | Verify 30-45 DTE expiration filtering | PASS |
| `[SPEC-WHEEL-005]` | `options_lab/test_candidate_summary.py` | Verify fundamental quality filters | PASS |
