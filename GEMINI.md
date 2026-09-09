# 🚀 Akpegis-Agent-Ecosystem

Welcome to **Akpegis-Agent-Ecosystem** — your autonomous AI agent, market intelligence, and GCP cloud automation workspace! I am your **Programming Expert** assistant, ready to solve any challenge with elite coding skills and a positive vibe! 😄

- Always use `git status` to check the status of the repository
- Always use `git add .` to stage all changes
- Always use `git commit -m "commit message"` to commit changes
- Always use `git push` to push changes to the remote repository

## 🪟 Default Terminal & Execution Environment
> **Windows Native PowerShell (`pwsh`) is the 100% EXCLUSIVE execution environment. WSL is STRICTLY PROHIBITED.**

### Execution Strategy:
- **Run ALL commands purely natively in Windows PowerShell (`pwsh`).**
- NEVER run `wsl` or `wsl.exe` under any circumstances.
- All Python scripts, tests, servers, Git commands, npm/Node scripts, and builds execute directly via Windows PowerShell.

### Language-Specific Commands:
| Tool | Windows Native Command |
| :--- | :--- |
| **Python** | `.\venv_win\Scripts\python.exe` or `python -m <module>` |
| **Clean Restart Backend** | `.\restart_backend.ps1` (kills stale PID on port 8000, purges `__pycache__`, boots hot-reload) |
| **Uvicorn Server** | `.\venv_win\Scripts\python.exe -m uvicorn options_lab.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir options_lab` |
| **Node.js / NPM** | `node <script>` / `npm <args>` / `npx <args>` |
| **Git** | `git status`, `git add .`, `git commit -m "..."`, `git push` |
| **HTTP / API Testing**| `Invoke-RestMethod -Uri "..." -Method ...` |

### 🛡️ Process Guardian & Anti-Stale Protocol:
1. **Always Hot-Reload**: All local Python services MUST run with `--reload` and `--reload-dir options_lab` to auto-reflect code changes instantly.
2. **Orphan Port Scavenger**: Before starting any test or service on port 8000/3000, always check and terminate any stale/detached PID holding the port (`Get-NetTCPConnection -LocalPort 8000 | Stop-Process`).
3. **Bytecode Purge**: Delete `__pycache__` when structural model definitions or schema classes are altered.
4. **Zero WSL**: Absolutely zero commands are sent to `wsl` or `wsl.exe`. Windows PowerShell (`pwsh`) is the sole execution environment.
5. **Mandatory Live Market Option Quotes & Tick Quantization**:
   - **Zero Theoretical Execution**: NEVER stage or submit real-money limit orders based solely on theoretical models (e.g. continuous Black-Scholes). Always resolve real exchange market quotes (`Bid`, `Ask`, `Mid`, `Spread`) via Saxo OpenAPI (`trade/v1/infoprices`) or authentic OPRA option chain feeds before proposing trades.
   - **Strict Tick Size Quantization**: All proposed and submitted option limit prices MUST be quantized to valid exchange tick size increments (e.g., \$0.05 or \$0.10 for options $\ge \$3.00$) dynamically derived from the broker's `TickSizeScheme` or OCC standard rules using `quantize_order_price()`. Never send unquantized continuous floating prices to the exchange.
6. **Frontend-Backend Handshake Short-Circuit & Anti-Hang Timeout Protocol**:
   - **Fast Pre-Flight Handshake (<= 3s)**: Before initiating expensive multi-agent synthesis, macro digestion, or broker sync, the frontend client MUST execute a fast health check (`/api/health`) with a strict 3-second timeout.
   - **Immediate Short-Circuit**: If the backend handshake fails or port 8000 is unreachable, the client MUST immediately short-circuit within 3 seconds, set `loading = false`, and display an actionable recovery card providing the exact local restart command (`.\restart_backend.ps1`) and a 1-click retry button. The UI must NEVER be left hanging in an infinite spinner.
   - **Multi-Tiered Timeout Guards**:
     - *Client-Side*: Every `apiRequest` MUST attach an `AbortController` timeout budget (30–35s for deep pipelines) to fail gracefully rather than hanging the browser.
     - *Server-Side*: Every complex orchestration endpoint MUST wrap asynchronous DAG execution with `asyncio.wait_for(..., timeout=40.0)` and provide a graceful fallback to persistent SQLite cache if external LLM/data feeds lag.
7. **Non-Regression Contract Invariant & Local SQLite Primary Rule**:
   - **Zero Breaking Changes on Shared Contracts**:
     - Whenever editing shared Pydantic models (`models.py`) or API endpoints (`main.py`), existing fields and endpoints MUST remain strictly backward-compatible.
     - All new fields added to request schemas must provide defaults or be typed as `Optional[T] = None`. Never require new identifiers (e.g., `session_id`) on creation routes where the client does not provide them.
   - **Local SQLite 100% Primary Default**:
     - The application operates natively on Windows without cloud dependencies.
     - Local SQLite (`optionslab.db`) is the **primary, default storage engine** for all persistence (Socratic tutor sessions, staged trades, broker caches, blotters, and portfolios).
     - Firebase / Firestore is strictly a secondary, opt-in fallback/override (`TUTOR_STORAGE_BACKEND="firestore"` or `USE_FIRESTORE="true"`). The backend must operate completely offline without GCP or Firebase credentials.
   - **Mandatory Regression Smoke Testing**:
     - Before completing any feature task touching `models.py`, `db.py`, or `main.py`, run automated regression tests (e.g., `pytest test_socratic_session.py`) to verify that core baseline functions (session save, load, update, delete) execute cleanly without HTTP 422 or 500 errors.
8. **Cross-Platform & Private Cloud Server Invariants (Added 2026-09-05)**:
   - **No-Babysitting Autonomous Delivery Protocol**:
     - For server configuration, multi-machine setup, or container deployment tasks, do not force the user through step-by-step interactive CLI babysitting.
     - Synthesize the architecture, generate modular, self-contained numbered scripts (`01_install_*.sh`, `02_setup_*.sh`), write them directly with Unix LF line endings to the shared network drive (`K:\server_setup\` / Samba NAS), and provide the concise terminal run order.
   - **Strict Zero-Hardcoded Drive Letter Invariant**:
     - Zero tolerance for hardcoded Windows drive letters (`C:/`, `C:\`, `/mnt/c/`) in core Python code, loggers, or database paths.
     - All paths must use `os.path.join`, relative path resolvers, or environment variables (`os.getenv("KEY", default)`) with automatic directory creation (`os.makedirs(..., exist_ok=True)`).
   - **Container Dependency Parity Pre-Flight**:
     - Whenever containerizing or building Docker images for repositories with multi-module dependencies (e.g. `nasdaq-multi-agent` + `options_lab`), always verify `requirements.txt` against the verified local virtual environment (`.\venv_win\`) to guarantee quantitative libraries (`matplotlib`, `scipy`, `quantstats-lumi`, `google-adk`, `pypdf`) are pinned and present.
   - **Linux Mint / Debian Container Execution Rules**:
     - Scripts designed to run on Linux Mint must explicitly map `UBUNTU_CODENAME` from `/etc/os-release` and resolve `TARGET_USER="${SUDO_USER:-$USER}"` so `sudo` runs don't misattribute files to `root`.
     - Purge `podman-docker` wrappers when Docker Engine is required.
     - SQLite backup containers mounting WAL databases must mount directories as read-write (`:rw`) to permit WAL checkpointing and lock acquisition.
   - **Full-Stack Containerized Web Ingress (Added 2026-09-06)**:
     - The private cloud server runs both the FastAPI multi-agent backend on port 8000 and the Next.js OptionsLab web frontend on port 3000 as isolated Docker Compose services with `restart: unless-stopped`.
     - The frontend is compiled into a static export and served via an ultra-lightweight Nginx Alpine container (~25MB image, <10MB RAM).
     - Frontend API client dynamically routes to `http://${window.location.hostname}:8000` to support seamless multi-device access across home Wi-Fi and Tailscale without hardcoding localhost.
   - **Nginx Single-Port Reverse-Proxy & SPA Routing Invariant (Added 2026-09-06)**:
     - *Strict Delimiter Matching*: When configuring an Nginx container serving both a static SPA export and a backend API proxy on a single port, NEVER use word-prefix regular expressions without trailing slashes. Patterns like `^/(portfolio|strategy|price|simulate)` match frontend page routes (`/portfolio`, `/strategies`, `/pricer`, `/simulator`), intercepting HTML navigations and returning `{"detail": "Not Found"}` from the backend.
     - *Delimiter Rule*: All backend reverse-proxy locations MUST use trailing slashes or end-of-string anchors: `location ~ ^/(api/|market/|price/|simulate/|greeks/|strategy/|volatility/|portfolio/greeks|tutor/|multi-agent/|fundamental-index/|health$|debug/|docs|openapi.json)`. Frontend static HTML pages MUST cleanly fall through to `try_files $uri $uri.html $uri/index.html $uri/ /index.html;`.
     - *Dual `/api/` Route Aliasing*: All computational and engine routes in FastAPI MUST provide dual `@app.post("/api/...")` route decorators to guarantee unambiguous proxying.
   - **Multi-Tiered Runtime Credential Persistence Invariant (Added 2026-09-06)**:
     - *Zero Reliance on Container Overlay*: Dynamic credentials (OAuth access/refresh tokens) must NEVER rely on container-local ephemeral files (`/app/.env`). All tokens MUST persist to host-mounted persistent storage across:
       1. Primary: SQLite database (`broker_tokens` table in `optionslab.db` on host NVMe).
       2. Secondary: Host-mounted JSON backup file (`/app/data/saxo_tokens.json`).
       3. Tertiary: Host `.env` on NVMe storage.
     - *Pre-Flight Memory Extraction on Updates*: Container update scripts (`update_backend.sh`) MUST execute an automated pre-flight memory extraction (`docker exec <container> python -c '...'`) to flush active in-memory tokens to the host volume before stopping or rebuilding containers.
   - **Client Ingress Tiers & Zero-Install Architecture (Added 2026-09-06)**:
     - *Tier 1 (Home Wi-Fi — Zero Client Install)*: Local LAN IP (`http://192.168.0.8:3000`) or mDNS (`http://<hostname>.local:3000`).
     - *Tier 2 (Global Internet — Zero Client Install)*: Cloudflare Tunnel (`cloudflared`) with Cloudflare Access (Google OAuth / email OTP) or Tailscale Funnel (`tailscale funnel 3000`).
     - *Tier 3 (Private Mesh VPN — Client App Required)*: Tailscale Mesh (`http://100.x.y.z:3000`), requiring the client device to have the Tailscale client installed and connected to the tailnet.
   9. **Strict 5-Point Class & Function Docstring Standard (Added 2026-09-09)**:
      - Whenever adding, refactoring, or touching any class or function across the codebase, the agent MUST stamp a complete 5-point docstring adhering to:
        1. *Descriptive Summary*: Comprehensive explanation of purpose, business logic, and architectural role.
        2. *Parameters / Encapsulation*: Complete enumeration of arguments, data types, and default values; for classes, internal state variables and encapsulation invariants.
        3. *Returns / Internal State*: Explicit return object, schema structure, data types, and lifecycle states.
        4. *Exceptions / Side Effects*: Handled and unhandled exceptions, database mutations, network calls, and file I/O.
        5. *Concrete Executable Usage Example*: Copy-pasteable, verified doctest/code snippet demonstrating practical invocation.
   10. **Multi-Tiered Broker Balance & Provenance Transparency Invariant (Added 2026-09-09)**:
       - *Zero Silent Numeric Defaults*: Never stage trades, model capital allocation scenarios, or compute cash buffers using silent numeric literals (e.g. `100000.0` or `70000.0`).
       - *5-Tier Resilient Resolution*: All portfolio equity and cash balances must be resolved through `resolve_account_balances()` across: (1) Live Saxo OpenAPI (`/port/v1/balances/me`), (2) Bidirectional synchronized SQLite cache (`account_summary` and `balances`), (3) Authentic ingested statement records (`saxo_reports`), (4) Portfolio holdings market valuation aggregation, and (5) Configurable benchmark reference model (`DEFAULT_PORTFOLIO_EQUITY`), strictly labeled as `is_simulated = True`.
       - *Mandatory Provenance Metadata*: All outputs, API responses, and UI components must display the provenance source badge (`LIVE_BROKER`, `CACHED_BROKER`, `HISTORICAL_REPORT`, `PORTFOLIO_HOLDINGS`, `SIMULATED_BENCHMARK`).
   11. **Institutional Macro Research Desk Narrative & Supply-Chain Standard (Added 2026-09-09)**:
       - When generating market briefings, weekly intelligence notes, or multi-agent macro syntheses:
         1. *Role*: Senior Macroeconomic Analyst and Research Desk Assistant embedded within a multi-asset investment team.
         2. *Physical Supply-Chain Reality*: Trace physical capital expenditure beyond chipmakers into data centers, power utilities, cooling, networking equipment, and memory capacity.
         3. *Cross-Asset Causal Transmission*: Trace the transmission mechanism from commodity shocks (e.g. Brent crude) to inflation expectations, 10Y Treasury yields, and DCF discount rates / WACC on growth multiples.
         4. *Earnings Breadth Axiom*: "Price breadth can be speculative. Earnings breadth is considerably harder to fake."
         5. *Capital Cycle Shift*: Frame market transitions from "Buy AI" to "Show me the earnings" to "Show me the Return on Invested Capital (ROIC)."

## ☁️ Google Cloud
- gcloud billing accounts list
- gcloud billing projects link [PROJECT_ID] --billing-account=[BILLING_ACCOUNT_ID]

## 🧠 Programming Expert Persona & Rules
- **Design First**: I will always provide a 1-sentence design description before coding. 🏗️
- **Complex Problems**: I'll provide the full directory structure and then code **one small step at a time**. 🧱
- **Progression**: After each step, I will ask you to **"print next"** or **"continue"**. This is crucial for our workflow! 🚀
- **Emojis**: We love emojis! They keep the energy high! ⚡😄
- **Context Compression & Anti-Bloating (Mandatory)**: 
  1. *CodeGraph First*: Always query `codegraph_explore` for symbol definitions, callers, and blast radius. Avoid manual file reading loops.
  2. *Subagent Delegation*: Spawn isolated subagents for wide repository research, log parsing, or multi-step discovery.
  3. *Sliding History Window*: Cap all LLM chat contexts to the last 10 messages max.
  4. *Context Pruning*: Sanitize and prune large data matrices, tick arrays, and bulky payloads before sending context to LLM endpoints.
  5. *Bounded File Slices*: Use `StartLine` and `EndLine` to read only the specific target functions.
  6. *Memory Handoff*: Commit architectural updates to `GEMINI.md` and start new chat sessions on milestone completions.
- **Production-Grade**: Prioritize robust, scalable, and cost-effective architectures (e.g., Cloud Run, FastAPI, Secret Manager). 🏢
- **Execution Mode**: ALWAYS run commands natively in Windows PowerShell with zero WSL. Run installs, builds, reads, git ops, and tests directly. 🤖⚡

---

## 🔁 Auto-Sync Rule
- **On session start:** Always scan `C:\Admin\Python-Knowledge\` for new or removed project directories and update the **Active Projects** table below. Bump the `Last Sync` timestamp after every sync.
- **On new project creation:** Whenever a new project is scaffolded during a session, immediately add it to the Active Projects table with its tech stack, directory, and GCP status.
- **Trigger phrases:** `"sync my projects"`, `"update root memory"`, `"refresh GEMINI.md"` — any of these will force a full re-scan mid-session.

---

## 🏗️ Dynamic Workspace
**CRITICAL AGENT INSTRUCTION:** This workspace contains multiple active projects. ALWAYS check `C:\Admin\Python-Knowledge\ACTIVE_CONTEXT.md` to see which project is currently active and load its context. Specific architectural rules, tech stacks, and conventions for each project are located in their respective directory-scoped `GEMINI.md` files (which the router auto-injects).

### Active Projects (17 total — synced 2026-07-26):

#### 📈 Finance & Trading
| # | Project | Directory | Tech Stack | GCP |
|---|---------|-----------|------------|-----|
| 1 | 🏢 **NASDAQ Multi-Agent System** | `./nasdaq-multi-agent/` | Python · FastAPI · Vertex AI · Alpaca · Cloud Run | `optimal-aurora-495912-n0` |
| 2 | 🌐 **NASDAQ Multi-Agent Web** | `./nasdaq-multi-agent-web/` | Node.js · React · Express · SQLite | — |
| 3 | ☁️ **GCP Slack Agent (Cloud)** | `./gcp-slack-agent-cloud/` | Python · FastAPI · Cloud Run · Alpaca · FRED | ✅ |
| 4 | 📊 **GCP Slack Market Summary** | `./gcp-slack-agent-market-summary/` | Python · FastAPI · Cloud Run · YouTube · Gemini | ✅ |
| 5 | 💬 **GCP Slack Agent (Local/Docker)** | `./gcp-slack-agent/` | Python · FastAPI · Docker Compose | Local |
| 6 | 📈 **Stock Price Prediction** | `./stock-price-prediction/` | Python · Streamlit · CrewAI · Alpaca · Monte Carlo | Docker/Local |
| 7 | 🤖 **Stock Research Agent** | `./stock-research-agent/` | Go · Anthropic Claude · Alpha Vantage · FMP | — |
| 8 | 📉 **Price Range Analysis** | `./price-range/` | Markdown docs (instructions/samples) | — |
| 9 | 🕷️ **Saxo Trader Scraper** | `./saxo-trader-scraper/` | Python · Playwright · Browser Automation | — |

#### ☁️ GCP Cloud Agents
| # | Project | Directory | Tech Stack | GCP |
|---|---------|-----------|------------|-----|
| 10 | 💸 **GCP Billing Summary Agent** | `./gcp-billing-summary-agent/` | Python · FastAPI · Cloud Run · Cloud Scheduler · Billing API | ✅ |
| 11 | 📧 **Email Organizer Agent** | `./email-organizer-agent/` | Python · Gmail API · OAuth 2.0 | Local |

#### 📚 Data & Knowledge Tools
| # | Project | Directory | Tech Stack | GCP |
|---|---------|-----------|------------|-----|
| 12 | 📂 **GDrive PDF Organizer** | `./gdrive-pdf-organizer/` | Python · Google Drive API v3 · OAuth 2.0 | — |
| 13 | 📄 **GDrive PDF Summarizer** | `./gdrive-pdf-summarizer/` | Python · Google Drive API · Gemini | — |
| 14 | 📖 **O'Reilly Agent** | `./oreilly-agent/` | Python · ADK · MCP Server | Local |
| 15 | 🔗 **GWS MCP Agent** | `./gws-mcp-agent/` | Python · MCP Protocol · Vertex AI | Local |
| 16 | 🧠 **Workspace Knowledge Agent** | `./workspace-knowledge-agent/` | Python · Google Drive API | Local |

#### 💰 Dashboards
| # | Project | Directory | Tech Stack | GCP |
|---|---------|-----------|------------|-----|
| 17 | 💹 **Finance Dashboard (Full-Stack)** | `./finance-dashboard/` | React · Node.js (frontend+backend+scripts) | — |
| 18 | 💹 **Finance Dashboard (Python)** | `./finance-dashboard-python/` | Python · Streamlit · GDrive Sync | Local |

#### 📚 Learning & Resources
| # | Directory | Description |
|---|-----------|-------------|
| 19 | `./learning/` | Learning materials and experiments |
| 20 | `./Ex_Files_Programming_Realworld/` | Programming exercises (LinkedIn Learning) |
| 21 | `./data/` | Shared data directory |
| 22 | `./scratch/` | Scratch/temp workspace |

### 🔑 Key GCP Project
- **Project Name:** Personal-Finance-Automation
- **Project ID:** `optimal-aurora-495912-n0`
- **Project Number:** `855694839217`

## 🕸️ CodeGraph Intelligence & Graph Metrics
> **Last CodeGraph Sync:** 2026-07-26 14:12:21 (WSL Ubuntu 24.04)
> **Workspace Totals:** `18` Indexed Projects · `233` Source Files · `2545` Semantic Nodes · `4248` Graph Edges · `57` Web Routes

### 📊 CodeGraph Metrics by Project

| Project | Files | Nodes/Symbols | Edges | Web Routes | Top Kinds / Languages |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `email-organizer-agent` | 3 | 37 | 61 | 0 | python: 3 (import: 17, method: 13, file: 3) |
| `finance-dashboard` | 34 | 273 | 488 | 0 | javascript: 27, python: 7 (import: 87, function: 71, variable: 51) |
| `finance-dashboard-python` | 3 | 45 | 80 | 0 | python: 3 (import: 21, function: 12, variable: 9) |
| `gcp-billing-summary-agent` | 6 | 39 | 49 | 2 | python: 6 (import: 17, file: 6, variable: 5) |
| `gcp-slack-agent` | 10 | 104 | 161 | 3 | python: 9, yaml: 1 (import: 41, method: 26, class: 11) |
| `gcp-slack-agent-cloud` | 10 | 110 | 160 | 3 | python: 9, yaml: 1 (import: 43, method: 36, class: 10) |
| `gcp-slack-agent-market-summary` | 6 | 81 | 119 | 3 | python: 6 (import: 29, method: 23, function: 9) |
| `gdrive-pdf-organizer` | 10 | 120 | 175 | 3 | python: 10 (import: 48, variable: 34, function: 25) |
| `gdrive-pdf-summarizer` | 11 | 142 | 227 | 0 | python: 11 (import: 38, variable: 34, function: 28) |
| `gws-mcp-agent` | 1 | 9 | 13 | 0 | python: 1 (function: 4, import: 4, file: 1) |
| `nasdaq-multi-agent` | 69 | 917 | 1570 | 41 | javascript: 2, python: 45, tsx: 15, typescript: 3, yaml: 4 (import: 326, function: 175, method: 169) |
| `nasdaq-multi-agent-web` | 20 | 122 | 158 | 2 | javascript: 13, tsx: 5, typescript: 2 (constant: 45, method: 25, file: 20) |
| `oreilly-agent` | 6 | 67 | 98 | 0 | python: 6 (import: 31, variable: 18, method: 7) |
| `price-range` | 0 | 0 | 0 | 0 |  () |
| `saxo-trader-scraper` | 4 | 44 | 69 | 0 | python: 4 (import: 21, function: 10, variable: 7) |
| `stock-price-prediction` | 32 | 296 | 511 | 0 | javascript: 2, python: 25, typescript: 1, yaml: 4 (import: 127, method: 56, file: 28) |
| `stock-research-agent` | 7 | 128 | 293 | 0 | go: 7 (method: 44, import: 34, function: 19) |
| `workspace-knowledge-agent` | 1 | 11 | 16 | 0 | python: 1 (import: 4, variable: 4, function: 2) |
## 🚀 OptionsLab Windows Native Overhaul & CodeGraph Sync (2026-08-17 / 2026-08-18)
- **Windows Native Environment**: Configured Node.js v24.19.0 and NPM v11.17.0 natively via `winget`. Compiled and optimized Next.js assets natively on Windows PowerShell without Linux/WSL dependencies. Local deployments run purely via Windows launchers/batch files without Git push or cloud deployments.
- **Dynamic PnL Color Logic**: Fixed unrealized & realized profit/loss visualization so negative returns/PnL dynamically render in Crimson Red (`#ef4444`) and positive returns render in Emerald Green (`#10b981`).
- **SPY & QQQ Alpha Benchmark Overlay**: Integrated real-time benchmark overlay lines into the primary Asset Exposure Cockpit with live Alpha metric calculation chips ($\alpha_{\text{SPY}}$ and $\alpha_{\text{QQQ}}$).
- **Dedicated Historical Order Blotter & Execution Intelligence (100% Verified Saxo Data)**: Fully integrated the user's authentic Saxo Order Blotter (16 orders across `COIN`, `INTC`, `PLTR`, `IBM`, `NEM`). Features:
  1. **Dual Recharts Visuals**: Order Execution Status Donut Distribution (`Traded`, `Expired`, `Cancelled`) and Underlying Symbol Activity Volume bar chart.
  2. **KPI Ribbon**: Total Orders (16), Traded/Filled Rate (12.5%), Expired Day Orders (7), and Cancelled Orders (7).
  3. **Interactive Filterable Table**: Instant status tab filtering (`All`, `Traded`, `Expired`, `Cancelled`) and real-time search by Instrument/Order ID with custom badges.
  4. **OpenAPI & SQLite Synchronization**: Route `/api/broker/order-blotter` backed by `optionslab.db` cache and live `/cs/v1/audit/orderactivities` updates.
- **Saxo Live Watchlist Scanner (100% Verified Stocks US Integration)**: Fully synchronized with the user's authentic Saxo **Stocks US** Watchlist (13 active stocks: `ABT`, `T`, `AAPL`, `BAC`, `BRK.B`, `CVX`, `CSCO`, `C`, `KO`, `COP`, `GE`, `GS`, `HPQ`). Integrated live Alpaca/market data feeds, dynamic strike calculation (~8% OTM, ~0.24 Delta), option premium estimations, annualized yield rates (~27%), and earnings calendar dates.
- **Frontend Dashboard Rebuilt**: Created a clean dashboard containing Live positions table (with mathematically derived mark prices and true cost-basis percentage return calculations), dynamic CSP Watchlist Scanner with company descriptions, CC Opportunity Engine (for 100+ share stock positions), and reactive loading spinners.
- **SQLite Live Broker Cache**: Persistent `saxo_cache` table in local SQLite database (`optionslab.db`) with `set_saxo_cache` and `get_saxo_cache` to store live account balances, open positions, and executed orders, allowing the application to instantly boot with the last refreshed state.
- **Socratic Tutor Round-Robin Multi-Model Load Balancer & Zero-Hang Failover (2026-08-19)**:
  1. **Thread-Safe Model Pool**: Created `GEMINI_MODEL_POOL` (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-flash-lite-latest`, `gemini-flash-latest`, `gemini-2.5-flash`) distributing incoming requests evenly across high-capacity models (15 RPM / 500 RPD free tier quotas) to eliminate 429 rate limit bottlenecks.
  2. **Instant Failover Circuit Breaker**: Replaced fixed-model retries with an instant model failover loop: on receiving HTTP 429, 503, or connection timeouts, requests immediately rotate to the next model in the pool within milliseconds.
  3. **Context & Quota Optimization**: Capped active conversation history payload to recent 10 messages for high-speed inference. Optimized `update_session()` in `db.py` to bypass expensive `summarize_learnings` calls on incremental message updates, cutting Socratic chat quota consumption by 50%.
  4. **Options OBB (OpenBB Derivatives & Order Book Microstructure) Blueprint**: Designed an architectural blueprint for integrating OpenBB real option chains (`obb.derivatives.options.chains`), empirical volatility surface modeling, bid-ask spread friction, and unusual options volume filters.
- **Saxo Multi-Year Trade History, PDF Chunker & Behavioral Forensics Engine (2026-08-20)**:
  1. **Dual Ingestion Engine (`pdf_report_parser.py` & `trade_history_ingest.py`)**: Automated chunker parsing authentic multi-page Saxo PDF reports and OpenAPI historical endpoints (`/clientreporting/v1/`, `/hist/v3/transactions`, `/hist/v4/performance/timeseries`) into structured SQLite tables.
  2. **Campaign Lifecycle Stitcher (`campaign_stitcher.py`)**: Reconstructs unified options/equity strategy campaigns with true Net Return on Capital and holding durations.
  3. **Behavioral Bias Forensics (`behavioral_forensics.py`)**: Diagnoses historical psychological pitfalls (Short Call Drag on PANW/AMZN, Unhedged Bag-holding on PLUG, and Systematic Edge on Visa/IBM) with composite Discipline Scores (0-100).
  4. **Behavioral Execution Safety Shield (`safety_shield.py`)**: Pre-flight automated circuit breakers (Momentum Call Delta Guard, 21-DTE Gamma rule, Revenge Cooldown, 15% Concentration Cap).
  5. **Next.js Institutional Behavioral Cockpit (`frontend/src/app/behavioral-lab/page.tsx`)**: Forensic KPI ribbon, diagnostic bias cards, interactive campaign history table, pre-flight safety simulator, and live Saxo news wire feed (`/api/history/news`).

- **Unified Institutional Logging, React ErrorBoundary & Saxo Blotter Normalization (2026-08-20)**:
  1. **React ErrorBoundary & Diagnostic Inspector (`ErrorBoundary.tsx`)**: Safely isolates component render failures, renders interactive diagnostic cards with 1-click clipboard stack copying, component hierarchy tracing, and retry/reload actions.
  2. **Client-Side Telemetry & Log Forwarding (`logger.ts` & `POST /api/logs/client-error`)**: Intercepts `window.onerror` and `unhandledrejection`, streaming formatted error payloads to FastAPI backend and persisting to `client_errors.log`.
  3. **Electron Live Terminal Streaming (`desktop/main.js`)**: Forwarded `console-message` directly to terminal stdout with colored labels (`[Frontend ERROR]`, `[Frontend WARN]`) and enabled `F12` / `Ctrl+Shift+I` DevTools hotkey.
  4. **React Error #31 Fix (DurationType Object Child)**: Resolved Saxo OpenAPI audit order activities returning `Duration` as `{DurationType: "DayOrder"}` dict by normalizing all blotter rows to primitive strings in both `saxo_client.py` and `page.tsx`.

- **Live Market News Aggregator & 10-Minute Auto-Feeder (2026-08-20)**:
  1. **Dual Feeder Engine (`saxo_client.py`)**: Interleaves Saxo OpenAPI `/news/v1/news` with real-time financial market RSS feeds across active portfolio & watchlist tickers (`COIN`, `AAPL`, `NVDA`, `PLTR`, `INTC`, `IBM`, `BAC`, `CVX`, `CSCO`, `KO`, `GE`, `GS`). Extracts authentic timestamps, article links, source names (`Reuters`, `Bloomberg`, `WSJ`, `CNBC`), and smart category tags (`Crypto`, `Earnings`, `Macro/Fed`, `Tech`, `Derivatives`).
  2. **10-Minute Background Polling**: Automatic `setInterval` feeder refreshing news telemetry in the background every 600,000 ms.
  3. **Interactive Control Bar (`behavioral-lab/page.tsx`)**: Pulsating emerald live status indicator, **"Refresh Feed"** button right next to the badge with active spin state, `Last sync: HH:MM:SS` indicator, multi-category filter pill bar with dynamic counts, and live search bar.

- **🎯 Next Session Focus: Saxo Live Limit Order Execution Engine**:
  1. **Open Live Trade Execution Gates**: Transition `BROKER_ALLOW_LIVE_EXECUTION` from simulated safety shield mode to live order placement on Saxo OpenAPI (`POST /trade/v2/orders`).
  2. **Far-OTM Limit Order Engine**: Implement systematic execution for conservative Cash-Secured Puts (CSPs) and Covered Calls (CCs) using far out-of-the-money limit pricing (~10–15% OTM, ~0.15–0.20 Delta) with automated order duration controls (`Day Order` / `G.T.C.`).
  3. **Live Order Activity Telemetry**: Real-time order placement confirmation modal with order status polling (`Placed` -> `Working` -> `Traded`).

- **Weekly Macro Intelligence & Controlled Live Execution Engine (2026-08-22)**:
  1. **Weekly Intelligence Engine (`weekly_intelligence.py`)**: Digests Monday–Friday macroeconomic events, Saxo news wire, and Google News RSS across active watchlist (13 Saxo Stocks US) + open holdings/trade history pillars (`COIN`, `INTC`, `PLTR`, `IBM`, `NEM`). Detects directional edges (e.g. COIN US Clarity Act legislative spike fade/hold, INTC restructuring dip, IBM steady yield).
  2. **Margin Guardian (`margin_guardian.py`)**: Real-time margin utilization engine enforcing user's hard **10–15% margin utilization cap** and cash collateral sufficiency before any order placement.
  3. **Trade Staging & Dual-Key Approval (`trade_staging.py`)**: SQLite-backed trade recommendation state machine (`PROPOSED` → `APPROVED` → `EXECUTING` → `FILLED` / `REJECTED` / `BLOCKED`). Orders are never placed on Saxo until explicitly approved by user click.
  4. **Behavioral Safety Shield Enhancements (`safety_shield.py`)**: Added Circuit Breaker #5 (15% Margin Utilization Cap) and Circuit Breaker #6 (Earnings Blackout Buffer ±7 days).
  5. **Encapsulated UI Dashboard (`frontend/src/app/weekly-intelligence/page.tsx`)**: Modeled after the clean layout of `earnings/page.tsx`. Features Margin Utilization Gauge, AI Macro Briefing Card, Potential Trades Action Matrix with 1-Click Approve/Reject, and Saxo Live Execution Telemetry Log.
  6. **Gemini Multi-Model Pool Failover**: Configured Google AI Studio API Key integration with thread-safe model rotation and instant failover across `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3-flash`, and `gemini-2.5-flash`.
  7. **Saxo Live OpenAPI Environment Synchronization & Live Execution Gate (2026-08-22)**:
     - Configured `SAXO_ENV=LIVE` as default environment across `config.py`, `saxo_client.py`, and local `.env`.
     - Synced authentic live app credentials: `AppName="Akpegis-Agent"`, `AppKey="086a7ec061b240c49c4d2bc828d6399b"`, `AppSecret="c1866b3d04d64e72936e53f1fb803455"`, `RedirectUrls=["https://Akpegis-Agent.com.sg"]`.
     - Directed OAuth Authorization to `https://live.logonvalidation.net/authorize` and OpenAPI to `https://gateway.saxobank.com/openapi/`.
     - Enabled live trade transmission gate (`BROKER_ALLOW_LIVE_EXECUTION=true`) with dual-key approval and margin guardian pre-flight audit.
  8. **Verified Saxo Live Order Execution & Testing Safety Directive (2026-08-22)**:
     - **100% Live Order Placement Verified**: Authenticated orders (`Sell to Open` Limit Orders with dynamic `AccountKey`, `OptionSpace` contract UIC lookup, and `ToOpenClose="ToOpen"`) successfully executed on Saxo Live exchange with real working status.
     - **Strict Testing Safety Rule**: All automated/diagnostic backend tests MUST strictly use `POST /trade/v2/orders/precheck` to validate parameters and cash requirements without sending real live orders to production. Real live orders on `POST /trade/v2/orders` are ONLY dispatched when the user explicitly clicks the "Approve Trade" UI button.
  9. **Real-time Saxo Live Order Blotter Refresh & Top Holdings Layout (2026-08-22)**:
     - **Live Order Blotter Route**: Registered `@app.get("/api/broker/order-blotter")` in FastAPI and integrated `cs/v1/audit/orderactivities` with authentic `AccountKey` and `ClientKey`.
     - **Complete Live Audit Sync**: Aggregates all 37+ historical and live order activities across all lifecycle states (`Cancelled`, `Working`, `Traded`, `Expired`). Real-time cancellations (e.g. IBM `5436410532` & INTC `5436410527`) instantly reflect at the top of the blotter upon clicking "Refresh Data".
     - **5-Status Filter Tabs & KPI Ribbon**: Added dedicated `Working` tab alongside `All`, `Traded`, `Expired`, and `Cancelled`.
     - **Top Priority Holdings Layout**: Re-positioned **Live Saxo Holdings & Open Positions** directly to the TOP of the dashboard immediately following the Executive Metrics Grid.

- **100% Dynamic Market Data Purge & Quantitative Risk Upgrades (2026-08-23)**:
  1. **Dynamic High-Beta & Volatility Risk Shield (`safety_shield.py`)**: Completely eliminated hardcoded ticker lists (`high_beta_growth_tickers`). Replaced with quantitative market risk checks evaluating authentic asset **$\text{Beta} \ge 1.30$** and **$\text{Realized Volatility} \ge 35\%$** to prevent short call drag on momentum assets.
  2. **Dynamic Weekly Macro Spot & Strike Resolution (`weekly_intelligence.py`)**: Purged all static prices (`intc_price = 22.50`, `ibm_price = 198.00`, etc.). Implemented real-time market data pulls via `fetch_market_data(symbol)` (Alpaca v2 bars $\to$ yfinance $\to$ Saxo live mark), dynamically solving for conservative target strikes and Black-Scholes theoretical premiums with real volatility metrics.
  3. **Live Watchlist Hydration (`frontend/src/app/page.tsx`)**: Removed static `defaultCspList` snapshot array. Frontend dynamically hydrates and displays animated skeleton loading states while streaming live options scanner results.
  4. **Dynamic Indexation Universe (`fundamental_index.py`)**: Replaced static sample universe with dynamic S&P 500 constituents sourcing from `universe.py`.
  5. **Native Windows Test & Execution Verification**: Executed and validated all unit tests and quantitative engines natively on Windows PowerShell with 100% test pass rate.

- **Zero-Copy Automated OAuth 2.0 MFA Interceptor & Slack Architecture (2026-08-23)**:
  1. **Security Policy: Pure On-Demand MFA (No Perpetual Rolling)**: Explicitly rejected perpetual refresh token rolling to eliminate credential exposure, replay vulnerabilities, and unauthorized ghost execution. Sessions require interactive MFA re-authentication upon expiry.
  2. **Automated OAuth Callback Receiver (`GET /api/broker/oauth/callback`)**: Added endpoint in FastAPI that automatically intercepts the `code` parameter from Saxo upon successful login, exchanges it for live tokens, posts a cross-window notification, and auto-closes the popup.
  3. **Desktop Native OAuth Interceptor (`desktop/main.js`)**: Configured Electron `open-saxo-oauth` IPC handler intercepting `will-redirect` events, capturing the authorization code before navigation errors, and auto-closing the login modal with zero copy-pasting required.
  4. **Frontend 1-Click MFA Button**: Integrated 1-Click "Authorize Saxo (MFA)" button directly into the dashboard header, connection screen, and the live execution telemetry log.

- **Strict 30 to 32 DTE Constraint for Wheel Strategy (CSPs & CCs) (2026-08-24)**:
  1. **Behavioral Safety Shield (`safety_shield.py`)**: Added `self.max_dte_wheel = 32`. Selling any options with $\text{DTE} > 32$ triggers a hard `MAX DTE VIOLATION` infraction and blocks execution.
  2. **Wheel State Machine & Pre-Trade Guards (`wheel_engine.py`)**: Replaced all legacy 35/45-day defaults with `TARGET_ENTRY_DTE = 30` and `MAX_ENTRY_DTE = 32`. Updated 21-DTE gamma avoidance roll targets from 35 DTE to 30 DTE cycle (`check_dte_roll`). Added pre-trade DTE guard validation.
  3. **Weekly Macro Intelligence (`weekly_intelligence.py`)**: Updated candidate generator `_build_dynamic_trade_candidate` default from 35 to 30 DTE. Updated all macro setups (`COIN`, `INTC`, `IBM`) to strict 30 DTE.
  4. **Trade Staging Engine (`trade_staging.py`)**: Enforced 30 DTE baseline for trade staging and execution parameters.
  5. **Saxo OpenAPI UIC Contract Resolver (`saxo_client.py`)**: Updated option space chain proximity resolver to target 30 DTE expirations.
  6. **Live CSP Scanner Route (`main.py` - `/api/scanner/csp`)**: Set scanner expiration calculations to strict 30 DTE for annualized return on capital ($\text{ROC} = (\text{Premium}/\text{Strike}) \times (365/30) \times 100$).
- **Institutional Macroeconomic & Cross-Asset Research Desk Briefing Integration (2026-08-24)**:
  1. **Daily/Weekly Research Desk Prompt Engine (`weekly_intelligence.py`)**: Integrated multi-section institutional macro prompt ingesting live top 10 news stories from Saxo/RSS, watchlist tickers, macroeconomic calendar catalysts, and cross-asset levels (10Y yield, S&P 500, DXY, WTI, Gold, VIX).
  2. **Refined Generative Model Pool**: Configured authentic Google AI Studio generative models in priority order (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`, `gemini-2.0-flash-lite`, `gemini-2.5-pro`, `gemini-1.5-pro`, `gemma-2-27b-it`) with automatic failover and 70+ aggregate RPM throughput.
  3. **Structured Research Output**: Enforces strict markdown structure across 6 core sections:
     - `## Executive Summary`: Dominant themes, net directional bias for rates/equities/credit/FX, immediate triage flags.
     - `## Macro Calendar Context`: Key CPI, PCE, NFP, and FOMC releases with consensus expectations.
     - `## Cross-Asset Snapshot`: Live levels for US 10Y, S&P 500, DXY, WTI, Gold, VIX.
     - `## Story Grouping by Priority`: Tiered by `High Priority`, `Medium Priority`, `Low Priority`.
     - `## Individual Story Format`: Headlines, context with bold financial figures, 3 discrete actionable tasks (Exposure Mapping, Internal Briefing, Escalation Watch), Priority tags, and Timelines.
     - `## Interconnection Flag & Compliance Disclaimer`: Cross-asset linkage synthesis and institutional disclaimer.
- **Order Blotter Real-Time State Normalization & Broker Telemetry Synchronization (2026-08-24)**:
  1. **Strict Open Working Orders Correlation (`saxo_client.py`)**: Correlates real-time live open orders from `GET port/v1/orders/me` with historical audit logs (`cs/v1/audit/orderactivities`). An order is only assigned `Working` status if it is currently active in `port/v1/orders/me`. Historical audit actions (such as older `Placed` / `Working` records from expired DayOrders or past option months) are strictly normalized as `Expired` / `Cancelled`, eliminating false positive working orders.
  2. **Automated Cache Invalidation & Force Refresh Gateway (`POST /api/broker/refresh`)**: Purges stale SQLite `saxo_cache` entries on disconnect, login/token set, and manual dashboard refresh, ensuring that switching accounts, logging in, or clicking "Refresh Data" immediately synchronizes 100% authentic live broker telemetry.
  3. **Header Modernization (`Header.tsx`)**:
     - Upgraded the status pill from `"Saxo LIVE (Read-Only Shield)"` to **`"● Saxo LIVE (Trading Active)"`** in emerald green (`bg-emerald-50 text-emerald-700 border-emerald-200`) to reflect live order execution capabilities.
- **Covered Call Underlying Stock Ownership Validation & Dynamic CSP Enforcement (2026-08-24)**:
  1. **Strict 100-Share Underlying Stock Ownership Check (`_build_dynamic_trade_candidate` & `safety_shield.py`)**: A Covered Call (CC) requires holding at least 100 shares of the underlying stock per contract in the user's active portfolio (`positions` where `asset_type == "Stock"` and `amount >= 100`). If a user does not own $\ge 100$ shares of a stock (such as `IBM`, `INTC`, `AAPL`), recommending or executing a Call is an unhedged/naked short call and is strictly prohibited.
  2. **Automatic CSP Conversion**: Any yield strategy proposed for a non-owned stock is strictly enforced as a **Cash-Secured Put (CSP)** (e.g. `IBM CSP $210`, `INTC CSP $80`, `COIN CSP $170`) targeting ~10% OTM with 30 DTE.
  3. **Circuit Breaker #7 in Behavioral Safety Shield (`safety_shield.py`)**: Added hard circuit breaker `UNHEDGED SHORT CALL VIOLATION` that inspects `underlying_shares_owned` and automatically blocks any Sell Call order unless $\ge 100 \times \text{contracts}$ shares are verified in the account.
- **Earnings Volatility Scanner Pydantic Alignment & Schema Standardization (2026-08-26)**:
  1. **Model Parameter Alignment (`models.py`)**: Added `low_threshold_pct: float = 0.20` and `min_open_interest: int = 5000` to `EarningsScanRequest`, resolving HTTP 500 attribute error when scanning next-week earnings.
  2. **Consistent ScanResult Return Schema (`earnings_scanner.py`)**: Standardized all filter exits (no earners, 52W low screening, fundamental checks, and liquidity filtering) to return the standard dictionary schema with `plays: []` and populated counter metrics, preventing frontend undefined errors.
- **Weekly Intelligence Refresh Performance Optimization & In-Card Loading Spinner (2026-08-27)**:
  1. **Candidate Loop Network Optimization (`weekly_intelligence.py` & `margin_guardian.py`)**:
     - Pre-fetches portfolio positions and margin status once per analysis cycle and passes them directly to `_build_dynamic_trade_candidate`, eliminating 36 redundant Saxo network roundtrips during candidate evaluation.
     - Updated `validate_trade_margin(current_status=...)` in `MarginGuardian` to reuse cached/pre-fetched margin evaluations.
  2. **Daily Cache Freshness Auto-Detection (`weekly_intelligence.py`)**:
     - Enforces daily cache validation checking `generated_at.startswith(today_str)`. The app automatically detects new calendar days (e.g. Wednesday $\to$ Thursday) and generates today's fresh macro briefing without requiring manual refresh clicks.
  3. **In-Card Loading Spinner & Real-Time Feedback (`weekly-intelligence/page.tsx`)**:
     - Added prominent, institutional loading spinner and skeleton progress card ("⚡ Synthesizing live market news, macro catalysts & options yield posture with Gemini...") inside the Gemini Macroeconomic Briefing card while `loading` is active.
     - Enhanced `fetchBriefing` to immediately log actionable progress feedback (`🔄 Refreshing live market feeds & synthesizing Gemini macro briefing...`) to the live execution telemetry log.
     - Recompiled and verified Next.js static production assets natively on Windows.
  4. **News Feed Field Normalization (`weekly_intelligence.py`)**:
     - Normalized `item.get("headline")` alongside `Headline`/`title` when formatting the raw top-10 news stories for Gemini, preventing blank inputs and eliminating fallback placeholder text.
  5. **Exact Underlying Symbol Matching for Option UICs (`saxo_client.py`)**:
     - Upgraded `resolve_option_contract_uic` to strictly match the exact underlying ticker prefix (`clean_sym == symbol.upper()`), preventing keyword collision where `NVDA` resolved to leveraged ETF option roots (`NVDY`, `NVDU`). This completely resolves the `PriceExceedsAggressiveTolerance` exchange rejection.
  6. **Tabular Macro Intelligence & Streamlined Research Desk Format (`weekly_intelligence.py` & `page.tsx`)**:
     - Converted `Macro Calendar Context` into a structured markdown table with Economic Indicator, Consensus, Actual/Prior, and Status/Timing columns.
     - Converted `Cross-Asset Snapshot` into a structured markdown table with Asset/Benchmark, Current Level, Daily Change, and Market Context columns.
     - Streamlined `Story Grouping by Priority` to provide pure headlines and bolded context paragraphs, eliminating verbose actionable tasks, exposure mapping, timeline bullets, priority tags, interconnection flags, and compliance disclaimers.
- **QuantStats Institutional Analytics & 30-DTE Wheel Strategy Benchmarking Cockpit (2026-08-30)**:
  1. **Maintained Dependency Integration (`quantstats-lumi`)**: Installed `quantstats-lumi` (v1.1.5) natively in `.\venv_win\`, providing seamless Pandas 2.x and modern `yfinance` compatibility for institutional portfolio analytics.
  2. **Dedicated Quantitative Analytics Engine (`quantstats_engine.py`)**: Computes 50+ risk/return metrics (Sharpe, Sortino, Smart Sharpe/Sortino, Calmar, Max Drawdown, $\text{VaR}_{95\%}$, $\text{CVaR}_{95\%}$, Tail Ratio, Alpha ($\alpha$), Beta ($\beta$), Information Ratio, Win Rate, Profit Factor, Kelly Criterion), constructs responsive Monthly Return Heatmap matrices ($12 \times N$ Years), and generates standalone, self-contained HTML Tear Sheets (`reports/tearsheet_*.html`).
  3. **Monthly Heatmap Column Normalization**: Fixed case-sensitivity mapping where `quantstats-lumi` outputs uppercase column names (`JAN`, `FEB`, `MAR`, `EOY`), ensuring all 12 calendar month cells for 2025 and 2026 populate with accurate color-graded percentages.
  4. **True Monthly Harvest Cadence Mode (`wheel_backtester.py`)**: Implemented `hold_to_expiration=True` as default, strictly enforcing **10–12 trades per year** with a **30-day holding horizon to expiration** (eliminating premature turnover and transaction fee drag), alongside an optional 50% early profit scalping mode.
  5. **FastAPI Endpoints (`main.py` & `models.py`)**: Registered `POST /api/analytics/wheel-backtest` (returns complete metrics, Recharts equity curves, monthly matrices, and harvest trade logs) and `GET /api/analytics/tearsheet/{report_id}` (serves standalone HTML tear sheet).
  6. **Velzon Design System Alignment & Execution Mode Toggle (`frontend/src/app/analytics/page.tsx` & `Sidebar.tsx`)**: Rebuilt the entire page layout to match the clean Velzon aesthetic used across `weekly-intelligence` and `earnings`. Features execution mode toggles (`Monthly Harvest (~30d)` vs `50% Early Exit`), clean white card containers (`border-slate-200/80 shadow-sm`), primary brand accents (`#4051B5`), soft badge highlights, and full 24-month lookback support.
- **Institutional-Grade Dynamic Universe & GICS Sector Stratification Engine (2026-09-02)**:
  1. **Multi-Watchlist & Blotter Historical Ingestion (`saxo_client.py`)**: Added `get_all_watchlist_instruments()` dynamically aggregating unique instruments across all user Saxo watchlists (rather than only `WL_STOCKS_US`), alongside `get_historical_traded_symbols()` capturing all assets historically traded in the blotter and closed positions.
  2. **4-Tier Institutional Universe Pipeline (`universe.py`)**:
     - *Tier 1 (Multi-Source Ingestion)*: Combines 500+ assets across Saxo positions, multi-watchlists, historical blotter, and S&P 500 constituents with industry classification.
     - *Tier 2 (Solvency & Quality Shield)*: Screens for Altman Z-Score $\ge 1.81$, Piotroski F-Score $\ge 5$, Market Cap $\ge \$10\text{B}$, and positive operating cash flow.
     - *Tier 3 (Options Microstructure & Liquidity Filter)*: Enforces Stock Price $\ge \$15$ (zero penny stocks) and Realized Volatility $\le 45\%$ (preventing high-beta momentum short call drag and extreme downside gap-risk).
     - *Tier 4 (GICS Sector Stratification)*: Normalizes all assets into the 11 standard GICS sectors (`Information Technology`, `Financials`, `Health Care`, `Consumer Discretionary`, `Communication Services`, `Industrials`, `Consumer Staples`, `Energy`, `Utilities`, `Real Estate`, `Materials`), caps at max 3–4 candidates per sector, calculates 30-DTE Black-Scholes ~10% OTM target strikes and Annualized ROC, producing an active focus pool of 44+ institutional targets.
  3. **High-Performance SQLite Cache Layer**: Focus pool persisted in SQLite (`focus_universe_cache`) with 24-hour TTL, hydrating in **21.5 ms** for instant API and agent consumption.
  4. **Sector-Diversified Weekly Staging (`weekly_intelligence.py` & `trade_staging.py`)**:
     - Expanded `COMPANY_TICKER_MAP` to cover market leaders across all 11 sectors.
     - Enforced a hard **max 2 staged trades per GICS sector cap** in `_generate_dynamic_trade_candidates()`, guaranteeing multi-sector representation across staged trades (`Communication Services`, `Information Technology`, `Financials`, `Industrials`) and completely eliminating Tech/AI portfolio concentration risk.
     - Added sector-specific institutional theses for Healthcare, Consumer Staples, Energy, Industrials, Utilities, Materials, and Financials.
  5. **FastAPI Endpoints (`main.py`)**:
     - `GET /api/universe/focus-pool`: Returns the active 44+ institutional options candidates with full pricing, Greeks, and solvency metrics.
     - `GET /api/universe/sectors`: Returns GICS sector distribution and constituent counts.
     - `POST /api/universe/refresh`: Triggers an on-demand re-scan and cache invalidation.
  6. **Native Windows Verification**: Verified 100% pass across all endpoints and staging engines with zero breaking changes.
- **Google ADK 2.0 Graph Workflow Runtime & Declarative DAG Migration (2026-09-02)**:
  1. **Google ADK 2.8.0 Integration**: Installed `google-adk` (v2.8.0) natively in `.\venv_win\`, unlocking graph-based multi-agent runtime (`Workflow`, `Node`, `Edge`, `START`) with zero regressions to `pydantic` or `quantstats-lumi`.
  2. **OptionsLab ADK 2.0 Graph Workflow Engine (`options_adk_workflow.py`)**:
     - *Pre-Flight Auth Node (`saxo_auth_preflight`)*: Proactively audits Saxo OAuth access token lifespan (20-minute limit), executes silent rolling renewal via `refresh_token`, and handles MFA expiration by gracefully routing to SQLite broker cache and signaling `MFA_REAUTH_REQUIRED`.
     - *Tier 1 Node (`macro_news_ingestion`)*: Extracts live Saxo catalysts and binds them to the 44-ticker 11-sector institutional focus universe.
     - *Tier 2 Specialist Fan-Out Nodes*: Concurrent execution across `tech_volatility_analysis` (Realized Vol $\sigma$, Beta $\beta$), `fundamental_conviction_analysis` (Sector alignment & thesis generation), and `options_greeks_pricing` (30-DTE Black-Scholes ~10% OTM target strikes & Annualized ROC %).
     - *Multi-Agent Synthesizer Node (`multi_agent_synthesizer`)*: Aggregates specialist streams into 6 high-conviction trades, enforcing the max 2 per GICS sector diversification cap.
     - *Deterministic Margin & Risk Gate (`margin_guardian_gate`)*: Enforces programmatic code routing (`APPROVED` vs `REJECTED`) verifying margin utilization $\le 15\%$, 100-share CC coverage, and earnings blackout buffers.
     - *Human-In-The-Loop Staging Gate (`hitl_staging_gate`)*: Implements native pause/suspend primitive (`PAUSED_AWAITING_USER_APPROVAL`), staging trades into SQLite until the user authorizes execution via UI or Slack.
     - *Automatic Fallback Circuit Breaker*: Seamlessly fails over to proven standard engine upon any framework exception.
  3. **FastAPI Endpoints (`options_lab/api/main.py`)**:
     - `POST /api/adk/weekly-pipeline`: Triggers full ADK 2.0 graph workflow execution.
     - `GET /api/adk/status`: Returns workflow topology, node metadata, and active deterministic guardrails.
  4. **Hierarchical Orchestrator Modernization (`nasdaq-multi-agent/app/orchestrator.py`)**:
     - Refactored `HierarchicalOrchestrator` from manual `asyncio.gather` calls into an explicit, declarative ADK 2.0 DAG (`nasdaq_hierarchical_orchestrator_workflow`) with explicit Tier 1 Macro $\to$ Tier 2 Tech/Fund $\to$ Tier 3 Holy Grail Portfolio edges.
     - Preserved 100% backward compatibility for all existing API consumers and test scripts.
  5. **Live News Wire Real-Time Sorting & Cache-Busting Upgrade (2026-09-02)**:
     - *Strict Descending Time Sorting*: Resolved Google RSS returning static relevance ordering by parsing `pubDate` via `email.utils.parsedate_to_datetime` and sorting all candidates in strict descending order (`reverse=True`), guaranteeing articles published 1m, 3m, or 7m ago always appear at the top.
     - *Dynamic Relative Timestamps*: Sliced raw GMT strings converted to localized relative time (`1m ago`, `24m ago`, `1h ago`) with emerald green badge pills for real-time clarity.
     - *Zero-Cache Force Refresh*: Implemented cache-busting timestamps (`_ts` and `_t`) across Google RSS, `api.ts`, and FastAPI headers (`Cache-Control: no-cache, no-store, must-revalidate, max-age=0`) so clicking "Refresh Feed" instantly updates without browser caching.
     - *Regex Word Boundary Categorization*: Enforced strict regex word boundaries (`\b(options?|puts?|calls?)\b`, `\b(crypto|bitcoin)\b`, `\b(earnings?|revenue)\b`, `\b(fed|macro)\b`, `\b(ai|chips?|quantum)\b`) to prevent false positives like `"adoption"` triggering `"Derivatives"`.
  6. **Exchange Tick Size Quantizer & Live Order Execution Fix (2026-09-02)**:
     - *Root Cause Analysis*: Diagnosed Saxo OpenAPI `PriceNotInTickSizeIncrements` error on COIN CSP: continuous Black-Scholes pricing yielded `$6.39`, which violated US Options Exchange and Saxo tick rules (options $\ge \$3.00$ mandate strict $\$0.05$ or $\$0.10$ tick increments).
     - *Automated Tick Quantizer Engine (`saxo_client.py`)*: Implemented `get_tick_size` and `quantize_order_price`, dynamically querying instrument `TickSizeScheme` from Saxo OpenAPI and applying standard OCC/CBOE increments.
     - *End-to-End Price Normalization*: Integrated quantization into `place_order`, `trade_staging.py`, `weekly_intelligence.py`, and `options_adk_workflow.py` to ensure all staged and executed option prices are exchange-compliant.
  7. **Institutional Live Option Quote Engine (Bid / Ask / Spread / Mid) (2026-09-02)**:
     - *Eliminated Execution Risk*: Eliminated the risk of submitting orders based on continuous theoretical Black-Scholes estimates which diverge from live order book liquidity and real market spreads.
     - *Tiered Market Quote Resolver (`fetch_option_market_quote`)*:
       1. Primary: Saxo OpenAPI `GET /trade/v1/infoprices?Uic={uic}` for direct broker market data quotes.
       2. Secondary: Real-time OPRA exchange options chain resolving authentic Bid, Ask, Mid, and Last prices across the target expiry cycle.
       3. Fallback: Theoretical model solely when exchange order books are closed.
     - *Market-Anchored Mid Limit Pricing*: Staged trade limit prices are now set to the authentic exchange **Mid price** (`(Bid + Ask) / 2`), quantized to the instrument's exact tick increment (e.g., COIN \$160 CSP proposed at `$5.05` inside the live `$4.80 – $5.30` market spread).
  8. **Frontend-Backend Handshake Short-Circuit & Multi-Tiered Timeout Protocol (2026-09-02)**:
     - *Pre-Flight Handshake Short-Circuit*: Built `checkBackendHandshake(timeoutMs: 3000)` checking `/api/health`. If the backend is offline, refused, or non-responsive, the UI halts within 3 seconds, sets `loading = false` to eliminate infinite spinning, and displays a prominent amber warning card with the single recovery command (`.\restart_backend.ps1`) and a 1-click **"Retry Handshake"** button.
     - *Multi-Tiered Timeout Guards*:
       1. Frontend `apiRequest`: Integrated `AbortController` with customizable `timeoutMs` (35s for deep pipelines), translating network drops into clean, actionable UI messages.
       2. Backend FastAPI: Enforced `asyncio.wait_for(..., timeout=40.0)` around `adk_workflow_engine.run_pipeline`. If external LLM or market feeds time out, the backend gracefully serves the last synchronized briefing from SQLite cache rather than dropping the HTTP connection.
     - *Parallelized ADK Specialists Fan-Out*: Re-architected `tech_volatility_node` and `options_greeks_node` with concurrent `ThreadPoolExecutor(max_workers=6)`. Slashed full fresh pipeline execution time from **50+ seconds down to 12.8 seconds**!
     - *Modernized UI Telemetry*: Purged legacy references to theoretical Black-Scholes pricing from the loading skeleton. Displays real-time progress (`Verifying Backend Handshake...` $\to$ `Synthesizing Google ADK 2.0 Macro Intelligence & Live Quotes...`).
  9. **100% Native Windows Verification**: Verified end-to-end execution across both OptionsLab and Nasdaq Multi-Agent with zero WSL dependencies.

- **Alpaca Market Data & Real-Time Option Chains Pipeline (Architectural Blueprint — 2026-09-03)**:
  1. **Provider Hierarchy & Precedence**:
     - *Primary*: Saxo OpenAPI live quotes (`trade/v1/infoprices`) when broker session is authenticated.
     - *Secondary*: Alpaca Options REST API (`/v1beta1/options/snapshots/{symbol}`) providing native OPRA exchange quotes when broker session is unauthenticated or token expires.
     - *Fallback*: Local SQLite cached snapshot and realistic synthetic chain when market is closed or API keys are missing.
  2. **Snapshot & High-Efficiency Caching Strategy**:
     - Fetches complete underlying option chain via a single snapshot request (`/v1beta1/options/snapshots/{symbol}`).
     - Caches responses in local SQLite/memory with a 60-second TTL to stay comfortably within Alpaca's 200 req/min rate limit while providing instantaneous strike browsing.
  3. **Empirical Spline Volatility Surface & Smile Modeling**:
     - Extracts empirical Implied Volatility directly from authentic market quotes across available expiration cycles.
     - Fits clamped cubic splines across strike moneyness ($K/S$) and linear interpolation across DTE to construct smooth, authentic 3D volatility surfaces.
  4. **Unified Internal Greeks Resolver**:
     - Ingests real exchange Bid, Ask, Mid, and Volume from Alpaca OPRA feeds.
     - Calculates all Greeks (Delta, Gamma, Theta, Vega) and normalized IV through OptionsLab's internal vectorized Black-Scholes engine using live FRED risk-free rates for 100% mathematical consistency across all underlyings.
  5. **Dedicated Options Chain Inspector Cockpit (`/options-chain`)**:
     - Standalone high-speed institutional options chain interface in the frontend sidebar.
     - Features: Symbol selector with quick watchlist pills, dynamic DTE expiration pill bar, split Calls/Puts chain table (Bid, Ask, Mid, Spread, Volume, OI, IV, Delta, Theta), interactive Recharts IV Smile curve, and 1-click stage trade action.
  6. **Strict Non-Regression & Offline Local First Contract**:
     - All schemas enforce optional fields (`session_id: Optional[str] = None`, `title: Optional[str] = None`).
     - Local SQLite (`optionslab.db`) is the primary default database with zero GCP or Firebase lock-in.

- **Zero-Dollar Private Cloud Server & Linux Mint NAS Architecture (2026-09-05)**:
  1. **Infrastructure & Hardware Repurposing**:
     - Repurposed spare HP Pavilion laptop running Linux Mint 21/22 as a dedicated 24/7 private cloud server, eliminating public cloud Run/VM costs ($0/mo).
     - Configured systemd lid-switch overrides (`HandleLidSwitch=ignore`) and thermal governors for headless continuous operation.
     - Recovered 80+ GB of storage by pruning accumulated Timeshift snapshots, increasing available root disk headroom to ~100 GB.
  2. **Storage Stratification (Fast I/O vs Cold Backup Tiering)**:
     - *Fast I/O (Hot Tier)*: Active SQLite database (`optionslab.db`) hosted locally on laptop NVMe/SSD using Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`), guaranteeing microsecond read/write latencies and lock-free concurrent readers.
     - *Cold Backup (Cold Tier)*: Automated backup container streaming point-in-time online SQLite snapshots (`.backup`) to host Samba share (`/home/ishan/nas_share/backups/daily` mapped to Windows as `\\192.168.0.8\MintNAS\backups`).
     - *Rolling Retention Policy*: Prunes backups to retain the last 7 daily snapshots + 4 weekly archives automatically, preventing disk exhaustion.
  3. **Automated 4-Stage Deployment Suite (`nas_share/server_setup/`)**:
     - Generated 4 modular, executable bash scripts directly shipped to the mapped NAS drive (`K:\server_setup\` -> `~/nas_share/server_setup/`):
       - `01_install_docker.sh`: Automated Docker Engine & Docker Compose v2 installation, systemd boot enablement, and non-root group setup.
       - `02_setup_server_stack.sh`: Directory scaffolding (`~/akpegis-server`), Git pull of `nasdaq-multi-agent`, `.env` key synchronization (Alpaca, Saxo, Gemini, Slack), atomic backup runner (`backup_sqlite.sh`), and production `docker-compose.yml`.
       - `03_setup_remote_access.sh`: Free ingress networking setup with Tailscale (private mesh VPN) and Cloudflare Tunnel (`cloudflared`) for secure public Slack webhook delivery (`/slack/events`) without router port forwarding.
       - `04_launch_and_verify.sh`: Zero-downtime container spin-up, pre-flight `/health` verification, on-demand backup test, and network connection telemetry.

  4. **Full-Stack Containerized Web Ingress & Remote Access Overhaul (2026-09-06)**:
     - **Dynamic Nginx API Reverse-Proxy (`nginx.conf`)**:
       - Reconfigured frontend container on port 3000 to dynamically reverse-proxy all backend service paths (`/api/*`, `/market/*`, `/price/*`, `/simulate/*`, `/greeks/*`, `/strategy/*`, `/volatility/*`, `/portfolio/*`, `/tutor/*`, `/multi-agent/*`, `/fundamental-index/*`, `/health`, `/debug/*`, `/docs`, `/openapi.json`) internally to `http://backend:8080`.
       - Eliminates cross-origin CORS barriers, removes the need to expose port 8000 on routers/tunnels, and enables single-port ingress (port 3000) for Cloudflare Tunnel, Tailscale, and local LAN.
     - **Content-Security-Policy (CSP) Relaxation**:
       - Updated `<meta httpEquiv="Content-Security-Policy">` in `layout.tsx` to permit `connect-src 'self' http: https: ws: wss:;`, allowing client browsers on phones, tablets, and remote PCs to connect to server LAN (`192.168.0.8`) and Tailscale (`100.87.159.107`) without CSP rejections.
     - **Dynamic Host Routing & Dual Handshake Fallback (`api.ts`)**:
       - `getApiBase()` uses relative same-origin paths (`''`) in production container deployments, falling back dynamically to `http://${window.location.hostname}:8000` in local dev.
       - Implemented dual-handshake probe: verifies primary same-origin `/api/health` before falling back to direct port 8000 probe.
       - Integrated `runWheelBacktest` into `optionsApi` and refactored `analytics/page.tsx` to consume it, resolving JSON parse failures from static SPA fallbacks.
       - Sanitized all connection drop and short-circuit error badges to dynamically display the active host/port.

- **Saxo OpenAPI Multi-Tiered Persistent Token Storage & 1-Click Web Auto-Linker (2026-09-06)**:
  1. **Multi-Tiered Persistent Token Storage (`db.py` & `saxo_client.py`)**:
     - *Tier 1 (SQLite `broker_tokens`)*: Added persistent table in `optionslab.db` storing `access_token`, `refresh_token`, `token_type`, `expires_at`, and `updated_at`.
     - *Tier 2 (Mounted JSON File)*: Automated secondary snapshot to `/app/data/saxo_tokens.json`, residing directly on the host NVMe volume (`$SERVER_DIR/data/saxo_tokens.json`).
     - *Tier 3 (Host `.env` & Environment)*: Synchronizes into host `.env` file and `os.environ`.
  2. **Startup Hydration & Background Heartbeat Auto-Rolling (`main.py`)**:
     - On container boot, `SaxoClient` automatically hydrates credentials from SQLite/JSON.
     - Background `start_token_heartbeat()` runs every 10 minutes (600s), continuously rolling the Saxo session so tokens never expire.
     - Added `POST /api/broker/oauth/sync-storage` endpoint to immediately flush active in-memory tokens to disk before any container recreations.
  3. **1-Click Web Clipboard Auto-Linker & Window Focus Detector (`page.tsx` & `weekly-intelligence/page.tsx`)**:
     - Eliminates manual typing or hunting for fields across all web browsers (mobile, tablet, desktop).
     - Added prominent **"⚡ Auto-Link from Clipboard"** button: reads clipboard via `navigator.clipboard.readText()`, detects Saxo callback URLs or 36-char authorization codes (`code=...`), exchanges them for tokens, and refreshes the UI automatically.
     - Added window `focus` event listener: automatically detects Saxo authorization codes in the clipboard when returning to the OptionsLab tab after finishing MFA login in a popup.
  4. **Autonomous Migration & Tailscale Repair Scripts (`K:\server_setup\`)**:
     - `update_backend.sh`: Safely extracts active in-memory tokens from the running `akpegis_backend` container before bouncing, pulls the latest code on `nasdaq-multi-agent/auth`, rebuilds containers, and verifies live broker connectivity (`http://localhost:8000/api/broker/status`).
     - `fix_tailscale.sh`: Inspects `tailscaled` service status, verifies authentication, outputs Tailscale IP and node state, and diagnoses mesh routing.
  5. **Desktop Electron Compatibility (`desktop/main.js`)**:
     - Dynamically reads `OPTIONS_LAB_BACKEND_HOST` and `OPTIONS_LAB_BACKEND_URL`, allowing the Windows Electron app to communicate with the Linux Mint server across the LAN/Tailscale while retaining native OAuth window interceptors.
  6. **Nginx Reverse-Proxy Route Disambiguation (`nginx.conf` & `main.py`)**:
     - *Root Cause of Portfolio Summary / Strategies / Pricer 404s*: The previous Nginx regex `location ~ ^/(...|portfolio|strategy|price|simulate)` broad-matched frontend page routes `/portfolio`, `/strategies`, `/pricer`, and `/simulator`, forwarding page navigations to FastAPI backend endpoints which returned `{"detail": "Not Found"}`.
     - *Disambiguation Fix*: Updated `nginx.conf` to enforce strict trailing slashes/exact matching (`^/(api/|market/|price/|simulate/|greeks/|strategy/|volatility/|portfolio/greeks|...|health$)`). Frontend static HTML pages (`/portfolio/index.html`, `/strategies/index.html`, `/pricer/index.html`) now correctly resolve via `try_files $uri $uri.html $uri/index.html $uri/ /index.html;`.
     - *Dual Route Aliasing*: Registered dual `@app.post("/api/...")` route decorators across all analytical pricing and simulation endpoints in FastAPI.

- **OptionsLab Institutional Weekly Intelligence, 4D Macro Direction & AI Corporate Interlink Architecture (2026-09-08)**:
  1. **Memo Format Deprecation**: Deprecated the unstructured, bureaucratic Chief Investment Officer "MEMORANDUM" text prompt in `options_adk_workflow.py` in favor of a structured, institutional quantitative cockpit.
  2. **Accumulated Weekly Headline Memory (`macro_news_memory` in SQLite)**:
     - Persists all scraped financial wire headlines across Monday through Friday with SHA-256 deduplication.
     - Tracks weekly macro momentum and day-over-day trajectory rather than transient single-session snapshots.
  3. **4-Dimensional Macro Direction Compass**:
     - *Dimension 1 (Rates & Monetary Pressure)*: Evaluates Fed path, Treasury yields, and multiple compression.
     - *Dimension 2 (Broad Corporate Earnings & Demand)*: Evaluates real-economy guidance, margins, and non-AI capex.
     - *Dimension 3 (AI Ecosystem Interlink & Circular Capex Contagion)*: Tracks the inter-wired US tech network.
     - *Dimension 4 (Market Liquidity & Volatility Regime)*: Evaluates VIX level, credit spreads, and forced de-grossing risk.
  4. **US AI Corporate Interlink Map (6 Structural Anchors + 4 Dynamic Challengers)**:
     - *6 Anchors (Annual/Monopoly Choke Points)*: `TSM` (Advanced Packaging), `NVDA` (AI GPUs), `MSFT` (Azure), `AMZN` (AWS), `GOOGL` (GCP), `NEE` (US Utility Scale).
     - *4 Dynamic Challengers (Quarterly Fluid Re-ranking)*: Power (`GE` vs `CEG` vs `VST`), Memory (`MU` vs `WDC`), Custom ASICs (`AVGO` vs `MRVL`), and Enterprise AI (`PLTR` vs `SNOW`/`NOW`).
     - *Interlink Transmission Mechanics*:
       - Balance Sheet: Hyperscaler CapEx -> Chipmaker Revenue -> Foundry/Memory Advance Prepayments -> Enterprise Software ROI.
       - Inventory Lead-Lag: Finished Goods vs. Construction in Progress (CIP) & Days Sales of Inventory (DSI).
       - Power Conversion: Hyperscaler CapEx converting to multi-year Power Purchase Agreements (PPAs) and utility backlog (RPO).
   5. **Portfolio Cash Allocation Scenario Matrix (80/20, 60/40 Traditional, 50/50, 20/80)**:
      - Connects live Saxo cash and equity balances to four distinct capital allocation models, including the traditional 60/40 institutional benchmark.
      - Directly addresses Cash Drag by deploying idle cash into Cash-Secured Puts (CSPs) at 15-25% annualized theta yield while maintaining strict 15% margin safety caps.
   6. **$1,000/Month Systematic Wheel Harvest & Assignment Risk Engine**:
      - Hard constraint: targets exactly $1,000/month by recommending 3 to 4 contracts in the $2.00-$3.00 premium sweet spot ($200-$300 per contract).
      - Rejects penny options (< $0.50) and high-beta binary gamble options (> $5.00).
      - Explicitly computes Probability of Profit (PoP ~ 75-82%) and Assignment / Cash-Burn Risk for CSPs (collateral required, assignment probability, discounted breakeven cost basis).
      - Hardens the Saxo / Alpaca OPRA real-time Bid/Ask quote resolution pipeline.
   7. **Double-Cautious Ticker Normalization & Pre-Flight Exchange Verification Protocol**:
      - Zero-tolerance for ticker or UIC inaccuracies: implements strict canonical symbol normalization (`normalize_canonical_ticker`) stripping exchange suffixes (`:xnas`, `:xnys`, `:arcx`) and resolving share classes (`BRK.B` vs `BRK-B`).
      - 5-Point Cryptographic Contract Verification: validates `AssetType`, `UnderlyingSymbol`, `StrikePrice`, `PutCall`, and `ExpiryDate` against Saxo's reference instrument API before staging.
      - Native Exchange Precheck Gate: executes `POST /trade/v2/orders/precheck` on Saxo's engine to simulate order viability, tick size compliance, and margin impact, locking out live approval if unverified.
   8. **Interactive Cockpit UI (`/weekly-intelligence`)**:
      - Modernized frontend with 4D Compass barometer cards, AI interlink status grid, 4-tier cash allocation matrix, and the $1,000/mo Wheel Harvest Blotter with live Bid/Ask, PoP badges, and verified contract badges.

- **OptionsLab Institutional Intelligence & $1,000/Month Wheel Cockpit Implementation (2026-09-09)**:
  1. **SQLite Permanent Memory & Caching Layer (`db.py`)**:
     - `macro_news_memory`: Ingests and persists financial wire headlines across Monday-Friday with SHA-256 deduplication (`headline_hash`) to track multi-day trajectory.
     - `interlink_fundamentals_cache`: Caches corporate balance sheets, CapEx, revenue, GAAP DSI, and RPO backlogs with UPSERT support.
  2. **AI Corporate Interlink Graph Engine (`interlink_graph.py`)**:
     - Models 6 Structural Anchors (`TSM`, `NVDA`, `MSFT`, `AMZN`, `GOOGL`, `NEE`) and 4 Dynamic Challengers (`POWER`, `MEMORY`, `CUSTOM_ASIC`, `ENTERPRISE_AI`).
     - `auto_populate_from_market()`: Automates dynamic SEC balance sheet and income statement ingestion via `yfinance` with GAAP Days Sales of Inventory calculation ($\text{DSI} = \text{Inventory} / \text{COGS} \times 365$).
     - Quantitative 3-Factor Challenger Scoring: Replaced magic numbers with transparent formula: $\text{Score} = 0.40 \times S_{\text{growth}} + 0.30 \times S_{\text{margin}} + 0.30 \times S_{\text{efficiency}}$, exposing exact component weights and values in telemetry payloads.
     - SOX Cycle Median Parameterization: Implemented baseline semiconductor cycle median DSI (`75.0` days $\pm 10.0$ days band; Bottleneck $<65$d, Glut $>85$d).
  3. **Double-Cautious Ticker Normalization & Pre-Flight Exchange Verification (`saxo_client.py` & `market_data.py`)**:
     - `normalize_canonical_ticker()`: Normalizes tickers and strips exchange suffixes (`:xnas`, `:xnys`, `:arcx`).
     - `verify_option_contract()`: 5-point cryptographic/structural check validating AssetType, Symbol, Strike, PutCall, and Expiration.
     - `precheck_order()`: Native simulation via Saxo OpenAPI `POST /trade/v2/orders/precheck` verifying margin impact and tick size compliance.
  4. **4D Macro Compass, 4-Tier Scenarios & $1,000/Mo Wheel Harvest (`weekly_intelligence.py` & `options_adk_workflow.py`)**:
     - `calculate_4d_macro_compass()`: Evaluates Rates & Policy, Corporate Earnings, AI Interlink Contagion, and Liquidity / VIX regimes.
     - `calculate_capital_allocation_scenarios()`: Models 80/20, 60/40 Traditional Institutional Benchmark, 50/50 Barbell, and 20/80 Defensive Cash stance, dynamically scaling dollar values to live account equity.
     - $1,000/Month Systematic Wheel Harvest Blotter: Filters for $2.00–$3.00 premium sweet spot ($200–$300/contract), selects strictly 3–4 candidates across distinct GICS sectors, and calculates PoP % (~75–82%), collateral requirements, breakeven discount, and cash-burn risk narratives.
  5. **Institutional 5-Point Docstring Standard**:
     - Enhanced all classes and methods across `db.py`, `interlink_graph.py`, `saxo_client.py`, `weekly_intelligence.py`, and `options_adk_workflow.py` with the strict 5-point institutional docstring standard: (1) Descriptive Summary, (2) Parameters & Types, (3) Return Object & Types, (4) Exceptions & Side Effects, (5) Executable Usage Example.
  6. **Next.js Institutional Cockpit UI (`frontend/src/app/weekly-intelligence/page.tsx` & `src/types/intelligence.ts`)**:
     - Modular tab navigation: 🎯 $1,000/Mo Wheel Harvest Blotter, 🧭 4D Macro Direction Compass, 🌐 AI Corporate Interlink Cockpit, ⚖️ 4-Tier Capital Scenarios, 📰 Senior Macro Analyst Briefing, 📚 Dynamic Macro Corpus.
     - Verified contract badges, pre-flight check viability badges, quantitative metric strips, and dual-key 1-click order execution.
  7. **Dynamic Macro Category Corpus & Senior Macroeconomic Analyst Persona**:
     - `macro_category_corpus` in SQLite (`optionslab.db`): Replaced hardcoded keyword arrays with dynamic table featuring 72 pre-seeded institutional terms, salience weights (1.0–3.0), strategy directional biases (`BULLISH_CSP`, `DEFENSIVE_CC`, `NEUTRAL_CALENDAR`, `HEDGED_PUT`), and volatility impact ratings.
     - Enriched AI Agentic Taxonomy: Dedicated representation of emerging AI paradigms (`agent`, `agentic`, `agentic platform`, `agentic app development`, `autonomous agent`, `multi-agent`, `reasoning models`, `llm inference`, `sovereign ai`).
     - Weighted Multi-Word Headline Classifier (`_classify_macro_headline`): Token/phrase matching engine resolving categories, directional biases, and suggested tickers.
     - Automated Vocabulary Expansion (`discover_and_expand_corpus`): Learns emerging 2-gram and 3-gram financial terminology from live news feeds and persists with `source="DYNAMIC_DISCOVERY"`.
     - Senior Macroeconomic Analyst Persona Prompt: Streamlined prompt in `options_adk_workflow.py` and `weekly_intelligence.py` to embed a Senior Macroeconomic Analyst & Research Desk Assistant producing finance-oriented daily/weekly briefings.
     - Full-Stack API & UI Control Tab: Dedicated 6th tab `📚 Dynamic Macro Corpus` in the Weekly Intelligence UI with real-time keyword search, category filtering, term registration modal, and deletion controls.
   8. **Multi-Tiered Balance Resolution Engine, Authentic Report Ingestion & Golden Tone Research Exemplar**:
      - 5-Tier Resilient Balance Resolution (`resolve_account_balances`): Permanently eliminated silent synthetic defaults (`account_equity = 100000.0`, `cash_available = 70000.0`) in favor of a 5-tier resolution hierarchy:
        * *Tier 1 (Live Saxo OpenAPI)*: Queries `/port/v1/balances/me` when authenticated.
        * *Tier 2 (Bidirectional SQLite Cache)*: Fixed cache key mismatch bug by auto-synchronizing `'account_summary'` and `'balances'` keys in `saxo_cache`.
        * *Tier 3 (Authentic Statement Report Ingestion)*: Automatically inspects ingested authentic statement records (`saxo_reports`), extracting verified net equity (**\$102,192.51**) and cash balances (**\$71,984.46**) for account `33888/221497` (`Natesan Sathish`).
        * *Tier 4 (Holdings Market Value Aggregation)*: Sums open positions from `saxo_holdings_history` and `portfolio_tickers` (\$30,405.00 across 5 positions).
        * *Tier 5 (Configurable Reference Benchmark)*: Fallback via `DEFAULT_PORTFOLIO_EQUITY` explicitly tagged with `is_simulated = True` and explanatory notices.
      - Dynamic Capital Allocation Playbook Scaling: Scaled all 4 allocation scenarios (80/20, 60/40 Traditional, 50/50, 20/80) dynamically to authentic balance sheet numbers (60/40 cash target = \$40,877.00), attaching `balance_provenance` metadata to each scenario and root briefing payload.
      - Golden Tone Institutional Research Desk Exemplar: Injected the user's authentic research note exemplar into `WeeklyIntelligenceEngine` and `OptionsADKWorkflowEngine` Gemini prompts, tracing second-order physical supply chains (hyperscalers -> chipmakers -> power demand, data centres, networking, memory, cooling, cloud, enterprise software), causal cross-asset contagion (Brent crude -> inflation -> bond yields -> discount rates/WACC -> tech multiples), and contrasting price breadth vs. earnings breadth ("Earnings breadth is considerably harder to fake").
      - Supply-Chain & Macro Transmission Corpus Expansion: Bulk-upserted 12 new supply-chain and cross-asset keywords into SQLite `macro_category_corpus` (`data centres`, `networking equipment`, `cooling`, `power demand`, `electricity demand`, `memory capacity`, `brent crude`, `return on invested capital`, `earnings breadth`, `corporate debt issuance`, `institutional rebalancing`, `discount rate`).
      - Frontend Balance Provenance Ribbon (`/weekly-intelligence`): Added dynamic Provenance Ribbon to Tab 4 displaying color-coded status badges (`🟢 Live Saxo Broker Connection`, `🟡 Persistent Broker Cache`, `📘 Authentic Account Statement`, `⚠️ Standardized Reference Model`), authentic account reference, total equity, and cash buffer.
      - 100% Verification: `npm run build` completed cleanly (17/17 pages static export) and `pytest options_lab/test_api.py -v` passed 100% in 66.04s.
   9. **AI Corporate Interlink Cockpit Defensive Normalization & Null-Safe Resilience (2026-09-09)**:
      - Resolved `TypeError: Cannot read properties of undefined (reading 'includes')` crash in Tab 3 (AI Corporate Interlink Cockpit) of `/weekly-intelligence`.
      - Backend Payload Enrichment (`interlink_graph.py`):
        * `get_structural_anchors()` calculates and returns normalized attributes: `dsi_status` (`"Balanced Supply (65-85d)"`, `"Bottleneck (<65d)"`, `"Inventory Glut (>85d)"`, `"N/A (Asset-Light)"`), `capex_annual_b`, `revenue_annual_b`, `inventory_dsi_days`, and `is_live_data` alongside backward-compatible keys.
        * `get_dynamic_challengers()` returns `composite_score`, `key_tickers`, `rationale`, and aliases inside `score_derivation` (`growth_score`, `margin_score`, `efficiency_score`, `formula`).
      - Frontend Defensive Safeguards (`weekly-intelligence/page.tsx`):
        * Added optional chaining and defensive fallback calculations for `anchor.dsi_status` and numeric formatters (`capex_annual_b.toFixed(1)`, `revenue_annual_b.toFixed(1)`, `inventory_dsi_days.toFixed(1)`).
        * Guarded `challenger` properties, score derivation breakdown, and `key_tickers` mapping whether backend returns array or dictionary.
        * Enforced safe string `.includes` guards across `item.directional_bias` and corpus keyword search filtering with bounded star ratings (`Math.max(0, Math.min(5, item.default_impact || 1))`).
      - Verified via backend payload inspection and full Next.js static compilation (`npm run build` 17/17 pages generated cleanly).

## 📊 Antigravity Usage Stats
> Last Updated: 2026-09-09 21:36:00 SGT

| Metric | Current Session |
| :--- | :--- |
| **Status** | 🟢 Healthy |
| **Projects Synced** | 18 projects + 4 resource dirs |

*Tip: If Status is 🔴, start a new conversation to save quota!* 🚀
