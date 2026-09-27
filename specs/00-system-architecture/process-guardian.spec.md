# [SPEC-PROC-001] Process Guardian & Windows Execution Protocol

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: System Execution & DevOps
- **Owning Modules**: `restart_backend.ps1`, `options_lab/api/main.py`

---

## 1. Purpose & Scope
This specification governs process execution, terminal runtime safety, and local development lifecycle in Options Lab.

---

## 2. Invariants

### `[SPEC-PROC-001]`: 100% Windows Native PowerShell (`pwsh`) Execution
- Windows Native PowerShell (`pwsh`) is the exclusive execution environment.
- Under zero circumstances may commands be directed to `wsl` or `wsl.exe`.
- Virtual environments must invoke `.\venv_win\Scripts\python.exe` or `python -m <module>`.

### `[SPEC-PROC-002]`: Orphan Port Scavenger
- Prior to launching tests or starting server instances on port `8000` or `3000`, any detached process bound to the target port must be identified and cleanly terminated via `Stop-Process`.
- Script standard: `.\restart_backend.ps1`.

### `[SPEC-PROC-003]`: Hot-Reload & Bytecode Purge
- Local Python FastAPI services must execute with `--reload` and `--reload-dir options_lab`.
- Bytecode caches (`__pycache__`) must be purged whenever model definitions or database schemas are altered.

### `[SPEC-PROC-004]`: Prohibition on Complex Inline Python in PowerShell
- Complex multiline Python strings containing `$` or nested double quotes must never be passed inline to `python -c` in PowerShell.
- All executions must utilize standalone test scripts or `python -m pytest` to prevent PowerShell variable interpolation and `ParserError`.

### `[SPEC-PROC-005]`: Decoupled Startup Pre-Warm (15s Anti-Contention Delay)
- Background pre-warmers (e.g., weekly macro intelligence briefing generation) must delay startup tasks by at least 15 seconds (`await asyncio.sleep(15)`).
- This guarantees the frontend UI, WebSocket handshakes, and account balance telemetry (`/api/broker/refresh`) execute without socket starvation or thread pool lock contention. Never run `force_refresh=True` on startup.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File / Artifact | Verification Mechanism | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-PROC-001]` | PowerShell runtime environment | Native execution in pwsh terminal | PASS |
| `[SPEC-PROC-002]` | `restart_backend.ps1` | `Get-NetTCPConnection -LocalPort 8000 \| Stop-Process` | PASS |
| `[SPEC-PROC-005]` | `options_lab/api/main.py` | `startup_event()` contains 15s non-blocking sleep | PASS |
