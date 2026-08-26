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
    risk_free_rate: float = Field(0.05, description="Annualized risk-free interest rate")
    strike_ratios: Optional[List[float]] = Field(None, description="Strike price ratios")
    expirations_days: Optional[List[int]] = Field(None, description="Expirations in days")
    skew_intensity: float = Field(0.15, description="Put-skew slope intensity")
    smile_convexity: float = Field(0.10, description="OTM wings curvature")

class PortfolioPositionRequest(BaseModel):
    symbol: str
    quantity: float = 1.0
    type: Optional[str] = Field("stock", description="'stock', 'call', 'put'")
    asset_type: Optional[str] = Field("stock", description="'stock' or 'option'")
    spot_price: Optional[float] = None
    entry_price: Optional[float] = 0.0
    strike: Optional[float] = None
    days_to_expiration: Optional[float] = None
    volatility: Optional[float] = None

class PortfolioGreeksRequest(BaseModel):
    positions: List[PortfolioPositionRequest]
    risk_free_rate: float = Field(0.05, description="Risk-free rate")
    r: Optional[float] = None
    sigma: Optional[float] = 0.25

class SocraticTutorRequest(BaseModel):
    session_id: Optional[str] = None
    message: Optional[str] = None
    question: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    context: Optional[str] = None
    enable_grounding: bool = False

class TutorHintRequest(BaseModel):
    session_id: Optional[str] = None
    current_topic: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    context: Optional[str] = None

class ExplainerRequest(BaseModel):
    metric_name: str
    value: str
    context: Optional[str] = None

class ScenarioHedgingRequest(BaseModel):
    spot_price: float
    shock_pct: float = -0.20
    portfolio_delta: float = 100.0

class SaveSessionRequest(BaseModel):
    session_id: str
    title: str
    messages: List[Dict[str, Any]]
    key_learnings: Optional[List[str]] = []

class UpdateSessionRequest(BaseModel):
    messages: Optional[List[Dict[str, Any]]] = None
    key_learnings: Optional[List[str]] = None

class AnalyzeRequest(BaseModel):
    symbol: str = "AAPL"
    portfolio_equity: float = 100000.0

class FundamentalIndexRequest(BaseModel):
    top_n: int = 20
    rebalance_freq: str = "annually"

class FundamentalIndexMetric(BaseModel):
    symbol: str
    name: str
    price: float
    market_cap_weight: float
    fundamental_weight: float
    book_value: float
    cash_flow: float
    net_dividends: float
    sales: float
    arnott_score: float

class FundamentalIndexResponse(BaseModel):
    timestamp: str
    metrics: List[FundamentalIndexMetric]

class EarningsScanRequest(BaseModel):
    universe: str = Field("sp500", description="'sp500', 'nasdaq100', 'watchlist'")

class BrokerAccountSummary(BaseModel):
    status: str = Field(..., description="Connection status string")
    environment: str = Field("SIMULATION", description="'SIMULATION' or 'LIVE'")
    cash_available: float = Field(0.0, description="Available cash balance")
    total_equity: float = Field(0.0, description="Total account equity / Net Asset Value")
    margin_available: float = Field(0.0, description="Available margin for trading")
    margin_used: float = Field(0.0, description="Margin consumed by open positions")
    currency: str = Field("USD", description="Account base currency")
    account_id: str = Field("LIVE-ACC-PRIMARY", description="Account identifier")
    updated_at: str = Field(..., description="ISO timestamp")

class BrokerPosition(BaseModel):
    position_id: str = Field(..., description="Position ID from Saxo")
    uic: int = Field(..., description="Universal Instrument Code")
    symbol: str = Field(..., description="Clean stock ticker e.g. AAPL")
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

class SafetyCheckRequest(BaseModel):
    symbol: str = Field(..., description="Target ticker symbol")
    asset_type: str = Field("StockOption", description="Asset type e.g. Stock, StockOption")
    buy_sell: str = Field("Sell", description="'Buy' or 'Sell'")
    strike: Optional[float] = Field(None, description="Strike price if option")
    delta: Optional[float] = Field(None, description="Option Delta")
    dte: Optional[int] = Field(None, description="Days to expiration")
    order_value: float = Field(0.0, description="Total dollar value of proposed order")
    portfolio_equity: float = Field(100000.0, description="Current total portfolio equity")
    current_ticker_exposure: float = Field(0.0, description="Existing exposure in ticker")
    recent_loss_amount: float = Field(0.0, description="Recent major loss if within 24h")

class TradeApprovalRequest(BaseModel):
    trade_id: str = Field(..., description="Unique staged trade ID to approve and execute")

class TradeRejectRequest(BaseModel):
    trade_id: str = Field(..., description="Unique staged trade ID to reject")
    reason: Optional[str] = Field("User rejected", description="Optional rejection reason")

class MarginStatusResponse(BaseModel):
    total_equity: float
    cash_available: float
    margin_used: float
    margin_utilization_pct: float
    max_margin_limit_pct: float = 15.0
    allowed_margin_dollars: float
    remaining_margin_headroom: float
    is_within_limit: bool
    currency: str = "USD"
    updated_at: str
