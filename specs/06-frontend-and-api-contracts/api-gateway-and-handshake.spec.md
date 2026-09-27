# [SPEC-GW-001] API Gateway, Handshake & Anti-Hang Timeouts

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Frontend & API Contracts
- **Owning Modules**: `options_lab.frontend.src.lib.api`, `options_lab.api.main`

---

## 1. Purpose & Scope
This specification governs communication between the Next.js frontend client and the FastAPI backend gateway. It guarantees rapid failure recovery, dynamic port binding, and resilient network timeouts across local development, Docker containers, and remote VPN topologies.

---

## 2. Invariants

### `[SPEC-GW-001]`: Dynamic Base Resolver with Adaptive Discovery (`getApiBase()`)
- The frontend must dynamically resolve its backend base URL:
  - If `NEXT_PUBLIC_API_URL` is configured, prioritize it.
  - If running in browser on port 8000 (FastAPI static mount), use same-origin relative path `""`.
  - If running on port 3000 (Next dev server), target `http://${window.location.hostname}:8000`.
- In case of failure, an adaptive probe attempts a fallback to `http://${window.location.hostname}:8000`.

### `[SPEC-GW-002]`: Fast Pre-Flight Handshake & Immediate Short-Circuit
- Before initiating expensive workflows, the client executes a fast health check (`/api/health`) with an 8-second (or 3-second) timeout.
- If unreachable, the UI must immediately abort loading states and present an actionable recovery card displaying the restart command (`.\restart_backend.ps1`) and a 1-click retry button.
- The UI must NEVER be left hanging in an infinite spinner.

### `[SPEC-GW-003]`: Multi-Tiered Timeout Guards
- **Client-Side**: Every `apiRequest` MUST attach an `AbortController` timeout budget (30–35s for deep pipelines) to fail gracefully.
- **Server-Side**: Heavy multi-agent or macro orchestration endpoints must wrap async execution with `asyncio.wait_for(..., timeout=40.0)` with SQLite fallback.

### `[SPEC-GW-004]`: Dual `/api/` Route Decorators
- Every computational route must be registered with both standard and `/api/` prefixes:
  ```python
  @app.post("/price")
  @app.post("/api/price")
  ```
- This ensures seamless routing through Nginx SPA reverse proxies and Electron desktop containers.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-GW-001]` | `options_lab/frontend/src/lib/api.ts` | Verify dynamic host resolution logic | PASS |
| `[SPEC-GW-002]` | `options_lab/frontend/src/lib/api.ts` | Verify checkBackendHandshake abort signal | PASS |
| `[SPEC-GW-003]` | `tests/e2e/test_tier1_feature_coverage.py` | Verify timeout resilience under load | PASS |
| `[SPEC-GW-004]` | `options_lab/test_api.py` | Verify both /price and /api/price return 200 OK | PASS |
