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

## Design Goals
- **Hierarchical MAS:** Top-layer Macro agent identifies sectors; mid-layer analyzes stocks; **Correlation Agent** filters for uncorrelated bets.
- **Agents:**
  - **Correlation Agent [NEW]:** Fetches cross-asset history (Stocks/Bonds/BTC), calculates log returns, and identifies "Holy Grail" diversification opportunities (< 0.2 correlation).
  - Fundamental: ROE, net profit, revenue, asset-to-debt ratio.
  - Technical: Price/volume (EMA, RSI, ATR, Bollinger, ADX, Hurst).
  - News: LLM sentiment scoring.
  - Report: LLM composite institutional sentiment.
- **Key Insights:** Aim for 15-20 uncorrelated bets to reduce risk by 80% without sacrificing return. Keep macro filter and stock selection distinct.

## Deployment & CI/CD (CRITICAL)
- **Primary Branch:** `nasdaq-multi-agent/auth` (Current active dev branch).
- **GitHub Actions:** Triggered on push to `main` and `nasdaq-multi-agent/auth`.
- **Manual Trigger:** The `/analyze` endpoint is the primary way to run analysis (Ad-hoc).
- **Pushing via AI:** If pushing via Antigravity hangs, it is likely due to GitHub HTTPS/PAT authentication. Use WSL and ensure `git push --set-upstream origin <branch>` is used if the branch is new.
- **Project Scope:** Multi-Asset analysis including S&P 500, NASDAQ 100, Bonds, and Bitcoin.

