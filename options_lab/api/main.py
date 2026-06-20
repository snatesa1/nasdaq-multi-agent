from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
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
    ExplainerRequest,
    SocraticTutorRequest,
    ScenarioHedgingRequest,
    SaveSessionRequest,
    UpdateSessionRequest,
    AnalyzeRequest,
)

# Core imports from engine
from engine.gbm_engine import simulate_gbm
from engine.black_scholes import black_scholes_price, black_scholes_greeks, implied_volatility
from engine.monte_carlo import pricing_monte_carlo_standard, pricing_monte_carlo_lab_legacy
from engine.greeks import generate_greeks_surface
from engine.strategy_simulator import simulate_strategy_payoff

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

tutor_service = SocraticTutor()

# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "service": "options-lab", "version": "2.0.0"}

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

# ── Socratic Tutor Chat ────────────────────────────────────────────────────
@app.post("/tutor/ask")
def tutor_ask(params: SocraticTutorRequest, user=Depends(verify_firebase_token)):
    try:
        response = tutor_service.generate_response(
            message=params.message,
            chat_history=params.chat_history,
            context=params.context
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Tutor chat failed: {e}")
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

# ── Serve Static Frontend Files ─────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "out")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    logger.info(f"Mounted static frontend from {frontend_path}")
else:
    logger.warning(f"Frontend static folder not found at {frontend_path}. Running in API-only mode.")
