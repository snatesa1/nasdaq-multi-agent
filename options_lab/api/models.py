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

class ExplainerRequest(BaseModel):
    concept: str = Field(..., description="Concept to explain (e.g., 'Covered Call', 'Delta')")

class ScenarioHedgingRequest(BaseModel):
    ticker: str = Field(..., description="Asset ticker e.g., 'PANW'")
    shares: int = Field(100, description="Number of shares held")
    cost_basis: float = Field(..., description="Original purchase price of the shares")
    current_price: float = Field(..., description="Current price of the asset")

class SocraticTutorRequest(BaseModel):
    message: str = Field(..., description="Message from the user")
    chat_history: List[Dict[str, str]] = Field(default=[], description="List of past messages: [{'role': 'user'|'assistant', 'content': str}]")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional simulation state or positions context")

class SaveSessionRequest(BaseModel):
    title: str = Field(..., description="Human-readable session title")
    messages: List[Dict[str, str]] = Field(..., description="Full chat transcript")

class UpdateSessionRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Updated chat transcript")
    title: Optional[str] = Field(None, description="Optional new title")

# ── Portfolio Models ──────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    tickers: List[str] = Field(..., description="List of stock ticker symbols to analyze")

# ── Earnings Scanner Models ───────────────────────────────────────────────────

class EarningsScanRequest(BaseModel):
    low_threshold_pct: float = Field(0.20, description="Max percentage above 52-week low to consider deep value")
    min_open_interest: int = Field(5000, description="Minimum total front-month option open interest")

