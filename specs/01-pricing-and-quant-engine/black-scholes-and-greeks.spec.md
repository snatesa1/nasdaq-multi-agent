# [SPEC-QUANT-BS-001] Black-Scholes Analytical Pricing & Greeks Engine

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Quantitative Pricing Engine
- **Owning Modules**: `options_lab.engine.black_scholes`, `options_lab.engine.greeks`, `options_lab.api.main`

---

## 1. Purpose & Scope
This specification governs analytical European option pricing and first/second-order Greeks sensitivity computation in Options Lab.

---

## 2. Invariants

### `[SPEC-QUANT-BS-001]`: Boundary-Safe Expiry Valuation ($T \le 0$)
- When time to expiration $T \le 0$, the engine must not evaluate logarithmic or square-root terms.
- The engine must return the exact intrinsic value:
  $$\text{Call Price} = \max(0, S - K)$$
  $$\text{Put Price} = \max(0, K - S)$$
- All Greeks ($\Delta, \Gamma, \Theta, \nu, \rho$) must return $0.0$.

### `[SPEC-QUANT-BS-002]`: Standard Normal Distribution Precision
- The standard normal CDF $\Phi(x)$ utilizes the Abramowitz & Stegun (1964) approximation (formula 26.2.17) with maximum absolute error $\le 7.5 \times 10^{-8}$.
- Both $\phi(x)$ (PDF) and $\Phi(x)$ (CDF) must be cached with an LRU cache of at least 8,192 entries for high-throughput surface evaluation.

### `[SPEC-QUANT-BS-003]`: Analytical Greeks Standardization
All returned Greeks must adhere to standard institutional market conventions:
- **Delta ($\Delta$)**: Call $\in [0, 1]$, Put $\in [-1, 0]$.
- **Gamma ($\Gamma$)**: Identical for Call and Put; $\Gamma = \frac{\phi(d_1)}{S \sigma \sqrt{T}} \ge 0$.
- **Vega ($\nu$)**: Expressed per 1 percentage point change in volatility ($\sigma$): $\nu = \frac{S \sqrt{T} \phi(d_1)}{100}$.
- **Theta ($\Theta$)**: Expressed as decay per calendar day (annualized decay divided by 365.0).
- **Rho ($\rho$)**: Expressed per 1 percentage point change in risk-free rate ($r$): $\rho = \frac{\text{Term}}{100}$.

### `[SPEC-QUANT-BS-004]`: Strict Numeric Sanitization
- Volatility $\sigma$ must be positive ($\sigma > 0$). If $\sigma \le 0$, clamp to minimum floor $10^{-4}$.
- Spot price $S > 0$ and Strike price $K > 0$.

---

## 3. Mathematical Equations

$$d_1 = \frac{\ln(S / K) + (r + \frac{1}{2} \sigma^2) T}{\sigma \sqrt{T}}$$
$$d_2 = d_1 - \sigma \sqrt{T}$$

### European Call Price:
$$C(S, K, T, r, \sigma) = S \Phi(d_1) - K e^{-r T} \Phi(d_2)$$

### European Put Price:
$$P(S, K, T, r, \sigma) = K e^{-r T} \Phi(-d_2) - S \Phi(-d_1)$$

---

## 4. Verification & Traceability Matrix

| Invariant ID | Test File | Test Function | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-QUANT-BS-001]` | `options_lab/test_engine.py` | `test_black_scholes_zero_time()` | PASS |
| `[SPEC-QUANT-BS-002]` | `options_lab/test_engine.py` | `test_cdf_abramowitz_stegun_accuracy()` | PASS |
| `[SPEC-QUANT-BS-003]` | `options_lab/test_engine.py` | `test_analytical_greeks()` | PASS |
| `[SPEC-QUANT-BS-004]` | `options_lab/test_engine.py` | `test_invalid_inputs_sanitization()` | PASS |
