# nasdaq-multi-agent

Hierarchical Multi-Agent System (FastAPI) for comprehensive NASDAQ and Multi-Asset analysis.

## Project Details (NEW)
- **Project Name:** Personal-Finance-Automation
- **Project ID:** `optimal-aurora-495912-n0`
- **Project Number:** `855694839217`

## Architecture & Constraints
- **Endpoints:** `main.py` provides `/health`, `/cron/analyze` (Ad-hoc trigger), and `/slack/events` for `/nasdaqscan`.
- **Execution Rules:** Always use `BackgroundTasks` for the `_run_and_deliver` flow.
- **Orchestrator:** `HierarchicalOrchestrator` manages the pipeline.
- **Holy Grail Implementation:** 
  - **Correlation Agent:** Calculates log returns and correlation matrices across Nasdaq, S&P 500, Bonds, and Bitcoin.
  - **Independence Filter:** Ensures Technical, Fundamental, and Macro signals are statistically distinct.

## Options Lab & Socratic Tutor Modules [NEW]
- **Earnings Volatility Scanner (`api/earnings_scanner.py` & `frontend/src/app/earnings/page.tsx`)**:
  - Funnel logic: Universe Filter (S&P 500 Wikipedia scrape + NASDAQ) ➡️ 52W Low Proximity check (default 20%) ➡️ Exhaustive Fundamentals check (passes if >= 75% of available yfinance metrics like Piotroski, ROE >= 12%, Operating Margin >= 10%, Debt/Equity <= 1.5, Altman Z >= 1.8 pass) ➡️ Option Open Interest Liquidity (>= 5,000 contracts).
  - Volatility Matrix: Calculates 4-quarter pre-earnings volatility, T-1 move, and T+1 reaction.
  - **404 Resolution**: Added and committed `options_lab/frontend/src/app/earnings/page.tsx` along with backend scanner modules (`earnings_scanner.py`, `earnings_calendar.py`, `options_liquidity.py`, `universe.py`, `earnings_vol_agent.py`) which were previously untracked locally and therefore absent from Cloud Build / Next.js static exports.
  - **Git Push & Deployment**: Pushed local commits to `origin/nasdaq-multi-agent/auth` (hashes `411ece9` & `87ef94c`), triggering GitHub Actions CI/CD to build and deploy the Earnings Plays page to Cloud Run. Auto-approval permission granted for `git` commands.


- **Socratic Tutor Persistence (`api/db.py` & `api/tutor.py`)**:
  - Persists learning sessions permanently in a native GCP Firestore instance (`tutor_sessions` collection) with SQLite fallback in dev mode.
  - Summarizes transcript takeaways into 3-5 bulleted **Key Financial Learnings** dynamically using the Gemini API.
  - Acting Persona: Upgraded to a Senior Financial Analyst and Research Assistant style (covering corporate finance, capital allocation, risk, and regulatory updates).
  - **Billing & Model Safety Configuration [NEW]**: Restores `gemini-flash-latest` model target for Google AI Studio API calls (resolving deprecation issues for new accounts) and adds `DISABLE_VERTEX_FALLBACK=True` to fully block Vertex AI fallback triggers, preventing accidental charges on GCP billing accounts. Added explicit `location="us-central1"` initialization mapping to resolve GCP publisher model access paths.

## Design Goals
- **Hierarchical MAS:** Top-layer Macro agent identifies sectors; mid-layer analyzes stocks; **Correlation Agent** filters for uncorrelated bets.
- **Agents:**
  - **Correlation Agent [NEW]:** Fetches cross-asset history (Stocks/Bonds/BTC), calculates log returns, and identifies "Holy Grail" diversification opportunities (< 0.2 correlation).
  - Fundamental: ROE, net profit, revenue, asset-to-debt ratio.
  - Technical: Price/volume (EMA, RSI, ATR, Bollinger, ADX, Hurst).
  - News: LLM sentiment scoring.
  - Report: LLM composite institutional sentiment.
- **Key Insights:** Aim for 15-20 uncorrelated bets to reduce risk by 80% without sacrificing return. Keep macro filter and stock selection distinct.

## CodeGraph Guidelines (CRITICAL)
- **Token Efficiency**: This codebase is large. Always use the **CodeGraph** tools (`codegraph_explore` or `codegraph explore <query>` CLI) to research dependencies, callers, file structures, and symbol definitions before making changes. Avoid broad greps or file reading loops to conserve token context.

## Frontend Architecture (Options Lab)
- **Framework:** Next.js (App Router) with static export (`output: 'export'`).
- **Layout Chain:** `layout.tsx` (server, metadata) → `ClientLayout.tsx` (client, wraps `SidebarProvider` + `LayoutShell`) → `Sidebar.tsx`.
- **Mobile Responsiveness:**
  - **Sidebar (`components/Sidebar.tsx`)**: Exports `SidebarProvider` context + `useSidebar` hook. Desktop: fixed sidebar with collapse/expand toggle (72px collapsed / 256px expanded). Mobile: off-canvas drawer with hamburger menu + overlay backdrop. Auto-closes on route change and Escape key.
  - **ClientLayout (`components/ClientLayout.tsx`)**: Client wrapper consuming `useSidebar()` to dynamically set `ml-64` vs `ml-[72px]` on desktop, and `pt-14` (for mobile top bar) with no left margin on mobile.
  - **Key breakpoint:** `lg:` (1024px) — below this, sidebar becomes a slide-out drawer.

## Deployment & CI/CD (CRITICAL)
- **Primary Branch:** `nasdaq-multi-agent/auth` (Current active dev branch).
- **GitHub Actions:** Triggered on push to `main` and `nasdaq-multi-agent/auth`.
- **Manual Trigger:** The `/analyze` endpoint is the primary way to run analysis (Ad-hoc).
- **Pushing via AI:** If pushing via Antigravity hangs, it is likely due to GitHub HTTPS/PAT authentication. Use WSL and ensure `git push --set-upstream origin <branch>` is used if the branch is new.
- **Project Scope:** Multi-Asset analysis including S&P 500, NASDAQ 100, Bonds, and Bitcoin.
- **Secrets:** All secrets (including `GEMINI_API_KEY`) are passed as **Cloud Run environment variables** at deploy time via `--set-env-vars` in deploy scripts and GitHub Actions. The `_get_secret()` helper resolves from `os.getenv()` first, so Secret Manager API is **never called at runtime** — eliminating per-call charges. `DISABLE_VERTEX_FALLBACK=True` is set on all services to block Vertex AI billing leakage.
- **Model:** Default model is `gemini-flash-latest` (Google AI Studio free tier). Configured in deploy scripts, GitHub Actions, and `options_lab/api/config.py`.
- **Cloud Build (Options Lab):** Standardized to use `options_lab/cloudbuild.yaml` instead of inline flags. Uses `logging: CLOUD_LOGGING_ONLY` and `gcloud builds submit ... --suppress-logs` to bypass VPC-SC stream permissions errors in GitHub Actions. explicitly excludes `e2-highcpu-8` to enforce the 120-min daily free tier via `e2-medium`.
- **Deployment Concurrency & Conflict Prevention [NEW]:** Added `concurrency.cancel-in-progress: true` in `.github/workflows/deploy.yml` and replaced `google-github-actions/deploy-cloudrun` action with direct `gcloud run deploy` CLI calls to eliminate resource version (`etag`) conflicts on Cloud Run when rapid back-to-back commits are pushed.

