# nasdaq-multi-agent

Hierarchical Multi-Agent System (FastAPI) for comprehensive NASDAQ analysis.

## Architecture & Constraints
- **Endpoints:** `main.py` provides `/health`, `/cron/analyze` (for Scheduler), and `/slack/events` for `/nasdaqscan`.
- **Execution Rules:** Always use `BackgroundTasks` for the `_run_and_deliver` flow to comply with Slack's 3-second timeout rule.
- **Orchestrator:** `HierarchicalOrchestrator` manages the multi-agent execution pipeline. Deliveries include both Slack Block Kit messages and HTML Emails (via `formatter.py`).
- **Security:** Secure endpoints via `_verify_slack_signature` (HMAC-SHA256) and `_verify_cron_secret` helpers.

## Original Design Goals
- **Hierarchical MAS:** Top-layer Macro agent identifies sectors; mid-layer (Fundamental, Technical, News, Report) analyzes stocks; Portfolio agent dynamically weights via RL; Risk Control agent adjusts exposure.
- **Agents:**
  - Fundamental: ROE, net profit, revenue, asset-to-debt ratio.
  - Technical: Price/volume (EMA, RSI, ATR, Bollinger, ADX, Hurst).
  - News: LLM sentiment scoring.
  - Report: LLM composite institutional sentiment (analyst reports, disclosures).
- **Key Insights:** Keep macro filter and stock selection distinct. Embed LLMs within context-aware agents. Modular design for governance.
