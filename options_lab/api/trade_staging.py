import logging
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .saxo_client import SaxoClient
from .margin_guardian import MarginGuardian
from .safety_shield import BehavioralSafetyShield
from . import db as database

logger = logging.getLogger("trade-staging")


class TradeStagingEngine:
    """
    Trade Recommendation Staging & Dual-Key Approval Lifecycle Engine.
    
    State Machine:
    PROPOSED -> APPROVED -> EXECUTING -> FILLED / REJECTED / BLOCKED / EXPIRED
    """

    def __init__(
        self,
        saxo_client: Optional[SaxoClient] = None,
        margin_guardian: Optional[MarginGuardian] = None,
        safety_shield: Optional[BehavioralSafetyShield] = None
    ):
        self.saxo_client = saxo_client or SaxoClient()
        self.margin_guardian = margin_guardian or MarginGuardian(saxo_client=self.saxo_client)
        self.safety_shield = safety_shield or BehavioralSafetyShield()

    def stage_recommendation(self, rec: Dict[str, Any], week_label: str) -> Dict[str, Any]:
        """
        Stages a new trade recommendation into the SQLite database as PROPOSED.
        """
        symbol = rec.get("symbol", "UNKNOWN").upper()
        existing_prop = database.find_proposed_trade(symbol, week_label)
        trade_id = rec.get("trade_id") or rec.get("id") or rec.get("staged_trade_id") or (existing_prop["trade_id"] if existing_prop else f"TRD-{uuid.uuid4().hex[:8].upper()}")
        now_iso = datetime.now().isoformat()

        strategy = rec.get("strategy", "CSP").upper()
        direction = rec.get("direction", "BULLISH").upper()
        strike = float(rec.get("strike", 0.0))
        delta = float(rec.get("delta", 0.0))
        dte = int(rec.get("dte", 30))
        premium_est = float(rec.get("premium_estimate", 0.0))
        premium_est = self.saxo_client.quantize_order_price(premium_est, asset_type="StockOption")
        contracts = int(rec.get("contracts", 1))
        spot_price = float(rec.get("spot_price", 0.0))
        thesis = rec.get("thesis", "Market structure signal")
        edge_source = rec.get("edge_source", "Macro News Analysis")
        risk_rating = int(rec.get("risk_rating", 3))

        # Check underlying shares owned for Covered Call safety validation
        underlying_shares = 0.0
        try:
            pos_resp = self.saxo_client.get_positions()
            for p in pos_resp.get("positions", []):
                if p.get("symbol", "").upper() == symbol and p.get("asset_type") == "Stock":
                    underlying_shares += float(p.get("amount", 0.0))
        except Exception:
            try:
                cached_p = database.get_saxo_cache("positions")
                if cached_p and isinstance(cached_p, dict):
                    for p in cached_p.get("positions", []):
                        if p.get("symbol", "").upper() == symbol and p.get("asset_type") == "Stock":
                            underlying_shares += float(p.get("amount", 0.0))
            except Exception:
                pass

        # Run pre-flight margin evaluation
        margin_eval = self.margin_guardian.validate_trade_margin(
            strategy=strategy,
            strike=strike,
            contracts=contracts,
            spot_price=spot_price,
            option_premium=premium_est
        )

        # Run pre-flight behavioral safety evaluation (including CC underlying stock check)
        safety_eval = self.safety_shield.evaluate_order(
            symbol=symbol,
            asset_type="StockOption" if "PUT" in strategy or "CALL" in strategy else "Stock",
            buy_sell="Sell" if "CSP" in strategy or "CC" in strategy or "SHORT" in strategy else "Buy",
            option_type="call" if "CC" in strategy or "CALL" in strategy else "put",
            strike=strike,
            delta=delta,
            dte=dte,
            order_value=strike * 100.0 * contracts if "PUT" in strategy else spot_price * 100.0 * contracts,
            projected_margin_util_pct=margin_eval.get("projected_margin_util_pct", 0.0),
            underlying_shares_owned=underlying_shares,
            contracts=contracts
        )

        staged_record = {
            "trade_id": trade_id,
            "id": trade_id,
            "staged_trade_id": trade_id,
            "symbol": symbol,
            "name": rec.get("name", symbol),
            "sector": rec.get("sector", "Information Technology"),
            "strategy": strategy,
            "direction": direction,
            "strike": strike,
            "delta": delta,
            "dte": dte,
            "premium_estimate": premium_est,
            "bid_price": float(rec.get("bid_price", 0.0) or 0.0),
            "ask_price": float(rec.get("ask_price", 0.0) or 0.0),
            "spread": float(rec.get("spread", 0.0) or 0.0),
            "pricing_source": rec.get("pricing_source", "OPRA_LIVE"),
            "uic": rec.get("contract_uic") or rec.get("uic"),
            "contract_uic": rec.get("contract_uic") or rec.get("uic"),
            "contract_description": rec.get("contract_description"),
            "contract_symbol": rec.get("contract_symbol"),
            "expiration_date": rec.get("expiration_date"),
            "contracts": contracts,
            "spot_price": spot_price,
            "annualized_roc_pct": float(rec.get("annualized_roc_pct", 0.0)),
            "max_margin_impact_pct": margin_eval.get("estimated_margin_impact", 0.0),
            "collateral_required": margin_eval.get("collateral_required", 0.0),
            "thesis": thesis,
            "edge_source": edge_source,
            "risk_rating": risk_rating,
            "pillars": rec.get("pillars", {}),
            "margin_check_result": json.dumps(margin_eval),
            "safety_check_result": json.dumps(safety_eval),
            "status": rec.get("status", "PROPOSED"),
            "saxo_order_id": None,
            "saxo_order_response": None,
            "proposed_at": now_iso,
            "approved_at": None,
            "executed_at": None,
            "week_label": week_label,
            "seasonality_bias": rec.get("seasonality_bias"),
            "seasonality_win_rate_pct": rec.get("seasonality_win_rate_pct"),
            "seasonality_median_return_pct": rec.get("seasonality_median_return_pct"),
            "worst_historical_drawdown_pct": rec.get("worst_historical_drawdown_pct"),
            "iv_rank_pct": rec.get("iv_rank_pct"),
            "volatility_regime": rec.get("volatility_regime"),
            "has_earnings_blackout": rec.get("has_earnings_blackout"),
            "next_earnings_date": rec.get("next_earnings_date"),
            "buffer_rationale": rec.get("buffer_rationale"),
            "recommended_otm_buffer_pct": rec.get("recommended_otm_buffer_pct"),
            "rejection_reason": rec.get("rejection_reason")
        }

        # Persist to SQLite database via db helper
        database.save_staged_trade(staged_record)
        rec["trade_id"] = trade_id
        rec["id"] = trade_id
        rec["staged_trade_id"] = trade_id
        logger.info(f"Staged trade {trade_id} [{symbol} {strategy} ${strike}] for week {week_label}.")
        return staged_record

    def approve_and_execute_trade(self, trade_id: str) -> Dict[str, Any]:
        """
        Descriptive Summary:
            Authenticates and executes a staged trade order against Saxo OpenAPI or simulation sandbox.
            Executes pre-flight margin headroom verification, safety shield audit, contract UIC validation,
            idempotency locks against duplicate placement, and post-timeout broker reconciliation.

        Parameters:
            trade_id (str): Unique staged trade identifier (e.g. 'TRD-762BD7A8').

        Returns:
            Dict[str, Any]: Execution result containing 'status', 'trade_id', 'reasons', 'saxo_response', and 'record'.

        Exceptions / Side Effects:
            Raises ValueError if trade_id not found in SQLite database.
            Mutates SQLite staged_trades record to EXECUTING, PLACED, FILLED, UNCONFIRMED_TIMEOUT, or error states.
            Transmits real-money order request to Saxo OpenAPI endpoint when live execution is active.

        Concrete Executable Usage Example:
            >>> manager = StagedTradeManager()
            >>> res = manager.approve_and_execute_trade("TRD-762BD7A8")
            >>> assert res["status"] in ["PLACED", "FILLED", "UNCONFIRMED_TIMEOUT", "BLOCKED_SAFETY_CONFIG"]
        """
        record = database.get_staged_trade_by_id(trade_id)
        if not record:
            raise ValueError(f"Staged trade {trade_id} not found.")

        # Idempotency Shield: Block duplicate executions if trade is already active or unconfirmed
        if record["status"] in ["FILLED", "PLACED", "EXECUTING", "UNCONFIRMED_TIMEOUT"]:
            return {
                "status": record["status"],
                "message": f"Trade {trade_id} is already in state '{record['status']}'. Duplicate order submission blocked to protect capital.",
                "record": record
            }

        now_iso = datetime.now().isoformat()
        symbol = str(record.get("symbol", "AAPL")).strip().upper()
        strategy = str(record.get("strategy", "CSP")).strip().upper()
        strike = float(record.get("strike", 0.0))
        contracts = int(record.get("contracts", 1))
        premium_est = float(record.get("premium_estimate", 0.0))
        spot_price = float(record.get("spot_price", 0.0))
        delta = float(record.get("delta", 0.20))
        dte = int(record.get("dte", 30))

        # 1. Final Live Margin Headroom Audit
        margin_eval = self.margin_guardian.validate_trade_margin(
            strategy=strategy,
            strike=strike,
            contracts=contracts,
            spot_price=spot_price,
            option_premium=premium_est
        )
        if not margin_eval["approved"]:
            record["status"] = "MARGIN_EXCEEDED"
            record["margin_check_result"] = json.dumps(margin_eval)
            database.save_staged_trade(record)
            return {
                "status": "MARGIN_EXCEEDED",
                "trade_id": trade_id,
                "reasons": margin_eval.get("reasons", ["Margin cap exceeded."]),
                "record": record
            }

        # Determine buy/sell action and derivative type
        buy_sell = "Sell" if ("CSP" in strategy or "CC" in strategy or "SHORT" in strategy) else "Buy"
        asset_type = "StockOption" if ("CSP" in strategy or "CC" in strategy or "OPTION" in strategy) else "Stock"
        opt_type = "Put" if "CSP" in strategy else ("Call" if "CC" in strategy else "Put")

        # 2. Final Live Safety Shield Audit
        safety_eval = self.safety_shield.evaluate_order(
            symbol=symbol,
            asset_type=asset_type,
            buy_sell=buy_sell,
            option_type=opt_type,
            strike=strike,
            delta=delta,
            dte=dte,
            order_value=float(record.get("order_value", 0.0) or 0.0),
            projected_margin_util_pct=float(margin_eval.get("projected_margin_util_pct", 0.0) or 0.0),
            expiry_date=record.get("expiration_date"),
            contracts=contracts
        )
        if not safety_eval["approved"]:
            record["status"] = "BLOCKED"
            record["safety_check_result"] = json.dumps(safety_eval)
            database.save_staged_trade(record)
            infractions = safety_eval.get("infractions", [])
            return {
                "status": "BLOCKED",
                "trade_id": trade_id,
                "infractions": infractions,
                "reasons": infractions,
                "record": record
            }

        # 3. Resolve & Verify Contract UIC with Zero-Guessing Integrity Guard
        uic = record.get("contract_uic") or record.get("uic")
        expected_expiry = record.get("expiration_date")

        if asset_type == "StockOption":
            # If UIC was not pre-staged, attempt exact resolution
            if not uic:
                meta = self.saxo_client.resolve_exact_option_contract(
                    symbol=symbol,
                    strike=strike,
                    option_type=opt_type,
                    target_expiration_date=expected_expiry,
                    dte=dte
                )
                if meta:
                    uic = meta["contract_uic"]
                    expected_expiry = meta["expiration_date"]
                    record["contract_uic"] = uic
                    record["contract_description"] = meta["contract_description"]
                    record["contract_symbol"] = meta["contract_symbol"]
                    record["expiration_date"] = expected_expiry

            # Hard Integrity Pre-Flight Check: Verify contract details against Saxo live
            if uic and int(uic) > 0:
                uic = int(uic)
                details = self.saxo_client.get_instrument_details(uic, "StockOption")
                if details and not details.get("is_fallback"):
                    contract_desc = details.get("Description", "")
                    contract_expiry = str(details.get("ExpiryDate", "")).split("T")[0] if details.get("ExpiryDate") else ""
                    contract_sym = str(details.get("Symbol", "")).split(":")[0].split("/")[0].upper()

                    # Audit Expiry Date match
                    if expected_expiry and contract_expiry and contract_expiry != expected_expiry:
                        error_msg = (
                            f"CONTRACT INTEGRITY FAILURE: Staged expiry is '{expected_expiry}', but resolved Saxo contract "
                            f"'{contract_desc}' (UIC: {uic}) expires on '{contract_expiry}'. Order execution blocked to prevent wrong-month execution."
                        )
                        logger.error(error_msg)
                        record["status"] = "BLOCKED_EXPIRY_MISMATCH"
                        database.save_staged_trade(record)
                        return {
                            "status": "BLOCKED_EXPIRY_MISMATCH",
                            "trade_id": trade_id,
                            "reasons": [error_msg],
                            "record": record
                        }

                    # Audit Underlying Ticker match
                    if contract_sym and not contract_sym.startswith("INST-") and not (contract_sym == symbol.upper() or contract_sym.startswith(symbol.upper())):
                        error_msg = (
                            f"CONTRACT TICKER MISMATCH: Expected underlying ticker '{symbol}', but resolved Saxo contract "
                            f"'{contract_desc}' (UIC: {uic}) belongs to '{contract_sym}'. Order execution blocked."
                        )
                        logger.error(error_msg)
                        record["status"] = "BLOCKED_TICKER_MISMATCH"
                        database.save_staged_trade(record)
                        return {
                            "status": "BLOCKED_TICKER_MISMATCH",
                            "trade_id": trade_id,
                            "reasons": [error_msg],
                            "record": record
                        }

            if not uic or int(uic) <= 0:
                error_msg = f"Cannot approve trade {trade_id}: No verified Saxo Option Contract UIC exists for {symbol} {strike} {opt_type} expiring {expected_expiry}."
                logger.error(error_msg)
                record["status"] = "BLOCKED_NO_CONTRACT"
                database.save_staged_trade(record)
                return {
                    "status": "BLOCKED_NO_CONTRACT",
                    "trade_id": trade_id,
                    "reasons": [error_msg],
                    "record": record
                }
        else:
            # Stock asset type resolution
            if not uic:
                instruments = self.saxo_client.search_instruments(symbol, asset_types=["Stock"])
                if instruments and isinstance(instruments, list):
                    for inst in instruments:
                        inst_sym = (inst.get("Symbol") or "").split(":")[0].upper()
                        if inst_sym == symbol.upper():
                            uic = int(inst.get("Uic") or inst.get("Identifier") or 0)
                            break
            if not uic:
                uic = SaxoClient.KNOWN_UICS.get(symbol, 123456)
            uic = int(uic)

        # 4. Place Order on Saxo
        record["approved_at"] = now_iso
        record["status"] = "EXECUTING"
        database.save_staged_trade(record)

        try:
            clean_price = self.saxo_client.quantize_order_price(
                price=premium_est if asset_type == "StockOption" else spot_price,
                uic=uic,
                asset_type=asset_type
            )
            saxo_res = self.saxo_client.place_order(
                uic=uic,
                asset_type=asset_type,
                amount=contracts,
                buy_sell=buy_sell,
                order_type="Limit",
                order_price=clean_price,
                to_open_close="ToOpen"
            )

            record["executed_at"] = datetime.now().isoformat()
            record["saxo_order_id"] = str(saxo_res.get("order_id", saxo_res.get("OrderId", f"ORD-SAXO-{trade_id}")))
            record["saxo_order_response"] = json.dumps(saxo_res)
            
            # Check if order went through or blocked by config flag or error
            reasons = []
            if saxo_res.get("status") in ["LIVE_EXECUTION_BLOCKED_BY_SAFETY_SHIELD"]:
                record["status"] = "BLOCKED_SAFETY_CONFIG"
                reasons.append("Live order blocked by broker safety config (BROKER_ALLOW_LIVE_EXECUTION=False).")
            elif saxo_res.get("status") == "UNCONFIRMED_TIMEOUT":
                record["status"] = "UNCONFIRMED_TIMEOUT"
                reasons.append(saxo_res.get("error", "Saxo order request timed out. Order locked to prevent duplicates. Please check Saxo TraderGO."))
            elif saxo_res.get("reconciled") and saxo_res.get("status") == "PLACED":
                record["status"] = "PLACED"
                reasons.append(saxo_res.get("message", "Order confirmed on Saxo via post-timeout broker reconciliation."))
            elif "error" in saxo_res or saxo_res.get("status", "").endswith("_ERROR"):
                record["status"] = "EXECUTION_ERROR"
                raw_err = saxo_res.get("error", "")
                if not raw_err or "401" in str(raw_err) or "Unauthorized" in str(raw_err) or not self.saxo_client.access_token:
                    reasons.append("Saxo Live Session Expired (HTTP 401). Please update your 24-Hour Developer Token or reconnect your broker.")
                else:
                    reasons.append(str(raw_err))
            else:
                record["status"] = "FILLED" if self.saxo_client.environment == "SIM" and "order_id" in saxo_res else "PLACED"

            database.save_staged_trade(record)

            return {
                "status": record["status"],
                "trade_id": trade_id,
                "reasons": reasons,
                "saxo_response": saxo_res,
                "record": record
            }
        except Exception as e:
            err_str = str(e)
            logger.error(f"Saxo order placement failed for {trade_id}: {err_str}")
            is_timeout = "timed out" in err_str.lower() or "timeout" in err_str.lower()
            if is_timeout:
                record["status"] = "UNCONFIRMED_TIMEOUT"
                err_text = (
                    f"Broker gateway timed out for trade {trade_id}. "
                    f"Status unconfirmed on broker; duplicate submission locked to protect capital. Please check Saxo TraderGO."
                )
            else:
                record["status"] = "EXECUTION_ERROR"
                err_text = err_str
            record["saxo_order_response"] = json.dumps({"error": err_text})
            database.save_staged_trade(record)
            return {
                "status": record["status"],
                "trade_id": trade_id,
                "reasons": [err_text],
                "error": err_text,
                "record": record
            }

    def reject_trade(self, trade_id: str, reason: str = "User rejected") -> Dict[str, Any]:
        """User explicit rejection."""
        record = database.get_staged_trade_by_id(trade_id)
        if not record:
            raise ValueError(f"Staged trade {trade_id} not found.")

        record["status"] = "REJECTED"
        record["saxo_order_response"] = json.dumps({"rejection_reason": reason})
        database.save_staged_trade(record)
        return {"status": "REJECTED", "trade_id": trade_id, "reason": reason, "record": record}
