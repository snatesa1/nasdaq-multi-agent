# [SPEC-SYS-001] System Architecture & Topology

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: System Architecture
- **Owning Modules**: `options_lab.api.main`, `options_lab.frontend.src.lib.api`, `docker-compose.yml`

---

## 1. Purpose & High-Level Architecture
Options Lab operates as a high-performance quantitative options analysis and automated execution ecosystem. It features:
- **FastAPI Backend (Port 8000)**: Serves computational options pricing, multi-agent dialectical synthesis, and authentic broker execution.
- **Next.js SPA Frontend (Port 3000)**: Serves an ultra-responsive, light-themed institutional dashboard.
- **Offline-First SQLite SSOT**: Primary database `optionslab.db` residing on local NVMe storage with WAL mode enabled.
- **Private Cloud Ingress**: Supports local LAN access (`192.168.0.8:3000`), Tailscale VPN, and Cloudflare Tunnels without cloud vendor lock-in.

---

## 2. System Invariants

### `[SPEC-SYS-001]`: Local SQLite is the 100% Primary Database
- Local SQLite (`optionslab.db`) is the primary, default storage engine for all persistence: tutor sessions, broker caches, blotters, staged orders, and token registries.
- Cloud databases (Firebase / Firestore) are strictly secondary opt-in overrides (`USE_FIRESTORE="true"`). The backend must boot and run fully offline with zero GCP or Firebase credentials.

### `[SPEC-SYS-002]`: Non-Breaking Shared API Contracts
- Shared Pydantic models in `options_lab/api/models.py` must maintain strict backward compatibility.
- New fields added to request schemas must provide default values or be typed as `Optional[T] = None`. Never require new identifiers on endpoints where existing frontend clients omit them.

### `[SPEC-SYS-003]`: Dual `/api/` Route Aliasing
- All backend routes exposed under `/price`, `/simulate`, `/greeks`, `/strategy`, `/broker`, `/weekly-intelligence` must also be decorated with their `/api/` prefix (e.g. `@app.post("/price")` and `@app.post("/api/price")`).
- This ensures single-port reverse-proxying through Nginx or Electron without route truncation.

### `[SPEC-SYS-004]`: Strict Single Live Saxo Desk Engine
- Options Lab maintains **zero simulated paper trading sandbox** or detached dummy order blotter.
- All order generation, chain discovery, and execution contracts bind directly to the authentic Saxo OpenAPI live desk with strict tick quantization and 2-step user confirmation.

---

## 3. Network Topology & Ports

| Service | Host Port | Protocol | Container Mount |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend** | `8000` | HTTP / WebSocket | `/app` (uvicorn hot reload) |
| **Next.js Frontend** | `3000` | HTTP | Nginx Alpine static export or Next dev server |
| **Local SQLite** | N/A | File I/O (`optionslab.db`) | Host-mounted NVMe volume (`:rw`) |

---

## 4. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-SYS-001]` | `tests/unit/test_socratic_session.py` | Verify session operations succeed with SQLite offline | PASS |
| `[SPEC-SYS-002]` | `options_lab/test_api.py` | Verify request schemas accept legacy payloads | PASS |
| `[SPEC-SYS-003]` | `tests/e2e/test_tier1_feature_coverage.py` | Verify `/api/health` and `/api/price` endpoints respond | PASS |
| `[SPEC-SYS-004]` | `tests/unit/test_saxo_live.py` | Verify live Saxo OpenAPI integration and tick quantization | PASS |
