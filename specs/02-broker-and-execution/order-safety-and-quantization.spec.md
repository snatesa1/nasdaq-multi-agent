# [SPEC-SAXO-ORD-001] Order Safety, Tick Quantization & Sanitization

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Broker & Execution
- **Owning Modules**: `options_lab.api.saxo_client`, `options_lab.api.trade_staging`

---

## 1. Purpose & Scope
This specification governs exchange order safety invariants, tick size increment quantization, and trade blotter sanitization for all orders submitted to or retrieved from Saxo OpenAPI.

---

## 2. Invariants

### `[SPEC-SAXO-ORD-001]`: Mandatory Exchange Tick Size Quantization
- All proposed, staged, and submitted limit order prices must pass through `quantize_order_price()`.
- Floating continuous decimals (e.g. \$1.3372) are strictly prohibited.
- For options $\ge \$3.00$, tick increments standard is \$0.10 or \$0.05 per OCC rules or Saxo `TickSizeScheme`. For options $< \$3.00$, increments are \$0.05.
- The order price must satisfy:
  $$\text{quantized\_price} = \max\left(\text{tick}, \text{round}\left(\text{round}\left(\frac{P}{\text{tick}}\right) \times \text{tick}, 2\right)\right)$$

### `[SPEC-SAXO-ORD-002]`: Zero Theoretical Execution
- Staged trades and submitted limit orders must NEVER be priced using continuous theoretical models (e.g. raw Black-Scholes without market quote resolution).
- The desk must resolve live Bid/Ask/Mid/Spread via Saxo OpenAPI (`trade/v1/infoprices`) or authentic OPRA market feeds.

### `[SPEC-SAXO-ORD-003]`: Unexecuted Day Order Sanitization
- Trade blotters and performance stitchers must only aggregate authentic `Filled` / `Traded` executions and active `Working` orders.
- Unexecuted, cancelled, or expired draft day orders with \$0.00 price must NEVER be displayed as trade legs or aggregated into realized P&L calculations.

### `[SPEC-SAXO-ORD-004]`: Covered Call Physical Share Verification
- The staging engine must verify physical share ownership before approving a Covered Call (CC).
- Selling 1 CC contract requires owning at least 100 shares of the underlying stock. If fewer than 100 shares are held, the trade must be flagged as a Naked Call and blocked unless margin collateral supports it as a Cash-Secured or Naked write.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-SAXO-ORD-001]` | `options_lab/test_saxo_live.py` | `test_quantize_order_price_ticks()` | PASS |
| `[SPEC-SAXO-ORD-002]` | `options_lab/test_options_obb_validation.py` | Verify real quote resolution on staging | PASS |
| `[SPEC-SAXO-ORD-003]` | `tests/unit/test_trade_staging.py` | Verify expired/zero day orders excluded from blotter | PASS |
| `[SPEC-SAXO-ORD-004]` | `options_lab/test_trade_staging.py` | Verify Covered Call requires 100 shares held | PASS |
