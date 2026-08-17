from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from typing import Dict, Any, Optional

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
    BrokerOrder
)
import asyncio
from .saxo_client import SaxoClient




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
            logger.info(f"Syncing specific spreadsheet {spreadsheet_id}")
            tickers = sync_portfolio_from_sheet(spreadsheet_id)
            if not tickers:
                return {"message": "No tickers found or failed to read the spreadsheet. Verify sharing permissions.", "portfolios": []}
            
            # Check if portfolio already exists by source URL
            existing = database.list_portfolios()
            portfolio = None
            for p in existing:
                if p.get("source_url") == spreadsheet_id:
                    portfolio = p
                    break

            if portfolio is None:
                portfolio = database.create_portfolio(
                    name=f"Sheet Portfolio ({spreadsheet_id[:8]})",
                    source_url=spreadsheet_id
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
    return {
        "environment": settings.SAXO_ENV,
        "allow_live_execution": settings.BROKER_ALLOW_LIVE_EXECUTION,
        "has_access_token": bool(saxo_broker_client.access_token),
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

    if token and ("code=" in token or token.startswith("http")):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(token)
        query_params = parse_qs(parsed.query)
        if "code" in query_params:
            code = query_params["code"][0]

    if code:
        data = saxo_broker_client.exchange_code_for_token(code)
        return {"status": "SUCCESS", "message": "Live Saxo OAuth token successfully exchanged!", "data": data}

    if token:
        saxo_broker_client.set_token(token, refresh_token)
        saxo_broker_client._persist_tokens_to_env()
        return {"status": "SUCCESS", "message": "Live Saxo token successfully registered!", "environment": settings.SAXO_ENV}

    raise HTTPException(status_code=400, detail="Missing 'token' or 'code' parameter.")


@app.post("/api/broker/oauth/disconnect")
def disconnect_broker(user=Depends(verify_firebase_token)):
    """
    Clears live access tokens and closes active broker session.
    Safely terminates any live trading API calls.
    """
    saxo_broker_client.access_token = None
    saxo_broker_client.refresh_token = None
    if hasattr(saxo_broker_client, "session"):
        saxo_broker_client.session.cookies.clear()
    logger.info("Broker Live API session disconnected and access tokens cleared.")
    return {"status": "DISCONNECTED", "message": "Live Saxo trading bot connection safely closed."}



@app.get("/api/broker/account", response_model=BrokerAccountSummary)
async def get_broker_account(user=Depends(verify_firebase_token)):
    """Fetches real-time portfolio balance, equity, and margin with concurrency safety."""
    async with broker_concurrency_lock:
        try:
            balances = saxo_broker_client.get_account_balances()
            return BrokerAccountSummary(**balances)
        except ValueError as ve:
            if "authentication required" in str(ve).lower():
                raise HTTPException(status_code=401, detail=str(ve))
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Failed to fetch broker account: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/positions", response_model=BrokerPositionsResponse)
async def get_broker_positions(user=Depends(verify_firebase_token)):
    """Fetches current open stock and option positions with live mark prices and unrealized PnL."""
    async with broker_concurrency_lock:
        try:
            positions_data = saxo_broker_client.get_positions()
            return BrokerPositionsResponse(**positions_data)
        except ValueError as ve:
            if "authentication required" in str(ve).lower():
                raise HTTPException(status_code=401, detail=str(ve))
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Failed to fetch broker positions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/broker/orders", response_model=BrokerOrdersResponse)
async def get_broker_orders(user=Depends(verify_firebase_token)):
    """Fetches active working orders and recently executed order history."""
    async with broker_concurrency_lock:
        try:
            orders_data = saxo_broker_client.get_orders()
            return BrokerOrdersResponse(**orders_data)
        except ValueError as ve:
            if "authentication required" in str(ve).lower():
                raise HTTPException(status_code=401, detail=str(ve))
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Failed to fetch broker orders: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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

# ── Serve Static Frontend Files ─────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "out")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"Mounted static frontend from {frontend_path}")
else:
    logger.warning(f"Frontend static folder not found at {frontend_path}. Running in API-only mode.")
