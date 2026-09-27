# [SPEC-ARENA-001] Autonomous Multi-Agent Dialectical Fiduciary Arena

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Macro & Multi-Agent Architecture
- **Owning Modules**: `options_lab.api.weekly_intelligence`, `options_lab.api.main`

---

## 1. Purpose & Dialectical Philosophy
Options Lab deploys an institutional multi-agent dialectical committee where autonomous agents debate, challenge, and stress-test trade candidates before capital allocation. 

Rather than simple consensus voting, the system relies on **adversarial dialectical tension**:
- **Financial Analyst Agent**: Champions fundamental moat, valuation, and yield harvest opportunities.
- **Risk Aggregator Agent**: Defends the portfolio against tail-risk, margin exhaustion, and sector over-concentration.
- **Executive Allocator Agent**: Acts as the ultimate fiduciary gatekeeper, enforcing top-level monthly income targets.

---

## 2. Invariants

### `[SPEC-ARENA-001]`: Multi-Agent Persona Separation
- Each agent must maintain an independent evaluation rubric:
  - Financial Analyst: Focuses on earnings quality, moat, and 30-35 DTE sweet-spot premium.
  - Risk Aggregator: Evaluates margin headroom, 75% ceiling, 50% cash collateral, and contract sizing.
  - Allocator: Audits basket total against the top-level monthly dollar mandate.

### `[SPEC-ARENA-002]`: Top-Level Numeric Mandate Audit
- Before granting approval, the Allocator MUST sum the projected premium across all proposed trades:
  $$\text{Basket Harvest Total} = \sum_{i=1}^n (\text{Premium}_i \times 100 \times \text{Contracts}_i)$$
- The basket total is audited against the user's monthly income target (e.g. \$1,000 to \$1,500).

### `[SPEC-ARENA-003]`: Mandatory Dialectical Shortfall Challenge (`TARGET_SHORTFALL_CHALLENGE`)
- If the proposed candidates produce an aggregate deficit against the milestone target:
  1. The Allocator must issue an active challenge to the Financial Analyst: Questioning why sub-sweet spot candidates ($< \$2.00$ premium) were selected and interrogating alternative strikes or tickers.
  2. The Allocator must challenge the Risk Aggregator: Interrogating whether sizing can be scaled to 2 contracts within margin constraints.
- Status must be explicitly set to `TARGET_SHORTFALL_CHALLENGE`.

### `[SPEC-ARENA-004]`: Zero Silent Rubber-Stamping
- The desk is strictly forbidden from stamping "Approved" or "Golden Trade" on deficit portfolios without surfacing the explicit `TARGET_SHORTFALL_CHALLENGE` alert in the telemetry and UI.
- If risk constraints make reaching the target impossible, the Allocator must state its explicit dissent and document the exact trade-off.

### `[SPEC-ARENA-005]`: Dynamic 4D Macro Compass Calibration & 24h FRED Cache
- Macro telemetry (Fed Policy, Inflation/Yields, Liquidity, Volatility) updates dynamically.
- FRED series caching (`fred_macro_releases_latest`) strictly evaluates a 24-hour TTL:
  $$\text{Cache Valid} = (\text{now} - \text{timestamp}) < 86,400\text{ seconds}$$
- Multi-key fallback across `FRED_API_KEY`, `FRED_KEY`, and `settings.FRED_API_KEY` ensures uninterrupted macro indicators.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-ARENA-001]` | `options_lab/test_candidate_summary.py` | Verify distinct multi-agent personas present | PASS |
| `[SPEC-ARENA-002]` | `tests/test_dynamic_margin_sizing.py` | Verify basket harvest summation logic | PASS |
| `[SPEC-ARENA-003]` | `tests/test_dynamic_macro_calendar.py` | Verify TARGET_SHORTFALL_CHALLENGE triggered on deficit | PASS |
| `[SPEC-ARENA-004]` | `options_lab/test_candidate_summary.py` | Verify no silent rubber-stamping on shortfall | PASS |
| `[SPEC-ARENA-005]` | `tests/test_dynamic_macro_calendar.py` | Verify 24h FRED cache TTL and multi-key fallback | PASS |
