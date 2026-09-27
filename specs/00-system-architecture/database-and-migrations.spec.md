# [SPEC-DB-001] SQLite Database Architecture & Migration Protocol

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Persistence & Storage
- **Owning Modules**: `options_lab.api.db`

---

## 1. Purpose & Engine Architecture
Options Lab utilizes an embedded, zero-maintenance SQLite database (`optionslab.db`) as its **Primary Single Source of Truth (SSOT)**.
- **Location**: `options_lab/api/data/optionslab.db` (configurable via `DB_DATA_DIR`).
- **Pragmas**:
  - `PRAGMA journal_mode = WAL` (Write-Ahead Logging for high-concurrency read/write).
  - `PRAGMA synchronous = NORMAL`.
  - `PRAGMA busy_timeout = 30000` (30-second lock resolution).
  - `PRAGMA foreign_keys = ON`.

---

## 2. Invariants

### `[SPEC-DB-001]`: Zero Breaking Schema Changes
- All schema evolution must be non-destructive.
- New columns must include safe defaults or allow `NULL`.
- Automated migrations or startup checks must wrap column additions in try/except blocks to prevent `sqlite3.OperationalError` (e.g. duplicate column errors).

### `[SPEC-DB-002]`: Strict Primary Table Taxonomy
The SQLite database houses the following foundational schemas:
1. `sessions`: Socratic tutor conversations and key learnings.
2. `portfolios` & `portfolio_tickers`: Watchlists, holdings, and real-time quotes.
3. `saxo_cache`: Live broker API response caching with TTL.
4. `broker_tokens`: Persistent OAuth 2.0 access & refresh tokens across container reboots.
5. `account_summary` & `balances`: Synchronized cash, margin, and total equity records.
6. `saxo_reports`: Audited trade blotters, filled orders, and monthly statements.
7. `briefing_cache`: Weekly macro intelligence briefs and dialetical arena summaries.
8. `audit_log`: Behavioral forensics, user interaction tags, and risk alerts.

### `[SPEC-DB-003]`: Multi-Tier Token Persistence
Broker OAuth tokens must persist across three redundant layers:
1. Primary: `broker_tokens` table in SQLite.
2. Secondary: Host-mounted `data/saxo_tokens.json`.
3. Tertiary: `.env` file fallback.

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Verification Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-DB-001]` | `tests/unit/test_socratic_session.py` | Verify session creation with new columns | PASS |
| `[SPEC-DB-002]` | `options_lab/test_api.py` | Verify DB tables initialize without error | PASS |
| `[SPEC-DB-003]` | `tests/unit/test_saxo_live.py` | Verify token persistence across reboots | PASS |
