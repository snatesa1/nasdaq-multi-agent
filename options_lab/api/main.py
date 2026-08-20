from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, Body, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime


from .config import settings
from .models import (
    GBMParams,
    OptionParams,
    MonteCarloPricingRequest,
    LegacyLabRequest,
    StrategyRequest,
    VolSurfaceRequest,
    PortfolioGreeksRequest,
    SocraticTutorRequest,
    TutorHintRequest,
    ExplainerRequest,
    ScenarioHedgingRequest,
    SaveSessionRequest,
    UpdateSessionRequest,
    AnalyzeRequest,
    FundamentalIndexRequest,
    FundamentalIndexResponse,
    EarningsScanRequest,
    BrokerAccountSummary,
    BrokerPositionsResponse,
    BrokerOrdersResponse,
    BrokerPosition,
    BrokerOrder,
    SafetyCheckRequest
)
import asyncio
from .saxo_client import SaxoClient
from .tracker import log_progress
from .trade_history_ingest import TradeHistoryIngestEngine
from .campaign_stitcher import CampaignStitcher
from .behavioral_forensics import BehavioralForensicsEngine
from .safety_shield import BehavioralSafetyShield




import sys
_options_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _options_lab_dir not in sys.path:
    sys.path.insert(0, _options_lab_dir)

# Core imports from engine
from engine.gbm_engine import simulate_gbm
from engine.black_scholes import black_scholes_price, black_scholes_greeks, implied_volatility
from engine.monte_carlo import pricing_monte_carlo_standard, pricing_monte_carlo_lab_legacy
from engine.greeks import generate_greeks_surface
from engine.strategy_simulator import simulate_strategy_payoff
from engine.volatility_surface import generate_volatility_surface

# Service imports
from .market_data import fetch_market_data
from .tutor import SocraticTutor
from . import db as database
from .auth import verify_firebase_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("options-lab-api")

app = FastAPI(title="OptionsLab API", version="2.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .fundamental_index import FundamentalIndexEngine

tutor_service = SocraticTutor()
fundamental_engine = FundamentalIndexEngine()
saxo_broker_client = SaxoClient()
broker_concurrency_lock = asyncio.Lock()

ingest_engine = TradeHistoryIngestEngine()
campaign_stitcher = CampaignStitcher(ingest_engine=ingest_engine)
behavioral_forensics = BehavioralForensicsEngine(campaign_stitcher=campaign_stitcher)
safety_shield = BehavioralSafetyShield()



# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "service": "options-lab", "version": "2.0.0"}

# ── Fundamental Indexation Scan (Arnott 80/20 Replication) ───────────
@app.post("/fundamental-index/scan")
def scan_fundamental_index(params: FundamentalIndexRequest = FundamentalIndexRequest()):
    try:
        results = fundamental_engine.compute_index(symbols=params.symbols)
        return results
    except Exception as e:
        logger.error(f"Fundamental Index scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/db")
def debug_db():
    try:
        conn = database._get_conn()
        portfolios = conn.execute("SELECT * FROM portfolios").fetchall()
        tickers = conn.execute("SELECT * FROM portfolio_tickers").fetchall()
        return {
            "db_path": database._DB_PATH,
            "portfolios": [dict(r) for r in portfolios],
            "tickers": [dict(t) for t in tickers]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/tutor/debug_firestore")
def debug_firestore():
    try:
        from google.cloud import firestore
        import os
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "optimal-aurora-495912-n0")
        client = firestore.Client(project=project_id)
        
        # Test write
        doc_ref = client.collection("tutor_sessions_debug").document("test")
        doc_ref.set({"test": True, "timestamp": firestore.SERVER_TIMESTAMP})
        
        # Test read
        doc = doc_ref.get()
        data = doc.to_dict()
        
        # Delete
        doc_ref.delete()
        
        return {
            "status": "success",
            "project_id": project_id,
            "use_firestore_flag": database._USE_FIRESTORE,
            "data": str(data)
        }
    except Exception as e:
        import traceback
        return {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "use_firestore_flag": database._USE_FIRESTORE
        }


# ── Market Data ────────────────────────────────────────────────────────────
@app.get("/market/quote/{symbol}")
def get_quote(symbol: str, user=Depends(verify_firebase_token)):
    data = fetch_market_data(symbol)
    return data

@app.get("/market/universe")
def get_universe(user=Depends(verify_firebase_token)):
    try:
        import pandas as pd
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nasdaq_screener.csv")
        if not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="Screener data file not found.")

        df = pd.read_csv(csv_path)
        df = df.dropna(subset=['sector', 'symbol'])
        df['symbol'] = df['symbol'].str.strip().str.upper()
        df['sector'] = df['sector'].str.strip()
        df = df[~df['sector'].isin(['', 'Miscellaneous'])]
        df['pct_num'] = df['pctchange'].str.rstrip('%').astype(float)
        df = df[df['marketCap'] > 0]

        results = {}
        for sector, group in df.groupby('sector'):
            top_cap = group.nlargest(30, 'marketCap')
            top_momentum = top_cap.sort_values(by='pct_num', ascending=False).head(10)

            stock_list = []
            for _, row in top_momentum.iterrows():
                try:
                    price_str = str(row['lastsale']).replace('$', '').replace(',', '')
                    price_val = float(price_str)
                except Exception:
                    price_val = 0.0

                stock_list.append({
                    "symbol": row['symbol'],
                    "name": row['name'],
                    "marketCap": float(row['marketCap']),
                    "price": price_val,
                    "pctchange": float(row['pct_num'])
                })
            results[sector] = stock_list

        return results
    except Exception as e:
        logger.error(f"Failed to fetch market universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── GBM Simulation ─────────────────────────────────────────────────────────
@app.post("/simulate/gbm")
def post_simulate_gbm(params: GBMParams, user=Depends(verify_firebase_token)):
    try:
        results = simulate_gbm(
            S0=params.S0, mu=params.mu, sigma=params.sigma,
            T=params.T, N=params.N, num_paths=params.num_paths
        )
        return results
    except Exception as e:
        logger.error(f"GBM simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Analytical Option Pricing ──────────────────────────────────────────────
@app.post("/price/analytical")
def price_analytical(params: OptionParams, user=Depends(verify_firebase_token)):
    try:
        price = black_scholes_price(
            S=params.S, K=params.K, T=params.T, r=params.r,
            sigma=params.sigma, option_type=params.option_type
        )
        greeks = black_scholes_greeks(
            S=params.S, K=params.K, T=params.T, r=params.r,
            sigma=params.sigma, option_type=params.option_type
        )
        return {"price": price, "greeks": greeks}
    except Exception as e:
        logger.error(f"Analytical BS pricing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Monte Carlo Option Pricing ──────────────────────────────────────────────
@app.post("/price/monte-carlo")
def price_monte_carlo(params: MonteCarloPricingRequest, user=Depends(verify_firebase_token)):
    try:
        results = pricing_monte_carlo_standard(
            S0=params.S0, K=params.K, T=params.T, r=params.r,
            sigma=params.sigma, option_type=params.option_type, num_paths=params.num_paths
        )
        return results
    except Exception as e:
        logger.error(f"MC pricing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Legacy Lab Option Pricing ──────────────────────────────────────────────
@app.post("/price/legacy-lab")
def price_legacy_lab(params: LegacyLabRequest, user=Depends(verify_firebase_token)):
    try:
        results = pricing_monte_carlo_lab_legacy(
            S0=params.S0, K=params.K, T=params.T, r=params.r,
            sigma=params.sigma, N=params.N
        )
        return results
    except Exception as e:
        logger.error(f"Legacy lab pricing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Greeks Surface ─────────────────────────────────────────────────────────
@app.post("/greeks/surface")
def greeks_surface(params: OptionParams, user=Depends(verify_firebase_token)):
    try:
        results = generate_greeks_surface(
            S0=params.S, K=params.K, T=params.T, r=params.r,
            sigma=params.sigma, option_type=params.option_type
        )
        return results
    except Exception as e:
        logger.error(f"Greeks surface generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Strategy Payoff ────────────────────────────────────────────────────────
@app.post("/strategy/payoff")
def strategy_payoff(params: StrategyRequest, user=Depends(verify_firebase_token)):
    try:
        legs_data = []
        for leg in params.legs:
            legs_data.append({
                "asset_type": leg.asset_type,
                "option_type": leg.option_type,
                "position": leg.position,
                "strike": leg.strike,
                "expiry": leg.expiry,
                "entry_price": leg.entry_price,
                "quantity": leg.quantity
            })

        results = simulate_strategy_payoff(
            legs_data=legs_data,
            underlying_spot=params.underlying_spot,
            r=params.r, sigma=params.sigma,
            price_range_pct=params.price_range_pct, steps=params.steps
        )
        return results
    except Exception as e:
        logger.error(f"Strategy payoff simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Volatility Surface ───────────────────────────────────────────────────────
@app.post("/volatility/surface")
def volatility_surface(params: VolSurfaceRequest, user=Depends(verify_firebase_token)):
    try:
        results = generate_volatility_surface(
            spot_price=params.spot_price,
            base_sigma=params.base_sigma,
            risk_free_rate=params.risk_free_rate,
            strike_ratios=params.strike_ratios,
            expirations_days=params.expirations_days,
            skew_intensity=params.skew_intensity,
            smile_convexity=params.smile_convexity
        )
        return results
    except Exception as e:
        logger.error(f"Volatility surface calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Portfolio Net Greeks Aggregator ──────────────────────────────────────────
@app.post("/portfolio/greeks")
def portfolio_greeks(params: PortfolioGreeksRequest, user=Depends(verify_firebase_token)):
    try:
        from .analysis import calculate_portfolio_greeks
        positions = [p.dict() for p in params.positions]
        return calculate_portfolio_greeks(positions=positions, risk_free_rate=params.risk_free_rate)
    except Exception as e:
        logger.error(f"Portfolio Greeks calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Socratic Tutor Chat ────────────────────────────────────────────────────
@app.post("/tutor/ask")
def tutor_ask(params: SocraticTutorRequest, user=Depends(verify_firebase_token)):
    try:
        response = tutor_service.generate_response(
            message=params.message,
            chat_history=params.chat_history,
            context=params.context,
            enable_grounding=params.enable_grounding
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Tutor chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Socratic Tutor Pedagogical Hint ─────────────────────────────────────────
@app.post("/tutor/hint")
def tutor_hint(params: TutorHintRequest, user=Depends(verify_firebase_token)):
    try:
        hint = tutor_service.generate_hint(
            chat_history=params.chat_history,
            context=params.context
        )
        return {"hint": hint}
    except Exception as e:
        logger.error(f"Tutor hint generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Socratic Tutor Concept Explanation ──────────────────────────────────────
@app.post("/tutor/explain")
def tutor_explain(params: ExplainerRequest, user=Depends(verify_firebase_token)):
    try:
        response = tutor_service.get_concept_explanation(concept=params.concept)
        return {"explanation": response}
    except Exception as e:
        logger.error(f"Tutor explanation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Session Persistence ───────────────────────────────────────────────────────
@app.get("/tutor/sessions")
def list_sessions(user=Depends(verify_firebase_token)):
    try:
        return database.list_sessions()
    except Exception as e:
        logger.error(f"list_sessions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tutor/sessions", status_code=201)
def create_session(req: SaveSessionRequest, user=Depends(verify_firebase_token)):
    try:
        return database.create_session(title=req.title, messages=req.messages)
    except Exception as e:
        logger.error(f"create_session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tutor/sessions/{session_id}")
def get_session(session_id: str, user=Depends(verify_firebase_token)):
    result = database.get_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@app.put("/tutor/sessions/{session_id}")
def update_session(session_id: str, req: UpdateSessionRequest, user=Depends(verify_firebase_token)):
    result = database.update_session(session_id, messages=req.messages, title=req.title)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@app.delete("/tutor/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, user=Depends(verify_firebase_token)):
    ok = database.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return None

# ── Portfolio Management ──────────────────────────────────────────────────────
@app.get("/api/portfolio")
def list_portfolios(user=Depends(verify_firebase_token)):
    try:
        return database.list_portfolios()
    except Exception as e:
        logger.error(f"list_portfolios failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: str, user=Depends(verify_firebase_token)):
    result = database.get_portfolio(portfolio_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return result

@app.get("/api/portfolio/{portfolio_id}/analyze")
def analyze_portfolio(portfolio_id: str, user=Depends(verify_firebase_token)):
    from .analysis import analyze_portfolio_diversification
    result = analyze_portfolio_diversification(portfolio_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/portfolio/sync")
def sync_portfolios(spreadsheet_id: Optional[str] = None, user=Depends(verify_firebase_token)):
    """Sync portfolio sheets from the user's Google Drive."""
    try:
        from .drive_sync import sync_all_portfolios_from_drive, sync_portfolio_from_sheet

        if spreadsheet_id:
            from .drive_sync import extract_spreadsheet_id
            clean_id = extract_spreadsheet_id(spreadsheet_id)
            logger.info(f"Syncing specific spreadsheet URL/ID: {spreadsheet_id} -> Clean ID: {clean_id}")
            tickers = sync_portfolio_from_sheet(clean_id)
            if not tickers:
                return {
                    "message": f"No tickers found or could not read sheet ID '{clean_id}'. If private, ensure your local token.json is logged in.", 
                    "portfolios": []
                }
            
            # Check if portfolio already exists by source URL
            existing = database.list_portfolios()
            portfolio = None
            for p in existing:
                if p.get("source_url") == clean_id or p.get("source_url") == spreadsheet_id:
                    portfolio = p
                    break

            if portfolio is None:
                portfolio = database.create_portfolio(
                    name=f"Portfolio ({clean_id[:8]}...)",
                    source_url=clean_id
                )

            # Fetch live market data for each ticker to enrich it
            enriched_tickers = []
            for t in tickers:
                sym = t["symbol"].strip().upper()
                try:
                    mdata = fetch_market_data(sym)
                    enriched_tickers.append({
                        "symbol": sym,
                        "name": mdata.get("name") or sym,
                        "current_price": mdata.get("current_price", 0.0),
                        "change": mdata.get("change", 0.0),
                        "high": mdata.get("high", mdata.get("current_price", 0.0)),
                        "low": mdata.get("low", mdata.get("current_price", 0.0)),
                        "volume": mdata.get("volume", 0),
                    })
                except Exception as e:
                    logger.error(f"Failed to fetch market data during sync for {sym}: {e}")
                    enriched_tickers.append(t)

            # Upsert tickers
            synced_tickers = database.upsert_portfolio_tickers(
                portfolio_id=portfolio["id"],
                tickers=enriched_tickers
            )
            return {
                "message": "Synced specific portfolio",
                "portfolios": [{
                    "portfolio": portfolio,
                    "tickers_synced": len(synced_tickers)
                }]
            }

        # Fallback to auto-discovery
        synced = sync_all_portfolios_from_drive(query="portfolio")
        if not synced:
            return {"message": "No portfolio sheets found in Google Drive. Make sure sheets are shared with the Cloud Run service account.", "portfolios": []}

        results = []
        for sheet_name, data in synced.items():
            # Check if portfolio already exists by source URL
            existing = database.list_portfolios()
            portfolio = None
            for p in existing:
                if p.get("source_url") == data["sheet_id"]:
                    portfolio = p
                    break

            if portfolio is None:
                portfolio = database.create_portfolio(
                    name=sheet_name,
                    source_url=data["sheet_id"]
                )

            # Fetch live market data for each ticker to enrich it
            enriched_tickers = []
            for t in data["tickers"]:
                sym = t["symbol"].strip().upper()
                try:
                    mdata = fetch_market_data(sym)
                    enriched_tickers.append({
                        "symbol": sym,
                        "name": mdata.get("name") or sym,
                        "current_price": mdata.get("current_price", 0.0),
                        "change": mdata.get("change", 0.0),
                        "high": mdata.get("high", mdata.get("current_price", 0.0)),
                        "low": mdata.get("low", mdata.get("current_price", 0.0)),
                        "volume": mdata.get("volume", 0),
                    })
                except Exception as e:
                    logger.error(f"Failed to fetch market data during sync for {sym}: {e}")
                    enriched_tickers.append(t)

            # Upsert tickers
            tickers = database.upsert_portfolio_tickers(
                portfolio_id=portfolio["id"],
                tickers=enriched_tickers
            )
            results.append({
                "portfolio": portfolio,
                "tickers_synced": len(tickers)
            })

        return {"message": f"Synced {len(results)} portfolios", "portfolios": results}
    except Exception as e:
        logger.error(f"Portfolio sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/portfolio/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: str, user=Depends(verify_firebase_token)):
    ok = database.delete_portfolio(portfolio_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return None

# ── Multi-Agent Analysis ──────────────────────────────────────────────────────
@app.post("/multi-agent/analyze")
async def run_multi_agent_analysis(req: AnalyzeRequest, user=Depends(verify_firebase_token)):
    """
    Run the hierarchical multi-agent analysis pipeline on the given tickers.
    This is a simplified version that runs Technical + Fundamental agents
    on each ticker and returns the combined results.
    """
    try:
        from .agents.technical_agent import TechnicalAgent
        from .agents.fundamental_agent import FundamentalAgent
        import asyncio

        tech_agent = TechnicalAgent()
        fund_agent = FundamentalAgent()

        results = {}
        for ticker in req.tickers:
            ticker = ticker.strip().upper()
            if not ticker or ticker.endswith("=F"):
                continue  # Skip futures

            try:
                tech_result, fund_result = await asyncio.gather(
                    tech_agent.analyze(symbol=ticker),
                    fund_agent.analyze(symbol=ticker),
                    return_exceptions=True
                )

                results[ticker] = {
                    "technical": tech_result.to_dict() if hasattr(tech_result, 'to_dict') else {"error": str(tech_result)},
                    "fundamental": fund_result.to_dict() if hasattr(fund_result, 'to_dict') else {"error": str(fund_result)},
                }
            except Exception as e:
                logger.error(f"Analysis failed for {ticker}: {e}")
                results[ticker] = {"error": str(e)}

        return {"tickers_analyzed": len(results), "results": results}
    except Exception as e:
        logger.error(f"Multi-agent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Earnings Volatility Scanner ──────────────────────────────────────────
@app.get("/api/earnings/upcoming")
def get_upcoming_earnings(user=Depends(verify_firebase_token)):
    try:
        from .earnings_calendar import get_upcoming_earnings_calendar
        return get_upcoming_earnings_calendar()
    except Exception as e:
        logger.error(f"Failed to fetch upcoming earnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/earnings/scan")
async def scan_earnings(req: EarningsScanRequest = Body(...), user=Depends(verify_firebase_token)):
    try:
        from .earnings_scanner import run_earnings_scan
        results = await run_earnings_scan(
            low_threshold_pct=req.low_threshold_pct,
            min_open_interest=req.min_open_interest
        )
        return results
    except Exception as e:
        logger.error(f"Earnings scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/earnings/volatility/{symbol}")
async def get_earnings_volatility(symbol: str, user=Depends(verify_firebase_token)):
    try:
        from .agents.earnings_vol_agent import EarningsVolAgent
        agent = EarningsVolAgent()
        result = await agent.analyze(symbol)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Failed to get earnings volatility for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Broker Gateway Endpoints (Type-Safe Live & SIM Integration) ───────────

@app.get("/api/broker/status")
def get_broker_status(user=Depends(verify_firebase_token)):
    """Returns the operational environment, live execution safety guard, and connection health."""
    has_token = bool(saxo_broker_client.access_token)
    log_progress("Status Check", "INFO", f"Status queried. Has token: {has_token}")
    return {
        "environment": settings.SAXO_ENV,
        "allow_live_execution": settings.BROKER_ALLOW_LIVE_EXECUTION,
        "has_access_token": has_token,
        "has_refresh_token": bool(saxo_broker_client.refresh_token),
        "needs_reauth": getattr(saxo_broker_client, 'needs_reauth', False),
        "base_url": saxo_broker_client.base_url,
        "timeout_seconds": saxo_broker_client.timeout,
        "app_name": settings.SAXO_APP_NAME,
        "status": "NEEDS_REAUTH" if getattr(saxo_broker_client, 'needs_reauth', False) else "READY"
    }

@app.get("/api/broker/oauth/auth-url")
def get_broker_auth_url(user=Depends(verify_firebase_token)):
    """Generates the Saxo OpenAPI OAuth login URL for authorizing the Live Akpegis-Agent app."""
    url = saxo_broker_client.get_authorization_url()
    return {"auth_url": url, "app_name": settings.SAXO_APP_NAME, "redirect_url": settings.SAXO_REDIRECT_URL}

@app.post("/api/broker/oauth/set-token")
def set_broker_token(payload: Dict[str, Any] = Body(...), user=Depends(verify_firebase_token)):
    """
    Sets the live access token or exchanges an authorization code.
    Allows 1-click token injection from the developer portal or OAuth redirect.
    """
    token = payload.get("token") or payload.get("access_token")
    code = payload.get("code")
    refresh_token = payload.get("refresh_token")

    # Auto-detect if they pasted a UUID code directly instead of the full URL or token
    if token and len(token.strip()) == 36 and "-" in token:
        code = token.strip()
        token = None

    if token and ("code=" in token or token.startswith("http")):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(token)
        query_params = parse_qs(parsed.query)
        if "code" in query_params:
            code = query_params["code"][0]

    if code:
        data = saxo_broker_client.exchange_code_for_token(code)
        log_progress("OAuth Code Exchange", "SUCCESS", "Saxo code exchanged for tokens successfully.")
        return {"status": "SUCCESS", "message": "Live Saxo OAuth token successfully exchanged!", "data": data}

    if token:
        saxo_broker_client.set_token(token, refresh_token)
        saxo_broker_client._persist_tokens_to_env()
        log_progress("Token Configuration", "SUCCESS", f"Developer token applied manually (Length: {len(token)})")
        return {"status": "SUCCESS", "message": "Live Saxo token successfully registered!", "environment": settings.SAXO_ENV}

    log_progress("Token Configuration", "ERROR", "Token set request failed due to missing params.")
    raise HTTPException(status_code=400, detail="Missing 'token' or 'code' parameter.")


@app.post("/api/broker/oauth/disconnect")
def disconnect_broker(user=Depends(verify_firebase_token)):
    """
    Clears live access tokens, wipes cached Saxo records, and closes active broker session.
    """
    saxo_broker_client.access_token = None
    saxo_broker_client.refresh_token = None
    saxo_broker_client.needs_reauth = True
    saxo_broker_client.token_acquired_at = None
    saxo_broker_client._persist_tokens_to_env()
    if hasattr(saxo_broker_client, "session"):
        saxo_broker_client.session.cookies.clear()
    database.clear_saxo_cache()
    log_progress("Session Disconnect", "SUCCESS", "Disconnected Saxo session, wiped SQLite cache, and cleared access tokens.")
    logger.info("Broker Live API session disconnected, SQLite cache cleared, and access tokens wiped.")
    return {"status": "DISCONNECTED", "message": "Live Saxo trading bot connection safely closed."}




@app.get("/api/broker/account", response_model=BrokerAccountSummary)
async def get_broker_account(user=Depends(verify_firebase_token)):
    """Fetches real-time portfolio balance, equity, and margin directly from Saxo OpenAPI."""
    async with broker_concurrency_lock:
        try:
            balances = saxo_broker_client.get_account_balances()
            database.set_saxo_cache("account_summary", balances)
            log_progress("Account Fetch", "SUCCESS", f"Fetched account total equity: ${balances.get('total_equity')}")
            return BrokerAccountSummary(**balances)
        except Exception as e:
            cached = database.get_saxo_cache("account_summary")
            if cached:
                logger.info("Serving cached Saxo account summary from SQLite.")
                return BrokerAccountSummary(**cached)
            log_progress("Account Fetch", "ERROR", f"Exception during account fetch: {e}")
            logger.error(f"Failed to fetch broker account: {e}")
            if "authentication required" in str(e).lower() or "401" in str(e):
                raise HTTPException(status_code=401, detail=str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/positions", response_model=BrokerPositionsResponse)
async def get_broker_positions(user=Depends(verify_firebase_token)):
    """Fetches current open stock and option positions directly from Saxo OpenAPI."""
    async with broker_concurrency_lock:
        try:
            positions_data = saxo_broker_client.get_positions()
            database.set_saxo_cache("positions", positions_data)
            log_progress("Positions Fetch", "SUCCESS", f"Fetched open positions (Count: {len(positions_data.get('positions', []))})")
            return BrokerPositionsResponse(**positions_data)
        except Exception as e:
            cached = database.get_saxo_cache("positions")
            if cached:
                logger.info("Serving cached Saxo positions from SQLite.")
                return BrokerPositionsResponse(**cached)
            log_progress("Positions Fetch", "ERROR", f"Exception during positions fetch: {e}")
            logger.error(f"Failed to fetch broker positions: {e}")
            if "authentication required" in str(e).lower() or "401" in str(e):
                raise HTTPException(status_code=401, detail=str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/orders", response_model=BrokerOrdersResponse)
async def get_broker_orders(user=Depends(verify_firebase_token)):
    """Fetches active working orders and recently executed order history directly from Saxo OpenAPI."""
    async with broker_concurrency_lock:
        try:
            orders_data = saxo_broker_client.get_orders()
            database.set_saxo_cache("orders", orders_data)
            return BrokerOrdersResponse(**orders_data)
        except Exception as e:
            cached = database.get_saxo_cache("orders")
            if cached:
                logger.info("Serving cached Saxo orders from SQLite.")
                return BrokerOrdersResponse(**cached)
            logger.error(f"Failed to fetch broker orders: {e}")
            if "authentication required" in str(e).lower() or "401" in str(e):
                raise HTTPException(status_code=401, detail=str(e))
            raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/broker/cache")
def get_broker_cached_snapshot(user=Depends(verify_firebase_token)):
    """Returns the full offline/cached snapshot of Saxo accounts, positions, and orders from SQLite."""
    return {
        "account": database.get_saxo_cache("account_summary"),
        "positions": database.get_saxo_cache("positions"),
        "orders": database.get_saxo_cache("orders")
    }

@app.post("/api/broker/orders")
async def place_broker_order(
    payload: Dict[str, Any] = Body(...),
    user=Depends(verify_firebase_token)
):
    """
    Places an order via the broker gateway.
    Protected by the Live Safety Shield (blocks real execution unless explicitly enabled).
    """
    async with broker_concurrency_lock:
        try:
            uic = int(payload.get("uic", 0))
            asset_type = payload.get("asset_type", "StockOption")
            amount = int(payload.get("amount", 1))
            buy_sell = payload.get("buy_sell", "Sell")
            order_type = payload.get("order_type", "Limit")
            order_price = float(payload.get("order_price", 0.0))

            res = saxo_broker_client.place_order(
                uic=uic,
                asset_type=asset_type,
                amount=amount,
                buy_sell=buy_sell,
                order_type=order_type,
                order_price=order_price
            )
            return res
        except Exception as e:
            logger.error(f"Failed to place broker order: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/broker/pipeline/scan")
async def run_broker_pipeline_scan(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    user=Depends(verify_firebase_token)
):
    """
    Triggers end-to-end systematic options yield scan with concurrency lock
    to avoid duplicate or overlapping background scans.
    """
    async with broker_concurrency_lock:
        try:
            from .saxo_pipeline import SaxoPipeline
            pipeline = SaxoPipeline(saxo_client=saxo_broker_client)
            candidates = (payload or {}).get("candidates", ["AAPL", "NVDA", "JPM", "TSLA"])
            simulate_order = (payload or {}).get("simulate_order_placement", True)

            results = await pipeline.execute_full_pipeline_scan(
                candidate_tickers=candidates,
                simulate_order_placement=simulate_order
            )
            return results
        except Exception as e:
            logger.error(f"Broker pipeline scan failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/watchlists")
async def get_broker_watchlists(user=Depends(verify_firebase_token)):
    """Fetches user custom watchlists directly from Saxo OpenAPI."""
    try:
        watchlists = saxo_broker_client.get_user_watchlists()
        return {"watchlists": watchlists}
    except Exception as e:
        logger.error(f"Failed to fetch Saxo watchlists: {e}")
        return {"watchlists": [{"WatchlistId": "WL_DEFAULT", "Name": "Primary Watchlist", "Position": 0}]}

@app.get("/api/broker/watchlist/{watchlist_id}")
async def get_broker_watchlist_instruments(watchlist_id: str, user=Depends(verify_firebase_token)):
    """Fetches resolved instruments belonging to a specific Saxo watchlist."""
    try:
        instruments = saxo_broker_client.get_watchlist_instruments(watchlist_id)
        return {"watchlist_id": watchlist_id, "instruments": instruments}
    except Exception as e:
        logger.error(f"Failed to fetch watchlist instruments: {e}")
        return {"watchlist_id": watchlist_id, "instruments": []}

@app.get("/api/broker/closed-positions")
async def get_broker_closed_positions(user=Depends(verify_firebase_token)):
    """Fetches historical closed positions / order blotter with realized P&L."""
    try:
        trades = saxo_broker_client.get_closed_positions()
        return {"trades": trades, "count": len(trades)}
    except Exception as e:
        logger.error(f"Failed to fetch closed positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scanner/csp")
async def scan_csp_opportunities(
    source: str = "saxo",
    watchlist_id: Optional[str] = None,
    user=Depends(verify_firebase_token)
):
    """
    Scans live market option setups for Saxo watchlist tickers or open holdings,
    computing ~0.20-0.30 Delta target strikes, yield, and annualized ROC %.
    """
    instruments = []
    
    # 1. Pull instruments from Saxo Watchlist or Holdings
    if source == "saxo":
        target_wl = watchlist_id if (watchlist_id and watchlist_id != "WL_DEFAULT") else "WL_STOCKS_US"
        instruments = saxo_broker_client.get_watchlist_instruments(target_wl)
    
    if not instruments:
        instruments = saxo_broker_client.get_watchlist_instruments("WL_STOCKS_US")

    symbols = [item["symbol"] for item in instruments if "symbol" in item]

    results = []
    for item in instruments:
        sym = item.get("symbol")
        if not sym:
            continue
        try:
            # Clean symbol for yahoo/alpaca lookups
            lookup_sym = sym.replace(".", "-")
            mkt = fetch_market_data(lookup_sym)
            
            # Prefer live quote or fallback to watchlist last traded price
            price = float(mkt.get("current_price") or item.get("price") or 100.0)
            if price <= 0:
                price = float(item.get("price") or 100.0)

            # Target Put strike ~8% OTM (Delta ~ -0.22 to -0.26)
            if price > 500:
                target_strike = round((price * 0.92) / 5.0) * 5.0
            elif price > 100:
                target_strike = round(price * 0.92)
            else:
                target_strike = round(price * 0.92, 1)

            dte = 35
            # Premium estimation: 2.2% - 2.8% of underlying price
            est_premium = round(price * 0.024, 2)
            ret_on_cap = (est_premium / target_strike) * 100.0 if target_strike > 0 else 0.0
            annualized_roc = (ret_on_cap * (365 / dte))
            
            # Simulated upcoming earnings calendar
            earnings_map = {
                "AAPL": "2026-10-29", "ABT": "2026-10-16", "T": "2026-10-22",
                "BAC": "2026-10-15", "BRK.B": "2026-11-06", "CVX": "2026-10-30",
                "CSCO": "2026-11-12", "C": "2026-10-13", "KO": "2026-10-20",
                "COP": "2026-10-29", "GE": "2026-10-21", "GS": "2026-10-14",
                "HPQ": "2026-11-24"
            }
            earnings_date = earnings_map.get(sym, "2026-11-15")

            results.append({
                "ticker": sym,
                "name": item.get("name") or item.get("description", sym),
                "price": round(price, 2),
                "strike": round(target_strike, 2),
                "delta": -0.24,
                "dte": dte,
                "premium": est_premium,
                "yield": round(ret_on_cap, 2),
                "annualized": round(annualized_roc, 1),
                "earnings": earnings_date
            })
        except Exception as e:
            logger.debug(f"CSP quote generation for {sym} failed: {e}")

    return {
        "source": source,
        "scanned_symbols": symbols,
        "opportunities": results
    }

# ── Order Blotter Endpoint ──────────────────────────────────────────────────
@app.get("/api/broker/order-blotter")
async def get_broker_order_blotter(user=Depends(verify_firebase_token)):
    """Fetches full historical Saxo Order Blotter with all statuses (Traded, Expired, Cancelled)."""
    try:
        data = saxo_broker_client.get_order_blotter()
        database.set_saxo_cache("order_blotter", data)
        return data
    except Exception as e:
        logger.error(f"Failed to fetch order blotter: {e}")
        cached = database.get_saxo_cache("order_blotter")
        if cached:
            return cached
        raise HTTPException(status_code=500, detail=str(e))

# ── Multi-Year Trade History Ingestion & Behavioral Forensics ────────────────
@app.post("/api/history/upload-pdf")
async def upload_saxo_pdf_report(
    file: UploadFile = File(...),
    user=Depends(verify_firebase_token)
):
    """Parses and ingests an authentic multi-page Saxo Portfolio or Positions PDF report."""
    try:
        pdf_bytes = await file.read()
        res = ingest_engine.ingest_pdf_bytes(pdf_bytes, filename=file.filename or "Saxo_Report.pdf")
        log_progress("PDF Ingest", "SUCCESS", f"Ingested report {res.get('report_id')}")
        return res
    except Exception as e:
        logger.error(f"Failed to ingest Saxo PDF report: {e}")
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {str(e)}")

@app.post("/api/history/sample-init")
def initialize_sample_report(user=Depends(verify_firebase_token)):
    """Seeds the database with the verified 16-page Saxo baseline portfolio report."""
    try:
        res = ingest_engine.ingest_default_sample()
        return res
    except Exception as e:
        logger.error(f"Failed to initialize sample report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/reports")
def list_ingested_reports(user=Depends(verify_firebase_token)):
    """Lists all historical reports stored in the database."""
    try:
        reports = ingest_engine.get_ingested_reports()
        if not reports:
            # Auto-seed if empty
            ingest_engine.ingest_default_sample()
            reports = ingest_engine.get_ingested_reports()
        return {"reports": reports}
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/campaigns")
def get_historical_campaigns(report_id: Optional[str] = None, user=Depends(verify_firebase_token)):
    """Returns stitched multi-leg trade campaign lifecycles (Wheel, Covered Calls, Bag-holds)."""
    try:
        campaigns = campaign_stitcher.reconstruct_all_campaigns(report_id=report_id)
        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        logger.error(f"Failed to reconstruct campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/behavioral-audit")
def get_behavioral_audit(report_id: Optional[str] = None, user=Depends(verify_firebase_token)):
    """Performs full psychological and behavioral audit, calculating discipline score and bias diagnostics."""
    try:
        audit = behavioral_forensics.generate_behavioral_audit(report_id=report_id)
        return audit
    except Exception as e:
        logger.error(f"Failed to run behavioral audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/news")
def get_portfolio_news_feed(top: int = 25, user=Depends(verify_firebase_token)):
    """Fetches real-time portfolio news wire and financial headline feed from Saxo."""
    try:
        news = saxo_broker_client.get_portfolio_news(top=top)
        return {"news": news, "count": len(news)}
    except Exception as e:
        logger.error(f"Failed to fetch portfolio news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shield/check-order")
def check_order_behavioral_safety(
    req: SafetyCheckRequest,
    user=Depends(verify_firebase_token)
):
    """Evaluates an incoming order against historical behavioral guardrails and circuit breakers."""
    try:
        eval_result = safety_shield.evaluate_order(
            symbol=req.symbol,
            asset_type=req.asset_type,
            buy_sell=req.buy_sell,
            strike=req.strike,
            delta=req.delta,
            dte=req.dte,
            order_value=req.order_value,
            portfolio_equity=req.portfolio_equity,
            current_ticker_exposure=req.current_ticker_exposure,
            recent_loss_amount=req.recent_loss_amount
        )
        return eval_result
    except Exception as e:
        logger.error(f"Safety check failed: {e}")
# ── Client-Side Error Telemetry & Unified Logger ───────────────────────────

@app.post("/api/logs/client-error")
async def log_client_error(payload: Dict[str, Any] = Body(...)):
    """Ingests, formats, and persists frontend runtime exceptions and telemetry."""
    level = payload.get("level", "error").upper()
    msg = payload.get("message", "Unknown client exception")
    source = payload.get("source", "frontend")
    stack = payload.get("stack", "")
    comp_stack = payload.get("componentStack", "")
    url = payload.get("url", "")
    ts = payload.get("timestamp", datetime.now().isoformat())

    formatted_log = (
        f"\n🔴 [FRONTEND RUNTIME EXCEPTION] [{ts}]\n"
        f"   Level: {level}\n"
        f"   Message: {msg}\n"
        f"   URL: {url}\n"
        f"   Source: {source}\n"
    )
    if stack:
        formatted_log += f"   Stack: {stack}\n"
    if comp_stack:
        formatted_log += f"   Component Hierarchy: {comp_stack}\n"

    print(formatted_log)
    logger.error(formatted_log)

    # Persist to client_errors.log
    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "client_errors.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted_log + "\n" + "-"*80 + "\n")
    except Exception as e_log:
        logger.warning(f"Failed writing to client_errors.log: {e_log}")

    return {"status": "LOGGED", "timestamp": ts}



from fastapi.staticfiles import StaticFiles

class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' http://127.0.0.1:* http://localhost:* https: data: blob:; "
            "script-src 'self' 'unsafe-inline' http://127.0.0.1:* http://localhost:* https:; "
            "style-src 'self' 'unsafe-inline' https: fonts.googleapis.com; "
            "font-src 'self' data: https: fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' http://127.0.0.1:* http://localhost:* https: ws: wss:; "
            "frame-src 'self' https:;"
        )
        return response


frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "out")
if os.path.exists(frontend_path):
    app.mount("/", NoCacheStaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"Mounted static frontend from {frontend_path} (Cache-Control disabled)")
else:
    logger.warning(f"Frontend static folder not found at {frontend_path}. Running in API-only mode.")
