from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Dict, Any

class GBMParams(BaseModel):
    S0: float = Field(..., description="Initial asset price")
    mu: float = Field(0.05, description="Drift coefficient (annualized rate of return)")
    sigma: float = Field(0.2, description="Volatility coefficient (annualized)")
    T: float = Field(1.0, description="Time to maturity in years")
    N: int = Field(252, description="Number of steps in path")
    num_paths: int = Field(100, description="Number of simulation paths")

class OptionParams(BaseModel):
    S: float = Field(..., description="Current stock price")
    K: float = Field(..., description="Strike price")
    T: float = Field(..., description="Time to expiry in years")
    r: float = Field(..., description="Risk-free rate")
    sigma: float = Field(..., description="Volatility")
    option_type: str = Field("call", description="'call' or 'put'")

class AnalyticalPricingResponse(BaseModel):
    price: float
    greeks: Dict[str, float]

class MonteCarloPricingRequest(BaseModel):
    S0: float
    K: float
    T: float
    r: float
    sigma: float
    option_type: str
    num_paths: int = 5000

class LegacyLabRequest(BaseModel):
    S0: float = 80.0
    sigma: float = 0.03
    r: float = 0.001
    T: float = 100/365.0
    N: int = 1000
    K: float = 100.0

class StrategyLegRequest(BaseModel):
    asset_type: str = Field("option", description="'stock' or 'option'")
    option_type: Optional[str] = Field(None, description="'call' or 'put' (for option legs)")
    position: str = Field("long", description="'long' or 'short'")
    strike: Optional[float] = Field(None, description="Strike price for options")
    expiry: Optional[float] = Field(None, description="Expiry in years")
    entry_price: float = Field(0.0, description="Cost of stock or option premium at entry")
    quantity: int = Field(1, description="Quantity")

class StrategyRequest(BaseModel):
    legs: List[StrategyLegRequest]
    underlying_spot: float
    r: float = 0.05
    sigma: float = 0.2
    price_range_pct: float = 0.4
    steps: int = 50

class VolSurfaceRequest(BaseModel):
    spot_price: float = Field(100.0, description="Underlying asset spot price")
    base_sigma: float = Field(0.25, description="ATM baseline volatility")
    risk_free_rate: float = Field(0.05, description="Annualized risk-free rate")
    strike_ratios: Optional[List[float]] = Field(None, description="List of strike ratios e.g. [0.8, 0.9, 1.0, 1.1, 1.2]")
    expirations_days: Optional[List[int]] = Field(None, description="List of expiration periods in days")
    skew_intensity: float = Field(0.15, description="Put skew slope intensity")
    smile_convexity: float = Field(0.10, description="OTM wing curvature")

class PositionLeg(BaseModel):
    type: str = Field("stock", description="'stock', 'call', or 'put'")
    symbol: str = Field("AAPL", description="Ticker symbol")
    quantity: float = Field(1.0, description="Quantity of contracts or shares")
    spot_price: float = Field(100.0, description="Current spot price")
    strike: Optional[float] = Field(100.0, description="Strike price for option legs")
    days_to_expiration: Optional[float] = Field(30.0, description="Days to expiration")
    volatility: Optional[float] = Field(0.25, description="Implied volatility")

class PortfolioGreeksRequest(BaseModel):
    positions: List[PositionLeg]
    risk_free_rate: float = Field(0.05, description="Risk-free rate")

class ExplainerRequest(BaseModel):
    concept: str = Field(..., description="Concept to explain (e.g., 'Covered Call', 'Delta')")

class ScenarioHedgingRequest(BaseModel):
    ticker: str = Field(..., description="Asset ticker e.g., 'PANW'")
    shares: int = Field(100, description="Number of shares held")
    cost_basis: float = Field(..., description="Original purchase price of the shares")
    current_price: float = Field(..., description="Current price of the asset")

class SocraticTutorRequest(BaseModel):
    message: str = Field(..., description="Message from the user")
    chat_history: List[Dict[str, str]] = Field(default=[], description="List of past messages")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional simulation state or positions context")
    enable_grounding: bool = Field(False, description="Enable Google Search Grounding for live market news")

class TutorHintRequest(BaseModel):
    chat_history: List[Dict[str, str]] = Field(default=[], description="List of past messages")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional simulation state context")

class SaveSessionRequest(BaseModel):
    title: str = Field(..., description="Human-readable session title")
    messages: List[Dict[str, str]] = Field(..., description="Full chat transcript")

class UpdateSessionRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Updated chat transcript")
    title: Optional[str] = Field(None, description="Optional new title")

# ── Fundamental Index Models ──────────────────────────────────────────────────

class FundamentalIndexRequest(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="Optional custom list of tickers to index")

class FundamentalIndexResponse(BaseModel):
    universe_size: int
    total_market_cap: float
    tickers: List[Dict[str, Any]]

# ── Portfolio Models ──────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    tickers: List[str] = Field(..., description="List of stock ticker symbols to analyze")

# ── Earnings Scanner Models ───────────────────────────────────────────────────

class EarningsScanRequest(BaseModel):
    low_threshold_pct: float = Field(0.20, description="Max percentage above 52-week low to consider deep value")
    min_open_interest: int = Field(5000, description="Minimum total front-month option open interest")

# ── Broker Gateway & Execution Models (Type-Safe Live & SIM) ─────────────────

class BrokerEnvironment(str):
    SIMULATION = "SIMULATION"
    LIVE = "LIVE"

class BrokerAccountSummary(BaseModel):
    status: str = Field(..., description="Connection status e.g. LIVE_SAXO_CONNECTED, SIM_SANDBOX_MOCK")
    environment: str = Field("SIMULATION", description="'SIMULATION' or 'LIVE'")
    cash_available: float = Field(0.0, description="Cash available for trading")
    total_equity: float = Field(0.0, description="Total account equity")
    margin_available: float = Field(0.0, description="Margin available")
    margin_used: float = Field(0.0, description="Margin currently utilized")
    currency: str = Field("USD", description="Base account currency")
    account_id: Optional[str] = Field(None, description="Masked account identifier")
    updated_at: str = Field(..., description="ISO timestamp of data fetch")

class BrokerPosition(BaseModel):
    position_id: str = Field(..., description="Unique position identifier or UIC")
    uic: int = Field(..., description="Universal Instrument Code")
    symbol: str = Field(..., description="Stock or underlying ticker")
    description: str = Field(..., description="Full contract or asset name")
    asset_type: str = Field("Stock", description="'Stock', 'StockOption', 'Contract', etc.")
    option_type: Optional[str] = Field(None, description="'call' or 'put' if option")
    strike_price: Optional[float] = Field(None, description="Strike price for options")
    expiry_date: Optional[str] = Field(None, description="Expiry date string YYYY-MM-DD")
    amount: float = Field(..., description="Holding amount or contract count")
    open_price: float = Field(..., description="Average entry / execution price")
    current_price: float = Field(..., description="Current mark / spot market price")
    market_value: float = Field(0.0, description="Total position market value")
    unrealized_pnl: float = Field(0.0, description="Unrealized profit or loss in USD")
    unrealized_pnl_pct: float = Field(0.0, description="Unrealized P&L percentage")
    currency: str = Field("USD", description="Currency of position")

class BrokerPositionsResponse(BaseModel):
    environment: str = Field("SIMULATION", description="'SIMULATION' or 'LIVE'")
    status: str = Field(..., description="Connection status")
    total_positions_count: int = Field(0, description="Count of open positions")
    total_unrealized_pnl: float = Field(0.0, description="Aggregate unrealized PnL")
    positions: List[BrokerPosition] = Field(default=[], description="List of open positions")
    updated_at: str = Field(..., description="ISO timestamp")

class BrokerOrder(BaseModel):
    order_id: str = Field(..., description="Broker Order ID")
    uic: int = Field(..., description="Universal Instrument Code")
    symbol: str = Field(..., description="Asset symbol")
    description: str = Field(..., description="Instrument description")
    asset_type: str = Field("StockOption", description="Asset type")
    buy_sell: str = Field("Buy", description="'Buy' or 'Sell'")
    order_type: str = Field("Limit", description="'Limit', 'Market', 'StopLimit'")
    amount: float = Field(..., description="Order quantity")
    order_price: float = Field(..., description="Placed order limit price")
    filled_price: Optional[float] = Field(None, description="Actual execution filled price")
    status: str = Field(..., description="Status: 'Filled', 'Working', 'Cancelled', 'Rejected'")
    placed_at: str = Field(..., description="Order placement timestamp")
    executed_at: Optional[str] = Field(None, description="Execution timestamp if filled")

class BrokerOrdersResponse(BaseModel):
    environment: str = Field("SIMULATION", description="'SIMULATION' or 'LIVE'")
    status: str = Field(..., description="Connection status")
    total_orders_count: int = Field(0, description="Count of orders returned")
    orders: List[BrokerOrder] = Field(default=[], description="List of historical/active orders")
    updated_at: str = Field(..., description="ISO timestamp")

