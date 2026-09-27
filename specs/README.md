# 🏛️ Options Lab: Spec-Driven Architecture (SDD) Constitution

Welcome to the **Spec-Driven Architecture (SDD)** repository for **Options Lab**.

This directory (`specs/`) is the **Single Source of Truth (SSOT)** for all architectural, mathematical, execution, and user interface contracts governing Options Lab.

---

## 1. Core Principles

1. **Specification Precedes Implementation**: No feature, quant equation, API endpoint, or database column may be modified in code without an existing or updated specification.
2. **Immutable Invariant Tagging**: All non-negotiable requirements are codified with standardized tags in the format:
   `[SPEC-<DOMAIN>-<ID>]` (e.g. `[SPEC-MARGIN-001]`, `[SPEC-SAXO-002]`).
3. **Traceability by Default**: Every test in `tests/` maps directly to one or more `[SPEC-...]` tags.
4. **Strict Single Execution Engine**: Options Lab executes orders strictly via the **Live Saxo Desk Engine** ([`specs/02-broker-and-execution/saxo-execution-desk.spec.md`](file:///c:/Admin/Akpegis-Agent-Ecosystem/nasdaq-multi-agent/specs/02-broker-and-execution/saxo-execution-desk.spec.md)). No mock sandboxes or fictitious paper trade environments exist.
5. **Living Document Sync**: When the user requests a behavioral change, the specification is updated first (or concurrently), ensuring the spec never drifts from reality.

---

## 2. Directory & Pillar Structure

```
specs/
├── README.md                                  # This constitution and invariant index
│
├── 00-system-architecture/
│   ├── system-overview.spec.md               # [SPEC-SYS] Topology, ports, SQLite primary, offline-first
│   ├── process-guardian.spec.md              # [SPEC-PROC] Port scavenging, hot reload, zero-WSL pwsh rule
│   └── database-and-migrations.spec.md       # [SPEC-DB] SQLite schemas, migrations, versioning
│
├── 01-pricing-and-quant-engine/
│   ├── black-scholes-and-greeks.spec.md      # [SPEC-QUANT-BS] Pricing, Greeks, continuous vs discrete limits
│   ├── monte-carlo-and-gbm.spec.md           # [SPEC-QUANT-MC] Path simulation, antithetic variates
│   └── volatility-surface.spec.md            # [SPEC-QUANT-VOL] Smile calibration, root-finding tolerance
│
├── 02-broker-and-execution/
│   ├── saxo-execution-desk.spec.md           # [SPEC-SAXO-DESK] Strict single live execution engine, OAuth PKCE
│   ├── balance-and-collateral.spec.md        # [SPEC-SAXO-BAL] 5-tier balance resolution, provenance badge
│   └── order-safety-and-quantization.spec.md # [SPEC-SAXO-ORD] Tick quantization, day-order sanitization
│
├── 03-options-harvest-and-margin/
│   ├── wheel-harvest-engine.spec.md          # [SPEC-WHEEL] CSPs/CCs, strike selection, delta 0.15-0.25
│   ├── margin-guardian.spec.md               # [SPEC-MARGIN] 75% margin ceiling, 50% cash cap, 1-5 slot sizing
│   └── expiry-radar-and-rolls.spec.md        # [SPEC-ROLL] <=14 DTE radar, roll credit checks, replacements
│
├── 04-macro-and-multi-agent/
│   ├── macro-weekly-intelligence.spec.md     # [SPEC-MACRO] FRED 24h TTL, 4D Macro Compass dynamic scoring
│   └── dialectical-fiduciary-arena.spec.md   # [SPEC-ARENA] Allocator vs Analyst vs Risk, shortfall challenge
│
├── 05-behavioral-forensics-and-tutor/
│   ├── socratic-tutor.spec.md                # [SPEC-TUTOR] Socratic tutor session lifecycle, offline SQLite
│   └── behavioral-audit-blotter.spec.md      # [SPEC-AUDIT] Forensic trade tagging, emotional tilt detection
│
└── 06-frontend-and-api-contracts/
    ├── api-gateway-and-handshake.spec.md     # [SPEC-GW] 3s pre-flight handshake, dynamic base, anti-hang
    └── ui-design-and-theming.spec.md         # [SPEC-UI] Light theme hierarchy, live data binding
```

---

## 3. How to Update Specifications

### Method A: Conversational Direction (Recommended)
You state what you want to change in chat:
> *"Gemini, change the margin ceiling to 65% when VIX > 25, and change the roll horizon to 21 DTE."*

The agent will:
1. Locate `specs/03-options-harvest-and-margin/margin-guardian.spec.md` and `expiry-radar-and-rolls.spec.md`.
2. Update the invariant tags (`[SPEC-MARGIN-002]`, `[SPEC-ROLL-001]`).
3. Apply the changes to the Python/TypeScript codebase.
4. Run the automated compliance test suite to verify implementation.

### Method B: Direct Spec Editing
1. Directly open any `.spec.md` file in your editor.
2. Edit formulas, thresholds, or acceptance criteria.
3. In chat, say: *"Gemini, sync the codebase with the updated `specs/...`"*.
4. The agent will read the updated spec, update the code, and confirm tests pass.

---

## 4. Invariant Tag Registry

| Invariant Prefix | Pillar | Owning Module |
| :--- | :--- | :--- |
| `[SPEC-SYS-*]` | System Architecture | FastAPI / Docker / SQLite |
| `[SPEC-PROC-*]` | Process Guardian | `restart_backend.ps1` / pwsh |
| `[SPEC-DB-*]` | Database & Storage | `options_lab.api.db` |
| `[SPEC-QUANT-*]` | Pricing & Greeks Engine | `options_lab.engine.*` |
| `[SPEC-SAXO-*]` | Live Saxo Desk & Execution | `options_lab.api.saxo_*` |
| `[SPEC-MARGIN-*]` | Margin Guardian | `options_lab.api.margin_guardian` |
| `[SPEC-WHEEL-*]` | Wheel Harvest Engine | `options_lab.api.wheel_engine` |
| `[SPEC-ROLL-*]` | Expiry Radar & Rolls | `options_lab.api.weekly_intelligence` |
| `[SPEC-MACRO-*]` | Macro & FRED Series | `options_lab.api.weekly_intelligence` |
| `[SPEC-ARENA-*]` | Dialectical Arena | `options_lab.api.weekly_intelligence` |
| `[SPEC-TUTOR-*]` | Socratic Tutor | `options_lab.api.tutor` |
| `[SPEC-AUDIT-*]` | Behavioral Forensics | `options_lab.api.behavioral_forensics` |
| `[SPEC-GW-*]` | API Gateway & Handshake | `options_lab.frontend.src.lib.api` |
| `[SPEC-UI-*]` | UI Design & Theming | `options_lab.frontend.src.*` |
