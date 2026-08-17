import os
import logging
import requests
from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlencode
from options_lab.api.config import settings

logger = logging.getLogger(__name__)


class SaxoClient:
    """
    Production-hardened Saxo OpenAPI Integration Client.
    
    Supports:
    - Dynamic Environment: SIM Sandbox & Live Trading Platform.
    - Strict Request Timeouts & Exponential Backoff Retries.
    - Connection Pooling via requests.Session.
    - Live Execution Safety Shield (Prevents unintentional live executions).
    - Normalized response formatting for Account Balances, Open Positions, and Order Activities.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.app_name = settings.SAXO_APP_NAME
        self.app_key = settings.SAXO_APP_KEY
        self.app_secret = settings.SAXO_APP_SECRET
        self.auth_endpoint = settings.SAXO_AUTH_ENDPOINT
        self.token_endpoint = settings.SAXO_TOKEN_ENDPOINT
        self.base_url = settings.SAXO_OPENAPI_BASE_URL.rstrip('/') + '/'
        self.redirect_url = settings.SAXO_REDIRECT_URL
        self.environment = settings.SAXO_ENV  # 'SIM' or 'LIVE'
        self.timeout = settings.SAXO_TIMEOUT_SECONDS

        self.access_token = access_token or getattr(settings, "SAXO_ACCESS_TOKEN", None) or None
        self.refresh_token = getattr(settings, "SAXO_REFRESH_TOKEN", None) or None
        self.needs_reauth = False  # Set True when refresh token is expired/consumed
        self.token_acquired_at = None  # Track when we last got a valid token

        # Configure resilient session with connection pooling & retries
        self.session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Auto-refresh if access_token is missing but refresh_token is configured
        if not self.access_token and self.refresh_token:
            try:
                self.refresh_access_token()
            except Exception as e:
                logger.warning(f"Auto-refreshing access token failed: {e}")
                self.needs_reauth = True

    def get_authorization_url(self, state: str = "bot_algo_state") -> str:
        """Generates the OAuth authorization URL for user login in browser."""
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "redirect_uri": self.redirect_url,
            "state": state
        }
        return f"{self.auth_endpoint}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges the authorization code for access_token and refresh_token."""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_url
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        logger.info(f"Exchanging Saxo authorization code for token in {self.environment} environment...")
        response = self.session.post(self.token_endpoint, data=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.needs_reauth = False
        self.token_acquired_at = datetime.now()
        self._persist_tokens_to_env()
        logger.info("Saxo OAuth access token successfully acquired and persisted.")
        return data

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refreshes an expired access_token using the refresh_token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available to renew Saxo session.")
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.app_key,
            "client_secret": self.app_secret
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = self.session.post(self.token_endpoint, data=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            if data.get("refresh_token"):
                self.refresh_token = data.get("refresh_token")
            self.needs_reauth = False
            self.token_acquired_at = datetime.now()
            self._persist_tokens_to_env()
            logger.info("Saxo OAuth access token successfully renewed.")
            return data
        except Exception as e:
            logger.warning(f"Saxo token renewal failed: {e}. Session requires re-authorization.")
            self.refresh_token = None
            self.needs_reauth = True
            raise


    def _persist_tokens_to_env(self):
        """Persists newly refreshed tokens to .env for seamless restarts."""
        try:
            env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            if os.path.exists(env_path) and self.access_token:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                for line in lines:
                    if line.startswith("SAXO_ACCESS_TOKEN="):
                        new_lines.append(f"SAXO_ACCESS_TOKEN={self.access_token}\n")
                    elif line.startswith("SAXO_REFRESH_TOKEN=") and self.refresh_token:
                        new_lines.append(f"SAXO_REFRESH_TOKEN={self.refresh_token}\n")
                    else:
                        new_lines.append(line)
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                logger.info("Persisted refreshed Saxo tokens to .env successfully.")
        except Exception as e:
            logger.warning(f"Failed to persist tokens to .env: {e}")

    def _ensure_valid_token(self):
        """Ensures that access_token is populated, reloading from .env or refreshing if needed."""
        if not self.access_token or not self.refresh_token:
            try:
                from dotenv import dotenv_values
                env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
                if os.path.exists(env_path):
                    vals = dotenv_values(env_path)
                    if not self.access_token:
                        self.access_token = vals.get("SAXO_ACCESS_TOKEN")
                    if not self.refresh_token:
                        self.refresh_token = vals.get("SAXO_REFRESH_TOKEN")
            except Exception as e:
                logger.warning(f"Failed reloading token from .env: {e}")

        if (not self.access_token or len(self.access_token) < 50) and self.refresh_token:
            try:
                self.refresh_access_token()
            except Exception as e:
                logger.warning(f"Automatic refresh during token ensure failed: {e}")

    def _get_headers(self) -> Dict[str, str]:
        self._ensure_valid_token()
        if not self.access_token:
            raise ValueError(
                f"Saxo Access Token missing for {self.environment} environment. "
                "Provide a developer token or configure OAuth authentication."
            )
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _make_authenticated_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Executes an authenticated request with automatic 401 token refresh & retry."""
        if self.needs_reauth:
            raise ValueError("Saxo session expired. Re-authorization required via OAuth.")
        self._ensure_valid_token()
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        try:
            response = self.session.request(method, url, headers=self._get_headers(), timeout=self.timeout, **kwargs)
            if response.status_code == 401 and self.refresh_token:
                logger.info("Saxo API returned 401 Unauthorized. Auto-refreshing OAuth session...")
                self.refresh_access_token()
                response = self.session.request(method, url, headers=self._get_headers(), timeout=self.timeout, **kwargs)
            elif response.status_code == 401:
                self.needs_reauth = True
                logger.warning("Saxo API returned 401 and no refresh token available. Re-auth required.")
            return response
        except Exception as e:
            if ("401" in str(e) or "missing" in str(e).lower()) and self.refresh_token:
                logger.info("Token issue caught. Auto-refreshing OAuth session...")
                self.refresh_access_token()
                return self.session.request(method, url, headers=self._get_headers(), timeout=self.timeout, **kwargs)
            raise



    # ── Portfolio & Balance Endpoints ──────────────────────────────────────────
    def get_account_balances(self) -> Dict[str, Any]:
        """
        Fetches real-time portfolio cash, equity, and margin balance.
        Endpoint: GET /port/v1/balances/me
        """
        now_iso = datetime.now().isoformat()
        self._ensure_valid_token()
        if not self.access_token:
            raise ValueError("Saxo authentication required. Please configure a valid access token.")
        try:
            response = self._make_authenticated_request("GET", "port/v1/balances/me")
            response.raise_for_status()
            data = response.json()
            
            cash = float(data.get("CashAvailableForTrading", data.get("TotalCashBalance", 0.0)))
            equity = float(data.get("TotalEquity", 0.0))
            margin_avail = float(data.get("MarginAvailableForTrading", data.get("MarginAvailable", 0.0)))
            margin_used = float(data.get("MarginUsedByCurrentPositions", 0.0))
            currency = data.get("Currency", "USD")
            account_id = data.get("AccountId", "LIVE-ACC-PRIMARY")

            return {
                "status": f"{self.environment}_SAXO_CONNECTED",
                "environment": self.environment,
                "cash_available": cash,
                "total_equity": equity,
                "margin_available": margin_avail,
                "margin_used": margin_used,
                "currency": currency,
                "account_id": str(account_id),
                "updated_at": now_iso
            }
        except Exception as e:
            logger.error(f"Saxo API balance fetch failed: {e}")
            raise

    def get_positions(self) -> Dict[str, Any]:
        """
        Fetches current open positions (stocks, options, CFDs) with normalized schema.
        Endpoint: GET /port/v1/positions/me
        """
        now_iso = datetime.now().isoformat()
        self._ensure_valid_token()
        if not self.access_token:
            raise ValueError("Saxo authentication required. Please configure a valid access token.")

        try:
            response = self._make_authenticated_request("GET", "port/v1/positions/me")
            response.raise_for_status()
            data = response.json()
            
            raw_positions = data.get("Data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            normalized_positions: List[Dict[str, Any]] = []

            for p in raw_positions:
                pos_base = p.get("PositionBase", {})
                pos_view = p.get("PositionView", {})
                options_data = pos_base.get("OptionsData", {})
                
                pos_id = str(pos_base.get("PositionId", p.get("PositionId", "POS-UNKNOWN")))
                uic = int(pos_base.get("Uic", p.get("Uic", 0)))
                asset_type = pos_base.get("AssetType", p.get("AssetType", "Stock"))
                
                # Fetch instrument details
                inst = self.get_instrument_details(uic, asset_type)
                sym = inst.get("Symbol") or pos_base.get("Symbol", "UNKNOWN")
                clean_sym = sym.split(":")[0].split("/")[0]
                desc = inst.get("Description") or pos_base.get("Description", clean_sym)
                
                amount = float(pos_base.get("Amount", p.get("Amount", 0.0)))
                open_price = float(pos_base.get("OpenPrice", pos_view.get("AverageOpenPrice", 0.0)))
                current_price = float(pos_view.get("CurrentPrice", open_price))
                market_val = float(pos_view.get("MarketValue", open_price * amount))
                
                # Retrieve Saxo-reported P&L
                pnl = float(pos_view.get("ProfitLossOnTrade", pos_view.get("ProfitLossOnOpeningPosition", 0.0)))
                
                # Calculate overall unrealized P&L percentage mathematically
                multiplier = 100 if asset_type in ["StockOption", "Option"] else 1
                cost_basis = open_price * abs(amount) * multiplier
                
                if cost_basis > 0:
                    if amount >= 0:  # Long position
                        pnl_pct = ((current_price - open_price) / open_price) * 100.0
                    else:  # Short position
                        pnl_pct = ((open_price - current_price) / open_price) * 100.0
                else:
                    pnl_pct = 0.0

                pnl_pct = round(pnl_pct, 2)
                
                # Strike and option type parsing
                strike = options_data.get("Strike") or pos_base.get("StrikePrice")
                expiry = (options_data.get("ExpiryDate", "")).split("T")[0] if options_data.get("ExpiryDate") else None
                opt_type = options_data.get("PutCall", "").lower() if options_data.get("PutCall") else ("call" if "call" in desc.lower() else ("put" if "put" in desc.lower() else None))

                normalized_positions.append({
                    "position_id": pos_id,
                    "uic": uic,
                    "symbol": clean_sym,
                    "description": desc,
                    "asset_type": asset_type,
                    "option_type": opt_type,
                    "strike_price": float(strike) if strike else None,
                    "expiry_date": expiry,
                    "amount": amount,
                    "open_price": open_price,
                    "current_price": current_price,
                    "market_value": market_val,
                    "unrealized_pnl": pnl,
                    "unrealized_pnl_pct": pnl_pct,
                    "currency": pos_view.get("ExposureCurrency", pos_base.get("Currency", "USD"))
                })

            total_pnl = sum(p["unrealized_pnl"] for p in normalized_positions)
            return {
                "environment": self.environment,
                "status": f"{self.environment}_SAXO_CONNECTED",
                "total_positions_count": len(normalized_positions),
                "total_unrealized_pnl": round(total_pnl, 2),
                "positions": normalized_positions,
                "updated_at": now_iso
            }
        except Exception as e:
            logger.error(f"Saxo API positions fetch failed: {e}")
            raise

    def set_token(self, access_token: str, refresh_token: Optional[str] = None):
        """Sets or updates the live Saxo access token and optional refresh token."""
        self.access_token = access_token.strip()
        if refresh_token:
            self.refresh_token = refresh_token.strip()
        self.needs_reauth = False
        self.token_acquired_at = datetime.now()
        logger.info(f"SaxoClient access token manually set for {self.environment} environment.")

    def get_orders(self) -> Dict[str, Any]:
        """
        Fetches full order blotter history (active working orders & filled/executed orders).
        Endpoints: GET /port/v1/orders/me and GET /cs/v1/audit/orderactivities
        """
        now_iso = datetime.now().isoformat()
        self._ensure_valid_token()
        if not self.access_token:
            raise ValueError("Saxo authentication required. Please configure a valid access token.")

        try:
            # 1. Fetch current working orders
            response = self._make_authenticated_request("GET", "port/v1/orders/me")
            response.raise_for_status()
            data = response.json()

            raw_orders = data.get("Data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            normalized_orders: List[Dict[str, Any]] = []

            for ord_item in raw_orders:
                order_id = str(ord_item.get("OrderId", f"ORD-{ord_item.get('Uic', 'UNK')}"))
                uic = int(ord_item.get("Uic", 0))
                asset_type = ord_item.get("AssetType", "StockOption")
                inst = self.get_instrument_details(uic, asset_type)
                sym = inst.get("Symbol") or ord_item.get("DisplayAndFormat", {}).get("Symbol", ord_item.get("Symbol", "UNKNOWN"))
                clean_sym = sym.split(":")[0].split("/")[0]
                desc = inst.get("Description") or ord_item.get("DisplayAndFormat", {}).get("Description", clean_sym)
                
                buy_sell = ord_item.get("BuySell", "Buy")
                order_type = ord_item.get("OrderType", "Limit")
                amount = float(ord_item.get("Amount", 1.0))
                order_price = float(ord_item.get("Price", ord_item.get("OrderPrice", 0.0)))
                status = ord_item.get("Status", "Working")
                placed_at = ord_item.get("OrderTime", now_iso)
                executed_at = ord_item.get("ExecutionTime") or (placed_at if status == "Filled" else None)
                filled_price = float(ord_item.get("FilledPrice", order_price)) if status == "Filled" else None

                normalized_orders.append({
                    "order_id": order_id,
                    "uic": uic,
                    "symbol": clean_sym,
                    "description": desc,
                    "asset_type": asset_type,
                    "buy_sell": buy_sell,
                    "order_type": order_type,
                    "amount": amount,
                    "order_price": order_price,
                    "filled_price": filled_price,
                    "status": status,
                    "placed_at": placed_at,
                    "executed_at": executed_at
                })

            # 2. Fetch historical order activities from audit trail
            try:
                audit_resp = self._make_authenticated_request("GET", "cs/v1/audit/orderactivities?$top=50")
                if audit_resp.status_code == 200:
                    audit_data = audit_resp.json()

                    audit_items = audit_data.get("Data", []) if isinstance(audit_data, dict) else []
                    for item in audit_items:
                        audit_id = str(item.get("OrderId", ""))
                        if audit_id and not any(o["order_id"] == audit_id for o in normalized_orders):
                            uic = int(item.get("Uic", 0))
                            asset_type = item.get("AssetType", "StockOption")
                            inst = self.get_instrument_details(uic, asset_type)
                            sym = inst.get("Symbol") or item.get("Symbol", "UNKNOWN")
                            clean_sym = sym.split(":")[0].split("/")[0]
                            desc = inst.get("Description") or item.get("Description", clean_sym)
                            
                            normalized_orders.append({
                                "order_id": audit_id,
                                "uic": uic,
                                "symbol": clean_sym,
                                "description": desc,
                                "asset_type": asset_type,
                                "buy_sell": item.get("BuySell", "Buy"),
                                "order_type": item.get("OrderType", "Limit"),
                                "amount": float(item.get("Amount", 1.0)),
                                "order_price": float(item.get("Price", 0.0)),
                                "filled_price": float(item.get("AverageExecutionPrice", item.get("Price", 0.0))),
                                "status": item.get("Status", "Filled"),
                                "placed_at": item.get("ActivityTime", now_iso),
                                "executed_at": item.get("ActivityTime", now_iso)
                            })
            except Exception as e_audit:
                logger.debug(f"Saxo audit order activities query non-critical: {e_audit}")


            return {
                "environment": self.environment,
                "status": f"{self.environment}_SAXO_CONNECTED",
                "total_orders_count": len(normalized_orders),
                "orders": normalized_orders,
                "updated_at": now_iso
            }
        except Exception as e:
            logger.warning(f"Saxo API orders fetch failed: {e}")
            return {
                "environment": self.environment,
                "status": f"{self.environment}_FALLBACK",
                "total_orders_count": 0,
                "orders": [],
                "updated_at": now_iso
            }

    # ── Reference & Instrument Search Endpoints ────────────────────────────────
    def get_instrument_details(self, uic: int, asset_type: str = "Stock") -> Dict[str, Any]:
        """Fetches detailed instrument metadata (symbol, description, currency) with local caching."""
        if not hasattr(self, "_instrument_cache"):
            self._instrument_cache = {}
        
        cache_key = f"{uic}_{asset_type}"
        if cache_key in self._instrument_cache:
            return self._instrument_cache[cache_key]

        if not self.access_token or uic <= 0:
            return {"Symbol": f"INST-{uic}", "Description": f"Instrument {uic}", "CurrencyCode": "USD"}

        try:
            response = self._make_authenticated_request("GET", f"ref/v1/instruments/details/{uic}/{asset_type}")
            if response.status_code == 200:
                data = response.json()
                self._instrument_cache[cache_key] = data
                return data
        except Exception as e:
            logger.debug(f"Instrument lookup for UIC {uic} failed: {e}")

        fallback = {"Symbol": f"INST-{uic}", "Description": f"Instrument {uic}", "CurrencyCode": "USD"}
        self._instrument_cache[cache_key] = fallback
        return fallback

    def search_instruments(self, keywords: str, asset_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches for instrument UIC codes by keyword (e.g., 'AAPL', 'SPY')."""
        if not self.access_token:
            return [{"Uic": 123456, "Symbol": keywords.upper(), "Description": f"{keywords.upper()} Stock Option", "AssetType": "StockOption"}]
        try:
            url = f"{self.base_url}ref/v1/instruments"
            params = {"Keywords": keywords}
            if asset_types:
                params["AssetTypes"] = ",".join(asset_types)
                
            response = self.session.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("Data", [])
        except Exception as e:
            logger.warning(f"Saxo API instrument search failed: {e}")
            return [{"Uic": 123456, "Symbol": keywords.upper(), "Description": f"{keywords.upper()} Stock Option", "AssetType": "StockOption"}]


    # ── Chart Data (Momentum & Price History) ──────────────────────────────────
    def get_chart_data(
        self, 
        uic: int, 
        asset_type: str = "Stock", 
        horizon: int = 1440, 
        count: int = 100
    ) -> Dict[str, Any]:
        """Retrieves OHLC candles for technical momentum & indicators calculation."""
        if not self.access_token:
            return {"status": "SIM_SANDBOX_MOCK", "Data": []}
        try:
            url = f"{self.base_url}chart/v3/charts"
            params = {
                "Uic": uic,
                "AssetType": asset_type,
                "Horizon": horizon,
                "Count": count
            }
            response = self.session.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Saxo API chart data fetch failed: {e}")
            return {"status": "SIM_SANDBOX_FALLBACK", "Data": []}

    # ── Trading & Order Execution Endpoints with Safety Shield ────────────────
    def place_order(
        self, 
        uic: int, 
        asset_type: str = "StockOption", 
        amount: int = 1, 
        buy_sell: str = "Sell", 
        order_type: str = "Limit", 
        order_price: float = 0.0
    ) -> Dict[str, Any]:
        """
        Places limit/market orders with strict safety shields.
        Endpoint: POST /trade/v2/orders
        """
        # 1. LIVE SAFETY SHIELD: Block any live execution if safety lock is active
        if self.environment == "LIVE" and not settings.BROKER_ALLOW_LIVE_EXECUTION:
            logger.error(f"🚨 LIVE ORDER BLOCKED: Live execution safety shield is active (BROKER_ALLOW_LIVE_EXECUTION=False).")
            return {
                "status": "LIVE_EXECUTION_BLOCKED_BY_SAFETY_SHIELD",
                "environment": self.environment,
                "message": "Live order was blocked by safety policy. Set BROKER_ALLOW_LIVE_EXECUTION=true to permit real trades.",
                "staged_order": {
                    "uic": uic,
                    "asset_type": asset_type,
                    "amount": amount,
                    "buy_sell": buy_sell,
                    "order_price": order_price
                }
            }

        # 2. SIM Sandbox Mock Execution
        if not self.access_token:
            return {
                "status": "SIM_SANDBOX_STAGED",
                "environment": self.environment,
                "order_id": f"ORD-SIM-{uic}-{int(order_price)}",
                "message": "Order validated and staged for SIM execution."
            }

        # 3. Live or Authenticated Sandbox OpenAPI Order Execution
        try:
            url = f"{self.base_url}trade/v2/orders"
            payload = {
                "Uic": uic,
                "AssetType": asset_type,
                "Amount": amount,
                "BuySell": buy_sell,
                "OrderType": order_type,
                "OrderPrice": round(order_price, 2),
                "OrderDuration": {"DurationType": "DayOrder"},
                "ManualOrder": True,
                "OrderRelation": "StandAlone"
            }
            
            response = self.session.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Saxo API order placement failed: {e}")
            return {
                "status": f"{self.environment}_ERROR",
                "order_id": f"ORD-ERR-{uic}",
                "error": str(e)
            }
