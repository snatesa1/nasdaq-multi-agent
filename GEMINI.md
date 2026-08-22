# nasdaq-multi-agent

Hierarchical Multi-Agent System (FastAPI) for comprehensive NASDAQ and Multi-Asset analysis.

## Project Details (NEW)
- **Project Name:** Personal-Finance-Automation (`projects/106787558501`)
- **Project ID:** `optimal-aurora-495912-n0`
- **Project Number:** `106787558501` (Primary) / `855694839217`
- **Active Gemini API Key:** (Configured securely in environment secrets)

## Architecture & Constraints
- **Endpoints:** `main.py` provides `/health`, `/cron/analyze` (Ad-hoc trigger), and `/slack/events` for `/nasdaqscan`.
- **Execution Rules:** Always use `BackgroundTasks` for the `_run_and_deliver` flow.
- **Orchestrator:** `HierarchicalOrchestrator` manages the pipeline.
- **Holy Grail Implementation:** 
  - **Correlation Agent:** Calculates log returns and correlation matrices across Nasdaq, S&P 500, Bonds, and Bitcoin.
  - **Independence Filter:** Ensures Technical, Fundamental, and Macro signals are statistically distinct.

## 🛡️ Mandatory End-to-End Validation Protocol (User Mandate)
- **Zero Hurrying & Complete Verification**: Take all the time needed to thoroughly and patiently validate every single change end-to-end before reporting to the user.
- **Full Static & Runtime Synchronization**: When modifying frontend code (`src/app/...`), NEVER consider the work done until a fresh production build/export (`npm run build` into `out/`) or active runtime server is verified, compiled, and proven responding.
- **Automated Validation Scripts**: Always create and execute verification test scripts to check live ports, API status codes, file timestamps, and rendered components.
- **No White-Box Guesswork**: Inspect actual file timestamps, process trees, and runtime logs before delivering results.
- **Context Compression & Anti-Bloating**:
  1. Mandate CodeGraph exploration (`codegraph_explore`) for codebase research.
  2. Maintain a sliding history window ($\le 10$ messages) in Socratic Tutor (`tutor.py`).
  3. Prune bulky simulation arrays and raw matrices via `_prune_context()` before LLM ingestion.
  4. Delegate heavy research and wide search operations to subagents (`invoke_subagent`).
  5. Slice file reads to bounded line ranges (`StartLine`/`EndLine`).



## Options Lab & Socratic Tutor Modules [NEW]
- **Earnings Volatility Scanner (`api/earnings_scanner.py` & `frontend/src/app/earnings/page.tsx`)**:
  - Funnel logic: Universe Filter (S&P 500 Wikipedia scrape + NASDAQ) ➡️ 52W Low Proximity check (default 20%) ➡️ 5-Pillar Conviction Screener / Fundamental Quality ➡️ Option Open Interest Liquidity.
  - Volatility Matrix: Calculates 4-quarter pre-earnings volatility, T-1 move, and T+1 reaction.
  - **Macro-Enhanced Volatility Framework [NEW]** (`earnings_macro_enhancement.md`): Upgrades earnings analysis with 5 Macro Context layers:
    1. *Market Beta De-Trending*: Isolates pure stock-specific earnings alpha ($\alpha_i$) by subtracting $S\&P 500$ market return ($\beta_i \cdot R_{\text{SPY}}$).
    2. *Sector ETF Relative Strength*: Compares post-earnings move against sector benchmark (XLK/XLF/XLE).
    3. *Macro Calendar Conflict Overlay*: Flags earnings dates coinciding within 24h of FOMC rate decisions, CPI inflation releases, or Non-Farm Payrolls.
    4. *VIX Regime & Term Structure*: Categorizes IV crush potential based on VIX levels (< 15 Complacent, 15-25 Normal, > 25 High Fear).
    5. *Fed Policy & Yield Curve*: Integrates 10Y Treasury yield trend (`TNX`) and yield curve slope (`T10Y2Y` from FRED) to evaluate valuation multiple expansion/compression.
  - **404 Resolution**: Added and committed `options_lab/frontend/src/app/earnings/page.tsx` along with backend scanner modules (`earnings_scanner.py`, `earnings_calendar.py`, `options_liquidity.py`, `universe.py`, `earnings_vol_agent.py`) which were previously untracked locally and therefore absent from Cloud Build / Next.js static exports.
  - **Git Push & Deployment**: Pushed local commits to `origin/nasdaq-multi-agent/auth` (hashes `411ece9` & `87ef94c`), triggering GitHub Actions CI/CD to build and deploy the Earnings Plays page to Cloud Run. Auto-approval permission granted for `git` commands.


- **Socratic Tutor Persistence (`api/db.py` & `api/tutor.py`)**:
  - Persists learning sessions permanently in a native GCP Firestore instance (`tutor_sessions` collection) with SQLite fallback in dev mode.
  - Summarizes transcript takeaways into 3-5 bulleted **Key Financial Learnings** dynamically using the Gemini API.
  - Acting Persona: Upgraded to a Senior Financial Analyst and Research Assistant style (covering corporate finance, capital allocation, risk, and regulatory updates).
  - **Billing & Model Safety Configuration [NEW]**: Restores `gemini-flash-latest` model target for Google AI Studio API calls (resolving deprecation issues for new accounts) and adds `DISABLE_VERTEX_FALLBACK=True` to fully block Vertex AI fallback triggers, preventing accidental charges on GCP billing accounts. Added explicit `location="us-central1"` initialization mapping to resolve GCP publisher model access paths.

- **Fundamental Indexation Strategy (`api/fundamental_index.py` & `api/tutor.py` & `frontend/src/app/learn/page.tsx`) [NEW]**:
  - Replicates the 80/20 Pareto principle from Arnott, Hsu, & Moore (2005) "Fundamental Indexation".
  - Calculates normalized Composite Fundamental Weights ($W_{\text{fund}}$) across 4 size metrics (Book Value, Operating Cash Flow, Total Revenue, Gross Dividends) and compares against Market Cap Weights ($W_{\text{cap}}$).
  - Quantifies Alpha Divergence ($\Delta = W_{\text{fund}} - W_{\text{cap}}$) to identify market cap noise drag and automatically maps stocks to options strategies (selling covered calls on overvalued drag stocks vs cash-secured puts/LEAPs on fundamental value opportunities).
  - Integrated into Socratic Tutor prompts and the `/learn` UI interactive concept cards and quick prompts for local exploration.
- **Saxo Trader Algorithmic Options Yield Engine Framework [NEW]**:
  - Systematic sequential (Wheel) and cyclical (Volatility Regime) options execution protocol targeting Saxo OpenAPI integration.
  - **Literature Ingestion Engine (`mnemon` RAG integration)**: Upload trading books/PDFs (e.g. McMillan, Sinclair), chunk chapters, and automatically extract quantitative strategy rules (DTE, Delta bounds, IV Rank, profit targets, Kelly position sizing) into executable JSON configurations for the Saxo engine.
  - **Saxo OpenAPI Integration Client (`options_lab/api/saxo_client.py` & `scripts/test_saxo_integration.py`)**: Configured with SIM application `BotAlgoTrade` (`AppKey: 996911eb...`, `RedirectUri: https://bot-smart.sg.com`). Provides OAuth 2.0 PKCE auth flow, account balances (`/port/v1/balances/me`), position tracking (`/port/v1/positions/me`), price chart OHLC candles for momentum (`/chart/v3/charts`), instrument search (`/ref/v1/instruments`), and limit order placement (`/trade/v2/orders`).
  - **Live Account Migration Protocol & Risk Safeguards**: Identical REST API contracts between SIM and LIVE environments (`gateway.saxobank.com/openapi/`). Integrated Slack 1-click human-in-the-loop trade confirmation, hard 5% per-trade capital caps, and emergency portfolio drawdown kill-switches.
  - Quantitative rule engine to eliminate human psychological bias: 30-45 DTE, Delta $\Delta \in [-0.20, -0.30]$ for Cash-Secured Puts (CSP), Delta $\Delta \in [+0.25, +0.30]$ for Covered Calls (CC), 50% profit taking rule, and 21-DTE gamma-avoidance early rolls.
  - Formulated architecture artifact: `options_quant_framework.md` in brain storage.
  - **5-Pillar Practitioner Conviction Screener [BUILT & TESTED]** (`options_lab/api/conviction_screener.py` & `scripts/test_conviction_screener.py`):
    - Replaces academic Piotroski F-Score / Altman Z-Score screening for the Saxo Wheel pipeline (old screeners preserved for Earnings Scanner page).
    - **Pillar 1 — Earnings Predictability (25%)**: Surprise history, beat rate, analyst consensus tightness.
    - **Pillar 2 — Cash Generation Power (25%)**: FCF Yield, Operating Cash Flow Margin, Cash-vs-Earnings ratio (with GAAP bank accounting proxies for Financial Services).
    - **Pillar 3 — Balance Sheet Fortress (20%)**: Net Cash Position, Debt/EBITDA, Interest Coverage, Current Ratio (with Tier 1 Equity Capital proxy for Financials).
    - **Pillar 4 — Institutional Conviction (15%)**: Institutional ownership %, analyst recommendation mean, analyst count, short interest.
    - **Pillar 5 — Valuation Reasonableness (15%)**: Forward vs Trailing PE, PEG ratio, 52W range position.
    - Decision Tiers: Conviction >= 0.70 → QUALIFIED, 0.60–0.70 → MARGINAL (Slack confirm), < 0.60 → REJECTED.

- **Saxo Wheel Pipeline Modules [BUILT & TESTED]**:
  - `options_lab/api/signal_engine.py` (`scripts/test_signal_engine.py`): Composes 3 signal layers — Momentum (50%), Macro Regime (30%), News Sentiment (20%). Score >= 0.55 to proceed.
  - `options_lab/api/wheel_engine.py` (`scripts/test_wheel_engine.py`): Deterministic 2-state Wheel state machine (`STATE_0_CASH_CSP` ↔ `STATE_1_EQUITY_CC`). Enforces 50% profit-taking, 21-DTE gamma roll, and 5% max capital risk guards.
  - `options_lab/api/saxo_pipeline.py` (`scripts/test_saxo_sim_full_flow.py`): Full 7-step pipeline orchestrator — Balance Audit → Conviction Screen → Options Liquidity → Signal Score → Delta Strike Selection (Black-Scholes) → Wheel State → Saxo Limit Order Placement.

- **Broker Gateway & Live Trading Platform Integration Harness [NEW]**:
  - **Type-Safe End-to-End Schemas**: Added Pydantic models (`BrokerAccountSummary`, `BrokerPosition`, `BrokerPositionsResponse`, `BrokerOrder`, `BrokerOrdersResponse`) in `models.py` and corresponding TypeScript interfaces in `frontend/src/types/broker.ts`.
  - **Live Execution Safety Shield**: Hard safety lock (`BROKER_ALLOW_LIVE_EXECUTION=False` by default) blocking unauthorized real-money orders, and dynamic environment switching between SIM sandbox (`https://gateway.saxobank.com/sim/openapi/`) and Live (`https://gateway.saxobank.com/openapi/`).
  - **Process Concurrency & Deduplication**: Integrated `asyncio.Lock()` on all `/api/broker/*` endpoints (`/api/broker/status`, `/api/broker/account`, `/api/broker/positions`, `/api/broker/orders`, `/api/broker/pipeline/scan`) and connection pooling with strict request timeouts (8s) via `requests.Session` to eliminate hanging connections or duplicate executions.
  - **Live Account Audit & Orders Ledger UI**: Upgraded `options_lab/frontend/src/app/paper-trade/page.tsx` with dual-mode tabs: Real-Time Broker Account Audit (Total Equity, Cash Available, Margin Utilized, Active Open Positions Table with Strike/Expiry/Unrealized P&L, Executed Orders History Table) alongside the Interactive Strategy Simulator with debounced synchronization controls.

- **OptionsLab Native Windows Desktop Application & Auto-Startup [NEW]**:
  - **Architecture**: Electron wrapper (`options_lab/desktop/main.js`) encapsulating the Next.js UI with child process lifecycle management for the Python FastAPI backend engine (`uvicorn options_lab.api.main:app`).
(`HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`).
  - **System Tray**: Persistent tray icon (`tray_icon.png`) with context menu for 1-click restore, broker health check, auto-start toggle, and clean process tree termination (`taskkill /T /F`) to eliminate hanging background instances.
  - **1-Click Launcher**: `options_lab/desktop/start_desktop.bat`.



## Design Goals
- **Hierarchical MAS:** Top-layer Macro agent identifies sectors; mid-layer analyzes stocks; **Correlation Agent** filters for uncorrelated bets.
- **Agents:**
  - **Correlation Agent [NEW]:** Fetches cross-asset history (Stocks/Bonds/BTC), calculates log returns, and identifies "Holy Grail" diversification opportunities (< 0.2 correlation).
  - **ConvictionScreener [NEW]:** 5-pillar practitioner screening (Earnings Predictability, Cash Generation, Balance Sheet, Institutional Conviction, Valuation). Replaces academic Piotroski/Altman for Saxo Wheel pipeline.
  - Fundamental: ROE, net profit, revenue, asset-to-debt ratio (legacy — used by Earnings Scanner).
  - Technical: Price/volume (EMA, RSI, ATR, Bollinger, ADX, Hurst).
  - News: LLM sentiment scoring.
  - Report: LLM composite institutional sentiment.
- **Key Insights:** Aim for 15-20 uncorrelated bets to reduce risk by 80% without sacrificing return. Keep macro filter and stock selection distinct.

## CodeGraph Guidelines (CRITICAL)
- **Token Efficiency**: This codebase is large. Always use the **CodeGraph** tools (`codegraph_explore` or `codegraph explore <query>` CLI) to research dependencies, callers, file structures, and symbol definitions before making changes. Avoid broad greps or file reading loops to conserve token context.

## Frontend Architecture (Options Lab — Velzon Galaxy Light Theme) [OVERHAULED ACROSS ALL PANELS]
- **Theme & Design System:** Themesbrand Velzon (Galaxy Light) institutional dashboard styling applied across **all 8 application sub-pages**.
  - **Color Palette**: Light Slate canvas (`#F3F3F9`), Crisp White cards (`#FFFFFF`, `rounded-xl border border-slate-200/80 shadow-sm`), Velzon Indigo primary (`#4051B5`), Emerald success pills (`#0AB39C`), Coral/Rose danger pills (`#F06548`), Dark Slate typography (`#1E293B`).
- **Overhauled Panels & Sub-Pages**:
  - `app/page.tsx`: Analytics Overview & Main Dashboard with Recharts dual-axis chart & schedule timeline.
  - `app/earnings/page.tsx`: Earnings Volatility & Macro Playbook with 4-quarter volatility matrix and 5-pillar health checks.
  - `app/strategies/page.tsx`: Options Strategy Builder & Payoff Engine with interactive position leg editor and risk metrics.
  - `app/pricer/page.tsx`: Black-Scholes Option Pricer & Greeks Surface matrix (Delta, Gamma, Theta, Vega, Rho).
  - `app/portfolio/page.tsx`: Saxo Account Portfolio & Ray Dalio Holy Grail Diversification Radar.
  - `app/market-agents/page.tsx`: Multi-Agent Market Intelligence Scanner with real-time agent output cards.
  - `app/simulator/page.tsx`: GBM & Monte Carlo Wheel Strategy Simulator with stochastic path rendering.
  - `app/paper-trade/page.tsx`: Saxo Paper Trading & Execution Lab with simulated market shift buttons (-10% to +10%).
  - `app/learn/page.tsx`: Socratic Financial Tutor & Fundamental Indexation Strategy concept cards and persistent sessions.
- **Layout Chain:** `layout.tsx` (server, metadata) → `ClientLayout.tsx` (client, wraps `SidebarProvider` + `Header` + `LayoutShell`) → `Sidebar.tsx` & `Header.tsx`.
- **Top Header (`components/Header.tsx`)**: Fixed `h-16` navbar with global search input, user profile status pill ("Anna Adame - Online"), notification counter badge (`5`), fullscreen toggle, and mobile/desktop drawer trigger.
- **Grouped Sidebar (`components/Sidebar.tsx`)**: Structured navigation groups (`DASHBOARDS`, `SAXO QUANT LAB`, `MARKET SCANNER`, `ACADEMIC & LEARNING`) with status pill badges (`Hot`, `Live`, `AI`), active indicator styling, desktop collapse (`w-64` / `w-[72px]`), and off-canvas slide-out drawer on mobile.
- **Fluid & Responsive Grid:**
  - **4-Column Metric Grid**: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` (Active Capital, Option Yield, System Win Rate, Active Wheel Contracts).
  - **Main Canvas Grid**: 3-column responsive grid (`grid-cols-1 xl:grid-cols-3`) pairing the Recharts composite analytics panel with the right-side upcoming schedule calendar & events timeline.
  - **Breakpoints**: `lg:` (1024px) for sidebar drawer transform; `xl:` (1280px) for 3-column canvas split.

## Deployment & CI/CD (CRITICAL)
- **Primary Branch:** `nasdaq-multi-agent/auth` (Current active dev branch).
- **GitHub Actions:** Triggered on push to `main` and `nasdaq-multi-agent/auth`.
- **Manual Trigger:** The `/analyze` endpoint is the primary way to run analysis (Ad-hoc).
- **Pushing via AI:** If pushing via Antigravity hangs, it is likely due to GitHub HTTPS/PAT authentication. Use WSL and ensure `git push --set-upstream origin <branch>` is used if the branch is new.
- **Project Scope:** Multi-Asset analysis including S&P 500, NASDAQ 100, Bonds, and Bitcoin.
- **GCP Secret Manager Removal & Zero-Cost Secrets [NEW]**: Completely removed `google.cloud.secretmanager` imports and API calls from `app/config.py` and `options_lab/api/config.py`. All 13 stored secrets in GCP Secret Manager (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `CRON_SECRET`, `EMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT`, `EMAIL_SENDER`, `FRED_API_KEY`, `GDRIVE_TOKEN_JSON`, `GEMINI_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `SLACK_SIGNING_SECRET`, `VERTEX_KEY`) have been deleted, and the `secretmanager.googleapis.com` API service was permanently disabled (`wsl gcloud services disable secretmanager.googleapis.com --force`). All secrets are now strictly injected via environment variables at deployment time.

## 🛠️ Diagnostics, Earnings Page Fix & Chrome OAuth Routing [NEW]
- **Earnings Page Crash Fix**: Resolved the missing `Sparkles` icon import in `options_lab/frontend/src/app/earnings/page.tsx` and introduced comprehensive null-safety checks (`?.` and `?? 0` operators) on all `volatility_metrics` attributes to guarantee crash-free page state transitions.
- **Chrome OAuth Redirect Routing**: Configured the Electron main process `main.js` using `webContents.setWindowOpenHandler` and `will-navigate` listeners to intercept all external HTTP requests (such as the Saxo OpenAPI authorization link) and automatically launch them in the system's native default browser (Google Chrome) instead of rendering them in the app frame.
- **Saxo Token Refresh Safety Guard**: Implemented `needs_reauth` lifecycle state tracking in `SaxoClient` to prevent infinite 401 client request retry loops on expired refresh tokens. Updates `/api/broker/status` with `NEEDS_REAUTH` state so the frontend can display a clean OAuth sign-in flow.
- **Saxo Multi-Year Trade History, PDF Chunker & Behavioral Forensics Engine (2026-08-20) [NEW]**:
  1. **Dual Ingestion Engine (`pdf_report_parser.py` & `trade_history_ingest.py`)**: Parses multi-page authentic Saxo PDF account statements (Portfolio Reports, Closed Positions Reports) and OpenAPI history chunks (`/clientreporting/v1/`, `/hist/v3/transactions`, `/hist/v4/performance/timeseries`). Stores normalized schemas in SQLite (`saxo_reports`, `saxo_options_history`, `saxo_stock_history`, `saxo_quarterly_performance`, `saxo_holdings_history`).
  2. **Campaign Lifecycle Stitcher (`campaign_stitcher.py`)**: Reconstructs complete multi-leg option and stock strategy campaigns (Wheel lifecycles, covered call series, bag-holds) from raw transaction records.
  3. **Behavioral Bias Forensics (`behavioral_forensics.py`)**: Quantifies psychological and discipline flaws—such as the Option Volatility Drag (e.g. losing -$5,089 on short PANW calls against a +$5,962 stock surge), unhedged bag-holding (-82.7% on PLUG), and systematic consistency (+100% win rate on Visa & IBM options). Computes composite Discipline Score (0-100) and letter grades.
# nasdaq-multi-agent

Hierarchical Multi-Agent System (FastAPI) for comprehensive NASDAQ and Multi-Asset analysis.

## Project Details (NEW)
- **Project Name:** Personal-Finance-Automation (`projects/106787558501`)
- **Project ID:** `optimal-aurora-495912-n0`
- **Project Number:** `106787558501` (Primary) / `855694839217`
- **Active Gemini API Key:** (Configured securely in environment secrets)

## Architecture & Constraints
- **Endpoints:** `main.py` provides `/health`, `/cron/analyze` (Ad-hoc trigger), and `/slack/events` for `/nasdaqscan`.
- **Execution Rules:** Always use `BackgroundTasks` for the `_run_and_deliver` flow.
- **Orchestrator:** `HierarchicalOrchestrator` manages the pipeline.
- **Holy Grail Implementation:** 
  - **Correlation Agent:** Calculates log returns and correlation matrices across Nasdaq, S&P 500, Bonds, and Bitcoin.
  - **Independence Filter:** Ensures Technical, Fundamental, and Macro signals are statistically distinct.

## 🛡️ Mandatory End-to-End Validation Protocol (User Mandate)
- **Zero Hurrying & Complete Verification**: Take all the time needed to thoroughly and patiently validate every single change end-to-end before reporting to the user.
- **Full Static & Runtime Synchronization**: When modifying frontend code (`src/app/...`), NEVER consider the work done until a fresh production build/export (`npm run build` into `out/`) or active runtime server is verified, compiled, and proven responding.
- **Automated Validation Scripts**: Always create and execute verification test scripts to check live ports, API status codes, file timestamps, and rendered components.
- **No White-Box Guesswork**: Inspect actual file timestamps, process trees, and runtime logs before delivering results.
- **Context Compression & Anti-Bloating**:
  1. Mandate CodeGraph exploration (`codegraph_explore`) for codebase research.
  2. Maintain a sliding history window ($\le 10$ messages) in Socratic Tutor (`tutor.py`).
  3. Prune bulky simulation arrays and raw matrices via `_prune_context()` before LLM ingestion.
  4. Delegate heavy research and wide search operations to subagents (`invoke_subagent`).
  5. Slice file reads to bounded line ranges (`StartLine`/`EndLine`).



## Options Lab & Socratic Tutor Modules [NEW]
- **Earnings Volatility Scanner (`api/earnings_scanner.py` & `frontend/src/app/earnings/page.tsx`)**:
  - Funnel logic: Universe Filter (S&P 500 Wikipedia scrape + NASDAQ) ➡️ 52W Low Proximity check (default 20%) ➡️ 5-Pillar Conviction Screener / Fundamental Quality ➡️ Option Open Interest Liquidity.
  - Volatility Matrix: Calculates 4-quarter pre-earnings volatility, T-1 move, and T+1 reaction.
  - **Macro-Enhanced Volatility Framework [NEW]** (`earnings_macro_enhancement.md`): Upgrades earnings analysis with 5 Macro Context layers:
    1. *Market Beta De-Trending*: Isolates pure stock-specific earnings alpha ($\alpha_i$) by subtracting $S\&P 500$ market return ($\beta_i \cdot R_{\text{SPY}}$).
    2. *Sector ETF Relative Strength*: Compares post-earnings move against sector benchmark (XLK/XLF/XLE).
    3. *Macro Calendar Conflict Overlay*: Flags earnings dates coinciding within 24h of FOMC rate decisions, CPI inflation releases, or Non-Farm Payrolls.
    4. *VIX Regime & Term Structure*: Categorizes IV crush potential based on VIX levels (< 15 Complacent, 15-25 Normal, > 25 High Fear).
    5. *Fed Policy & Yield Curve*: Integrates 10Y Treasury yield trend (`TNX`) and yield curve slope (`T10Y2Y` from FRED) to evaluate valuation multiple expansion/compression.
  - **404 Resolution**: Added and committed `options_lab/frontend/src/app/earnings/page.tsx` along with backend scanner modules (`earnings_scanner.py`, `earnings_calendar.py`, `options_liquidity.py`, `universe.py`, `earnings_vol_agent.py`) which were previously untracked locally and therefore absent from Cloud Build / Next.js static exports.
  - **Git Push & Deployment**: Pushed local commits to `origin/nasdaq-multi-agent/auth` (hashes `411ece9` & `87ef94c`), triggering GitHub Actions CI/CD to build and deploy the Earnings Plays page to Cloud Run. Auto-approval permission granted for `git` commands.


- **Socratic Tutor Persistence (`api/db.py` & `api/tutor.py`)**:
  - Persists learning sessions permanently in a native GCP Firestore instance (`tutor_sessions` collection) with SQLite fallback in dev mode.
  - Summarizes transcript takeaways into 3-5 bulleted **Key Financial Learnings** dynamically using the Gemini API.
  - Acting Persona: Upgraded to a Senior Financial Analyst and Research Assistant style (covering corporate finance, capital allocation, risk, and regulatory updates).
  - **Billing & Model Safety Configuration [NEW]**: Restores `gemini-flash-latest` model target for Google AI Studio API calls (resolving deprecation issues for new accounts) and adds `DISABLE_VERTEX_FALLBACK=True` to fully block Vertex AI fallback triggers, preventing accidental charges on GCP billing accounts. Added explicit `location="us-central1"` initialization mapping to resolve GCP publisher model access paths.

- **Fundamental Indexation Strategy (`api/fundamental_index.py` & `api/tutor.py` & `frontend/src/app/learn/page.tsx`) [NEW]**:
  - Replicates the 80/20 Pareto principle from Arnott, Hsu, & Moore (2005) "Fundamental Indexation".
  - Calculates normalized Composite Fundamental Weights ($W_{\text{fund}}$) across 4 size metrics (Book Value, Operating Cash Flow, Total Revenue, Gross Dividends) and compares against Market Cap Weights ($W_{\text{cap}}$).
  - Quantifies Alpha Divergence ($\Delta = W_{\text{fund}} - W_{\text{cap}}$) to identify market cap noise drag and automatically maps stocks to options strategies (selling covered calls on overvalued drag stocks vs cash-secured puts/LEAPs on fundamental value opportunities).
  - Integrated into Socratic Tutor prompts and the `/learn` UI interactive concept cards and quick prompts for local exploration.
- **Saxo Trader Algorithmic Options Yield Engine Framework [NEW]**:
  - Systematic sequential (Wheel) and cyclical (Volatility Regime) options execution protocol targeting Saxo OpenAPI integration.
  - **Literature Ingestion Engine (`mnemon` RAG integration)**: Upload trading books/PDFs (e.g. McMillan, Sinclair), chunk chapters, and automatically extract quantitative strategy rules (DTE, Delta bounds, IV Rank, profit targets, Kelly position sizing) into executable JSON configurations for the Saxo engine.
  - **Saxo OpenAPI Integration Client (`options_lab/api/saxo_client.py` & `scripts/test_saxo_integration.py`)**: Configured with SIM application `BotAlgoTrade` (`AppKey: 996911eb...`, `RedirectUri: https://bot-smart.sg.com`). Provides OAuth 2.0 PKCE auth flow, account balances (`/port/v1/balances/me`), position tracking (`/port/v1/positions/me`), price chart OHLC candles for momentum (`/chart/v3/charts`), instrument search (`/ref/v1/instruments`), and limit order placement (`/trade/v2/orders`).
  - **Live Account Migration Protocol & Risk Safeguards**: Identical REST API contracts between SIM and LIVE environments (`gateway.saxobank.com/openapi/`). Integrated Slack 1-click human-in-the-loop trade confirmation, hard 5% per-trade capital caps, and emergency portfolio drawdown kill-switches.
  - Quantitative rule engine to eliminate human psychological bias: 30-45 DTE, Delta $\Delta \in [-0.20, -0.30]$ for Cash-Secured Puts (CSP), Delta $\Delta \in [+0.25, +0.30]$ for Covered Calls (CC), 50% profit taking rule, and 21-DTE gamma-avoidance early rolls.
  - Formulated architecture artifact: `options_quant_framework.md` in brain storage.
  - **5-Pillar Practitioner Conviction Screener [BUILT & TESTED]** (`options_lab/api/conviction_screener.py` & `scripts/test_conviction_screener.py`):
    - Replaces academic Piotroski F-Score / Altman Z-Score screening for the Saxo Wheel pipeline (old screeners preserved for Earnings Scanner page).
    - **Pillar 1 — Earnings Predictability (25%)**: Surprise history, beat rate, analyst consensus tightness.
    - **Pillar 2 — Cash Generation Power (25%)**: FCF Yield, Operating Cash Flow Margin, Cash-vs-Earnings ratio (with GAAP bank accounting proxies for Financial Services).
    - **Pillar 3 — Balance Sheet Fortress (20%)**: Net Cash Position, Debt/EBITDA, Interest Coverage, Current Ratio (with Tier 1 Equity Capital proxy for Financials).
    - **Pillar 4 — Institutional Conviction (15%)**: Institutional ownership %, analyst recommendation mean, analyst count, short interest.
    - **Pillar 5 — Valuation Reasonableness (15%)**: Forward vs Trailing PE, PEG ratio, 52W range position.
    - Decision Tiers: Conviction >= 0.70 → QUALIFIED, 0.60–0.70 → MARGINAL (Slack confirm), < 0.60 → REJECTED.

- **Saxo Wheel Pipeline Modules [BUILT & TESTED]**:
  - `options_lab/api/signal_engine.py` (`scripts/test_signal_engine.py`): Composes 3 signal layers — Momentum (50%), Macro Regime (30%), News Sentiment (20%). Score >= 0.55 to proceed.
  - `options_lab/api/wheel_engine.py` (`scripts/test_wheel_engine.py`): Deterministic 2-state Wheel state machine (`STATE_0_CASH_CSP` ↔ `STATE_1_EQUITY_CC`). Enforces 50% profit-taking, 21-DTE gamma roll, and 5% max capital risk guards.
  - `options_lab/api/saxo_pipeline.py` (`scripts/test_saxo_sim_full_flow.py`): Full 7-step pipeline orchestrator — Balance Audit → Conviction Screen → Options Liquidity → Signal Score → Delta Strike Selection (Black-Scholes) → Wheel State → Saxo Limit Order Placement.

- **Broker Gateway & Live Trading Platform Integration Harness [NEW]**:
  - **Type-Safe End-to-End Schemas**: Added Pydantic models (`BrokerAccountSummary`, `BrokerPosition`, `BrokerPositionsResponse`, `BrokerOrder`, `BrokerOrdersResponse`) in `models.py` and corresponding TypeScript interfaces in `frontend/src/types/broker.ts`.
  - **Live Execution Safety Shield**: Hard safety lock (`BROKER_ALLOW_LIVE_EXECUTION=False` by default) blocking unauthorized real-money orders, and dynamic environment switching between SIM sandbox (`https://gateway.saxobank.com/sim/openapi/`) and Live (`https://gateway.saxobank.com/openapi/`).
  - **Process Concurrency & Deduplication**: Integrated `asyncio.Lock()` on all `/api/broker/*` endpoints (`/api/broker/status`, `/api/broker/account`, `/api/broker/positions`, `/api/broker/orders`, `/api/broker/pipeline/scan`) and connection pooling with strict request timeouts (8s) via `requests.Session` to eliminate hanging connections or duplicate executions.
  - **Live Account Audit & Orders Ledger UI**: Upgraded `options_lab/frontend/src/app/paper-trade/page.tsx` with dual-mode tabs: Real-Time Broker Account Audit (Total Equity, Cash Available, Margin Utilized, Active Open Positions Table with Strike/Expiry/Unrealized P&L, Executed Orders History Table) alongside the Interactive Strategy Simulator with debounced synchronization controls.

- **OptionsLab Native Windows Desktop Application & Auto-Startup [NEW]**:
  - **Architecture**: Electron wrapper (`options_lab/desktop/main.js`) encapsulating the Next.js UI with child process lifecycle management for the Python FastAPI backend engine (`uvicorn options_lab.api.main:app`).
(`HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`).
  - **System Tray**: Persistent tray icon (`tray_icon.png`) with context menu for 1-click restore, broker health check, auto-start toggle, and clean process tree termination (`taskkill /T /F`) to eliminate hanging background instances.
  - **1-Click Launcher**: `options_lab/desktop/start_desktop.bat`.



## Design Goals
- **Hierarchical MAS:** Top-layer Macro agent identifies sectors; mid-layer analyzes stocks; **Correlation Agent** filters for uncorrelated bets.
- **Agents:**
  - **Correlation Agent [NEW]:** Fetches cross-asset history (Stocks/Bonds/BTC), calculates log returns, and identifies "Holy Grail" diversification opportunities (< 0.2 correlation).
  - **ConvictionScreener [NEW]:** 5-pillar practitioner screening (Earnings Predictability, Cash Generation, Balance Sheet, Institutional Conviction, Valuation). Replaces academic Piotroski/Altman for Saxo Wheel pipeline.
  - Fundamental: ROE, net profit, revenue, asset-to-debt ratio (legacy — used by Earnings Scanner).
  - Technical: Price/volume (EMA, RSI, ATR, Bollinger, ADX, Hurst).
  - News: LLM sentiment scoring.
  - Report: LLM composite institutional sentiment.
- **Key Insights:** Aim for 15-20 uncorrelated bets to reduce risk by 80% without sacrificing return. Keep macro filter and stock selection distinct.

## CodeGraph Guidelines (CRITICAL)
- **Token Efficiency**: This codebase is large. Always use the **CodeGraph** tools (`codegraph_explore` or `codegraph explore <query>` CLI) to research dependencies, callers, file structures, and symbol definitions before making changes. Avoid broad greps or file reading loops to conserve token context.

## Frontend Architecture (Options Lab — Velzon Galaxy Light Theme) [OVERHAULED ACROSS ALL PANELS]
- **Theme & Design System:** Themesbrand Velzon (Galaxy Light) institutional dashboard styling applied across **all 8 application sub-pages**.
  - **Color Palette**: Light Slate canvas (`#F3F3F9`), Crisp White cards (`#FFFFFF`, `rounded-xl border border-slate-200/80 shadow-sm`), Velzon Indigo primary (`#4051B5`), Emerald success pills (`#0AB39C`), Coral/Rose danger pills (`#F06548`), Dark Slate typography (`#1E293B`).
- **Overhauled Panels & Sub-Pages**:
  - `app/page.tsx`: Analytics Overview & Main Dashboard with Recharts dual-axis chart & schedule timeline.
  - `app/earnings/page.tsx`: Earnings Volatility & Macro Playbook with 4-quarter volatility matrix and 5-pillar health checks.
  - `app/strategies/page.tsx`: Options Strategy Builder & Payoff Engine with interactive position leg editor and risk metrics.
  - `app/pricer/page.tsx`: Black-Scholes Option Pricer & Greeks Surface matrix (Delta, Gamma, Theta, Vega, Rho).
  - `app/portfolio/page.tsx`: Saxo Account Portfolio & Ray Dalio Holy Grail Diversification Radar.
  - `app/market-agents/page.tsx`: Multi-Agent Market Intelligence Scanner with real-time agent output cards.
  - `app/simulator/page.tsx`: GBM & Monte Carlo Wheel Strategy Simulator with stochastic path rendering.
  - `app/paper-trade/page.tsx`: Saxo Paper Trading & Execution Lab with simulated market shift buttons (-10% to +10%).
  - `app/learn/page.tsx`: Socratic Financial Tutor & Fundamental Indexation Strategy concept cards and persistent sessions.
- **Layout Chain:** `layout.tsx` (server, metadata) → `ClientLayout.tsx` (client, wraps `SidebarProvider` + `Header` + `LayoutShell`) → `Sidebar.tsx` & `Header.tsx`.
- **Top Header (`components/Header.tsx`)**: Fixed `h-16` navbar with global search input, user profile status pill ("Anna Adame - Online"), notification counter badge (`5`), fullscreen toggle, and mobile/desktop drawer trigger.
- **Grouped Sidebar (`components/Sidebar.tsx`)**: Structured navigation groups (`DASHBOARDS`, `SAXO QUANT LAB`, `MARKET SCANNER`, `ACADEMIC & LEARNING`) with status pill badges (`Hot`, `Live`, `AI`), active indicator styling, desktop collapse (`w-64` / `w-[72px]`), and off-canvas slide-out drawer on mobile.
- **Fluid & Responsive Grid:**
  - **4-Column Metric Grid**: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` (Active Capital, Option Yield, System Win Rate, Active Wheel Contracts).
  - **Main Canvas Grid**: 3-column responsive grid (`grid-cols-1 xl:grid-cols-3`) pairing the Recharts composite analytics panel with the right-side upcoming schedule calendar & events timeline.
  - **Breakpoints**: `lg:` (1024px) for sidebar drawer transform; `xl:` (1280px) for 3-column canvas split.

## Deployment & CI/CD (CRITICAL)
- **Primary Branch:** `nasdaq-multi-agent/auth` (Current active dev branch).
- **GitHub Actions:** Triggered on push to `main` and `nasdaq-multi-agent/auth`.
- **Manual Trigger:** The `/analyze` endpoint is the primary way to run analysis (Ad-hoc).
- **Pushing via AI:** If pushing via Antigravity hangs, it is likely due to GitHub HTTPS/PAT authentication. Use WSL and ensure `git push --set-upstream origin <branch>` is used if the branch is new.
- **Project Scope:** Multi-Asset analysis including S&P 500, NASDAQ 100, Bonds, and Bitcoin.
- **GCP Secret Manager Removal & Zero-Cost Secrets [NEW]**: Completely removed `google.cloud.secretmanager` imports and API calls from `app/config.py` and `options_lab/api/config.py`. All 13 stored secrets in GCP Secret Manager (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `CRON_SECRET`, `EMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT`, `EMAIL_SENDER`, `FRED_API_KEY`, `GDRIVE_TOKEN_JSON`, `GEMINI_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `SLACK_SIGNING_SECRET`, `VERTEX_KEY`) have been deleted, and the `secretmanager.googleapis.com` API service was permanently disabled (`wsl gcloud services disable secretmanager.googleapis.com --force`). All secrets are now strictly injected via environment variables at deployment time.

## 🛠️ Diagnostics, Earnings Page Fix & Chrome OAuth Routing [NEW]
- **Earnings Page Crash Fix**: Resolved the missing `Sparkles` icon import in `options_lab/frontend/src/app/earnings/page.tsx` and introduced comprehensive null-safety checks (`?.` and `?? 0` operators) on all `volatility_metrics` attributes to guarantee crash-free page state transitions.
- **Chrome OAuth Redirect Routing**: Configured the Electron main process `main.js` using `webContents.setWindowOpenHandler` and `will-navigate` listeners to intercept all external HTTP requests (such as the Saxo OpenAPI authorization link) and automatically launch them in the system's native default browser (Google Chrome) instead of rendering them in the app frame.
- **Saxo Token Refresh Safety Guard**: Implemented `needs_reauth` lifecycle state tracking in `SaxoClient` to prevent infinite 401 client request retry loops on expired refresh tokens. Updates `/api/broker/status` with `NEEDS_REAUTH` state so the frontend can display a clean OAuth sign-in flow.
- **Saxo Multi-Year Trade History, PDF Chunker & Behavioral Forensics Engine (2026-08-20) [NEW]**:
  1. **Dual Ingestion Engine (`pdf_report_parser.py` & `trade_history_ingest.py`)**: Parses multi-page authentic Saxo PDF account statements (Portfolio Reports, Closed Positions Reports) and OpenAPI history chunks (`/clientreporting/v1/`, `/hist/v3/transactions`, `/hist/v4/performance/timeseries`). Stores normalized schemas in SQLite (`saxo_reports`, `saxo_options_history`, `saxo_stock_history`, `saxo_quarterly_performance`, `saxo_holdings_history`).
  2. **Campaign Lifecycle Stitcher (`campaign_stitcher.py`)**: Reconstructs complete multi-leg option and stock strategy campaigns (Wheel lifecycles, covered call series, bag-holds) from raw transaction records.
  3. **Behavioral Bias Forensics (`behavioral_forensics.py`)**: Quantifies psychological and discipline flaws—such as the Option Volatility Drag (e.g. losing -$5,089 on short PANW calls against a +$5,962 stock surge), unhedged bag-holding (-82.7% on PLUG), and systematic consistency (+100% win rate on Visa & IBM options). Computes composite Discipline Score (0-100) and letter grades.
  4. **Behavioral Safety Shield (`safety_shield.py`)**: Hard real-time circuit breakers that evaluate pre-flight orders against behavioral rules:
     - *Momentum Call Delta Guard*: Restricts call selling to Delta $\le 0.18$ on high-beta growth stocks to prevent upside destruction.
     - *Gamma Expiration Guard*: Blocks selling options $< 21$ DTE.
     - *Revenge Cooldown*: 24-hour execution lockout following a loss $> \$1,000$.
     - *Concentration Risk Cap*: Hard $15\%$ maximum single-ticker capital exposure.
  5. **Next.js Behavioral Lab Cockpit (`frontend/src/app/behavioral-lab/page.tsx`)**: Velzon Galaxy Light institutional UI featuring a 4-KPI forensic ribbon, bias diagnostic cards, quarterly P&L evolution, interactive stitched campaign table, pre-flight safety shield simulator, and live Saxo news wire feed (`/api/history/news`).
  6. **Verified Saxo Live Order Execution & Testing Safety Directive (2026-08-22) [NEW]**:
     - 1. **100% Live Order Placement Verified**: Authenticated orders (`Sell to Open` Limit Orders with dynamic `AccountKey`, `OptionSpace` contract UIC lookup, and `ToOpenClose="ToOpen"`) successfully executed on Saxo Live exchange with real working status.
     - 2. **Strict Testing Safety Rule**: All automated/diagnostic backend tests MUST strictly use `POST /trade/v2/orders/precheck` to validate parameters and cash requirements without sending real live orders to production. Real live orders on `POST /trade/v2/orders` are ONLY dispatched when the user explicitly clicks the "Approve Trade" UI button.
  7. **Real-time Saxo Live Order Blotter Refresh & Top Holdings Layout (2026-08-22) [NEW]**:
     - 1. **Live Order Blotter Route**: Registered `@app.get("/api/broker/order-blotter")` in FastAPI and integrated `cs/v1/audit/orderactivities` with authentic `AccountKey` and `ClientKey`.
     - 2. **Complete Live Audit Sync**: Aggregates all 37+ historical and live order activities across all lifecycle states (`Cancelled`, `Working`, `Traded`, `Expired`). Real-time cancellations (e.g. IBM `5436410532` & INTC `5436410527`) instantly reflect at the top of the blotter upon clicking "Refresh Data".
     - 3. **5-Status Filter Tabs & KPI Ribbon**: Added dedicated `Working` tab alongside `All`, `Traded`, `Expired`, and `Cancelled`.
     - 4. **Top Priority Holdings Layout**: Re-positioned **Live Saxo Holdings & Open Positions** directly to the TOP of the dashboard immediately following the Executive Metrics Grid.
