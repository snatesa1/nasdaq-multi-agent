# 📊 NASDAQ Hierarchical Multi-Agent System

A production-grade, AI-powered market analysis platform that uses a **hierarchical multi-agent architecture** to deliver daily NASDAQ insights via **Slack** and **Email**.

Built with **FastAPI**, **Vertex AI (Gemini)**, and deployed on **Google Cloud Run** with automated CI/CD via **GitHub Actions** and **Workload Identity Federation**.

---

## 🏗️ Architecture

```
                    ┌─────────────────────┐
                    │    Orchestrator      │
                    │  (HierarchicalOrch)  │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐
    │   TIER 1: Macro │             │  TIER 1: FRED   │
    │   (parallel)    │             │  Indicators     │
    └────────┬────────┘             └─────────────────┘
             │
             │  → stock_universe[]
             │
    ┌────────┴────────────────────────┐
    │         TIER 2 (per stock)      │
    │  ┌────────────┐ ┌────────────┐  │
    │  │ Technical  │ │Fundamental │  │
    │  │   Agent    │ │   Agent    │  │
    │  └────────────┘ └────────────┘  │
    └─────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────────────┐
    │   Formatter (Slack + Email)     │
    └─────────────────────────────────┘
```

### Agent Pipeline

| Tier | Agent | Data Source | Purpose |
|------|-------|------------|---------|
| 1 | **Macro Agent** | Google News RSS + Gemini | Analyzes macro headlines, selects sectors, builds stock universe |
| 1 | **FRED Indicators Agent** | FRED API | Tracks key economic indicators (GDP, CPI, unemployment, yield curve) |
| 2 | **Technical Agent** | Alpaca / yfinance | RSI, MACD, Bollinger Bands, volume analysis per stock |
| 2 | **Fundamental Agent** | FMP API | P/E, revenue growth, debt ratios, earnings per stock |
| 3 | Portfolio + Risk | _(Phase 3 — planned)_ | Portfolio weighting and risk adjustment |

---

## 🚀 Features

- 🤖 **Multi-Agent AI** — 4 specialized agents orchestrated in a hierarchical pipeline
- 🧠 **Gemini-Powered** — Vertex AI (Gemini 2.0 Flash Lite) for macro analysis and metric explanations
- 📈 **Real-Time Data** — Alpaca, yfinance, FRED API, Financial Modeling Prep
- 💬 **Slack Integration** — Rich Block Kit messages via `/nasdaqscan` slash command
- 📧 **Email Reports** — Automated HTML email delivery via Gmail SMTP
- ⏰ **Scheduled Runs** — Cloud Scheduler triggers analysis Mon-Fri at 7 PM SGT
- 🔐 **Production Security** — GCP Secret Manager, HMAC signature verification, OIDC auth
- 🚀 **CI/CD** — GitHub Actions with Workload Identity Federation (keyless auth)

---

## 📁 Project Structure

```
nasdaq-multi-agent/
├── app/
│   ├── agents/
│   │   ├── base_agent.py            # Base agent class & AgentResult
│   │   ├── macro_agent.py           # Tier 1: Macro/sector analysis (Gemini)
│   │   ├── fred_indicators_agent.py # Tier 1: FRED economic indicators
│   │   ├── technical_agent.py       # Tier 2: Technical indicators per stock
│   │   ├── fundamental_agent.py     # Tier 2: Fundamental analysis per stock
│   │   └── metric_explainer.py      # LLM-powered metric explanations
│   ├── config.py                    # Settings (Secret Manager + env fallback)
│   ├── data_client.py               # Alpaca / yfinance / FRED data fetchers
│   ├── formatter.py                 # Slack Block Kit + Email HTML formatter
│   ├── main.py                      # FastAPI app (endpoints)
│   └── orchestrator.py              # Hierarchical pipeline coordinator
├── .github/
│   └── workflows/
│       └── deploy.yml               # CI/CD: GitHub Actions → Cloud Run
├── cloudbuild.yaml                  # Cloud Build config (VPC-SC compatible)
├── Dockerfile                       # Python 3.11-slim container
├── requirements.txt                 # Python dependencies
├── deploy_app.sh                    # Manual deployment script
├── setup_gh_actions_sa.sh           # Service account setup for CI/CD
├── upload_secrets.sh                # Upload secrets to GCP Secret Manager
├── init_gcp.sh                      # Initialize GCP APIs
└── destroy_app.sh                   # Teardown script
```

---

## ⚙️ Prerequisites

- **Python** 3.11+
- **Google Cloud** account with billing enabled
- **GitHub** repository
- **API Keys**: Alpaca, FRED, Financial Modeling Prep (FMP)
- **Slack** workspace with a bot app configured

---

## 🛠️ Setup

### 1. Clone & Install

```bash
git clone https://github.com/snatesa1/nasdaq-multi-agent.git
cd nasdaq-multi-agent
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# GCP
GCP_PROJECT_ID=your-project-id

# Data Sources
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
FMP_API_KEY=your-fmp-key
FRED_API_KEY=your-fred-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_CHANNEL_ID=C0XXXXXXXXX

# Email
EMAIL_SENDER=you@gmail.com
EMAIL_APP_PASSWORD=your-gmail-app-password
EMAIL_RECIPIENT=recipient@example.com

# Security
CRON_SECRET=your-random-cron-secret

# AI Model
VERTEX_MODEL=gemini-2.0-flash-lite
```

### 3. Initialize GCP

```bash
# Enable required APIs
bash init_gcp.sh

# Upload secrets to Secret Manager
bash upload_secrets.sh
```

### 4. Run Locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/cron/analyze` | Cloud Scheduler trigger (requires `X-Cron-Secret` header) |
| `POST` | `/slack/events` | Slack `/nasdaqscan` slash command handler |

---

## ☁️ Deployment

### Automated (CI/CD)

Every push to `main` triggers the GitHub Actions pipeline:

1. ✅ Checkout code & install dependencies
2. 🔑 Authenticate via Workload Identity Federation (keyless)
3. 🏗️ Build container image with Cloud Build
4. ☁️ Deploy to Cloud Run
5. ⏰ Create/update Cloud Scheduler job

### Manual

```bash
bash deploy_app.sh
```

### CI/CD Setup (One-Time)

```bash
# Create the deployer service account with required IAM roles
bash setup_gh_actions_sa.sh
```

Then configure these **GitHub Repository Secrets**:

| Secret | Description |
|--------|-------------|
| `WIF_PROVIDER` | Workload Identity Federation provider resource name |
| `WIF_SERVICE_ACCOUNT` | `github-actions-deployer@<project>.iam.gserviceaccount.com` |
| `CRON_SECRET` | Random secret for Cloud Scheduler authentication |
| `SLACK_CHANNEL_ID` | Default Slack channel for scheduled reports |
| `EMAIL_SENDER` | Gmail address for email reports |
| `EMAIL_RECIPIENT` | Recipient email address |
| `VERTEX_MODEL` | Gemini model name (e.g., `gemini-2.0-flash-lite`) |

### Required IAM Roles

The deployer service account needs:

| Role | Purpose |
|------|---------|
| `roles/run.admin` | Deploy Cloud Run services |
| `roles/cloudbuild.builds.editor` | Submit Cloud Build jobs |
| `roles/storage.admin` | Push images to GCR |
| `roles/cloudscheduler.admin` | Manage Cloud Scheduler jobs |
| `roles/secretmanager.secretAccessor` | Access secrets at runtime |
| `roles/iam.serviceAccountUser` | Act as service account for OIDC |
| `roles/run.invoker` | Allow Scheduler to invoke Cloud Run |

---

## 🔒 Security

- **Slack Requests** — Verified via HMAC-SHA256 signature (`X-Slack-Signature`)
- **Cron Requests** — Verified via `X-Cron-Secret` header
- **Secrets** — Stored in GCP Secret Manager (lazy-loaded, env fallback for local dev)
- **CI/CD Auth** — Workload Identity Federation (no JSON keys in GitHub)
- **Cloud Run** — OIDC-authenticated invocation from Cloud Scheduler

---

## 📅 Scheduled Analysis

Cloud Scheduler runs the analysis pipeline **Monday–Friday at 7:00 PM SGT** (11:00 UTC):

```
Schedule: 0 19 * * 1-5
Timezone: Asia/Singapore
Endpoint: POST /cron/analyze
Auth:     OIDC + X-Cron-Secret header
```

---

## 🧪 Local Testing

```bash
# Health check
curl http://localhost:8080/health

# Trigger analysis manually
curl -X POST http://localhost:8080/cron/analyze \
  -H "X-Cron-Secret: your-cron-secret"
```

---

## 📋 Roadmap

- [x] **Tier 1** — Macro Agent + FRED Indicators
- [x] **Tier 2** — Technical + Fundamental Agents
- [ ] **Tier 3** — Portfolio weighting + Risk adjustment
- [x] **Slack** — Rich Block Kit output
- [x] **Email** — HTML email reports
- [x] **CI/CD** — GitHub Actions + Workload Identity Federation
- [ ] **Dashboard** — Web UI for historical analysis
- [ ] **Backtesting** — Historical performance validation

---

## 📄 License

Private project. All rights reserved.
