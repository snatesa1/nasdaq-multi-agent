# [SPEC-TUTOR-001] Socratic Options Tutor & Session Persistence

- **Status**: Implemented & Verified
- **Version**: 1.0.0
- **Domain**: Behavioral Forensics & Education
- **Owning Modules**: `options_lab.api.tutor`, `options_lab.api.db`, `options_lab.api.main`

---

## 1. Purpose & Educational Architecture
The Socratic Tutor provides an institutional learning copilot embedded in Options Lab. It assists traders in mastering options theory, Greeks intuition, volatility surfaces, and risk management through guided Socratic inquiry.

---

## 2. Invariants

### `[SPEC-TUTOR-001]`: Local SQLite is the 100% Primary Storage Engine
- All tutor sessions, message histories, and key learnings must persist in the `sessions` table of `optionslab.db`.
- Cloud backends (Firestore) are strictly secondary opt-in overrides. The tutor must operate fully offline without external cloud credentials.

### `[SPEC-TUTOR-002]`: Non-Breaking Session Data Contract
- The session schema must maintain backward compatibility:
  - `id` (str, UUID)
  - `title` (str)
  - `created_at` (ISO timestamp)
  - `updated_at` (ISO timestamp)
  - `messages` (JSON serialized list of `{role, content, timestamp}`)
  - `key_learnings` (Optional[str], bulleted takeaways)
- Endpoints must accept session updates without requiring new mandatory identifiers.

### `[SPEC-TUTOR-003]`: Socratic Pedagogical Style
- The tutor must adhere to Socratic pedagogy:
  - It asks guiding, thought-provoking questions rather than lecturing.
  - It grounds explanations in the user's active portfolio positions or simulated scenario.
  - It reinforces mathematical rigor (e.g., distinguishing implied vs historical volatility).

---

## 3. Verification & Traceability Matrix

| Invariant ID | Test File | Test Assertion | Status |
| :--- | :--- | :--- | :--- |
| `[SPEC-TUTOR-001]` | `tests/unit/test_socratic_session.py` | Verify session operations succeed with SQLite offline | PASS |
| `[SPEC-TUTOR-002]` | `tests/unit/test_socratic_session.py` | Verify backward-compatible CRUD operations | PASS |
| `[SPEC-TUTOR-003]` | `options_lab/test_api.py` | Verify `/api/tutor/ask` returns Socratic response | PASS |
