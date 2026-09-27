# [SPEC-ROLL-001] Expiry Horizon Radar & Roll/Replacement Pipeline

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Options Harvest & Margin
- **Owning Modules**: `options_lab.api.weekly_intelligence`, `options_lab.api.margin_guardian`

---

## 1. Purpose & Scope
This specification governs proactive defense and capital recycling for expiring options positions. It identifies near-term expirations ($\le 14$ DTE) and stages automated roll and replacement actions to sustain uninterrupted compounding.

---

## 2. Invariants

### `[SPEC-ROLL-001]`: Near-Term Expiry Horizon Radar ($\le 14$ DTE)
- The desk must automatically scan all open short options positions with Days to Expiration $\le 14$ days.
- Positions outside this window ($> 14$ DTE) continue routine theta decay and are excluded from active roll staging.

### `[SPEC-ROLL-002]`: Dual Roll & Replacement Staging
For every expiring position, the desk must formulate two actionable choices:
1. **Direct Same-Ticker Roll**:
   - Rolled outward to the next monthly cycle (30–35 DTE).
   - Re-centered at $\sim 0.20 - 0.25$ Delta.
   - Must generate a **Net Credit** ($\text{New Premium} > \text{Buy-to-Close Cost}$).
2. **Cross-Sector Replacement Setup**:
   - High-conviction alternative ticker from an unassigned GICS sector.
   - Sized strictly within the collateral liberated by the expiring trade.

### `[SPEC-ROLL-003]`: Liberated Collateral Accounting
- The system must explicitly report the liberated cash collateral:
  $$\text{Liberated Collateral} = \text{Strike} \times 100 \times \text{Contracts}$$
- This liberated capacity must immediately be re-credited to `Remaining Collateral Headroom` in the planning blotter.

### `[SPEC-ROLL-004]`: Multi-Agent Roll Defense Rationale
- Each roll proposal must attach multi-agent consensus rationales:
  - **Financial Analyst**: Assignment probability and technical support levels.
  - **Risk Aggregator**: Margin neutrality and sector concentration.
  - **Allocator**: Net yield compounding rate and capital efficiency.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-ROLL-001]` | `tests/test_roll_replacement_radar.py` | Verify <=14 DTE detection | PASS |
| `[SPEC-ROLL-002]` | `tests/test_roll_replacement_radar.py` | Verify dual roll and replacement candidate generation | PASS |
| `[SPEC-ROLL-003]` | `tests/test_roll_replacement_radar.py` | Verify liberated collateral computation | PASS |
| `[SPEC-ROLL-004]` | `options_lab/test_candidate_summary.py` | Verify multi-agent consensus rationales on rolls | PASS |
