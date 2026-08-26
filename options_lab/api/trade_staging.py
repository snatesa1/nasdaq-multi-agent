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
        trade_id = existing_prop["trade_id"] if existing_prop else f"TRD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()

        strategy = rec.get("strategy", "CSP").upper()
        direction = rec.get("direction", "BULLISH").upper()
        strike = float(rec.get("strike", 0.0))
        delta = float(rec.get("delta", 0.0))
        dte = int(rec.get("dte", 30))
        premium_est = float(rec.get("premium_estimate", 0.0))
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
            "symbol": symbol,
            "name": rec.get("name", symbol),
            "strategy": strategy,
            "direction": direction,
            "strike": strike,
            "delta": delta,
            "dte": dte,
            "premium_estimate": premium_est,
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
            "status": "PROPOSED",
            "saxo_order_id": None,
            "saxo_order_response": None,
            "proposed_at": now_iso,
            "approved_at": None,
            "executed_at": None,
            "week_label": week_label
        }

        # Persist to SQLite database via db helper
        database.save_staged_trade(staged_record)
        logger.info(f"Staged trade {trade_id} [{symbol} {strategy} ${strike}] for week {week_label}.")
        return staged_record

    def approve_and_execute_trade(self, trade_id: str) -> Dict[str, Any]:
        """
        User approval endpoint:
        1. Fetches staged record.
        2. Re-audits live margin and safety shield.
        3. If approved, calls Saxo Client place_order API.
        4. Updates SQLite record to EXECUTING / FILLED / BLOCKED.
        """
        record = database.get_staged_trade_by_id(trade_id)
        if not record:
            raise ValueError(f"Staged trade {trade_id} not found.")

        if record["status"] in ["FILLED", "EXECUTING"]:
            return {"status": record["status"], "message": "Trade already approved/executed.", "record": record}

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

        # 2. Final Live Safety Shield Audit
        safety_eval = self.safety_shield.evaluate_order(
            symbol=symbol,
            asset_type="StockOption",
            buy_sell="Sell" if "CSP" in strategy or "CC" in strategy else "Buy",
            strike=strike,
            delta=delta,
            dte=dte,
            projected_margin_util_pct=margin_eval.get("projected_margin_util_pct", 0.0)
        )
        if not safety_eval["approved"]:
            record["status"] = "BLOCKED"
            record["safety_check_result"] = json.dumps(safety_eval)
            database.save_staged_trade(record)
            return {
                "status": "BLOCKED",
                "trade_id": trade_id,
                "infractions": safety_eval.get("infractions", []),
                "record": record
            }

        # Determine buy/sell action and derivative type
        buy_sell = "Sell" if ("CSP" in strategy or "CC" in strategy or "SHORT" in strategy) else "Buy"
        asset_type = "StockOption" if ("CSP" in strategy or "CC" in strategy or "OPTION" in strategy) else "Stock"
        opt_type = "Put" if "CSP" in strategy else ("Call" if "CC" in strategy else "Put")

        # 3. Resolve UIC for instrument
        uic = None
        if asset_type == "StockOption":
            uic = self.saxo_client.resolve_option_contract_uic(
                symbol=symbol,
                strike=strike,
                option_type=opt_type,
                dte=dte
            )

        if not uic:
            instruments = self.saxo_client.search_instruments(symbol, asset_types=[asset_type, "Stock"])
            if instruments and isinstance(instruments, list):
                first_inst = instruments[0]
                uic = int(first_inst.get("Uic") or first_inst.get("Identifier") or first_inst.get("PrimaryListing") or 0)

        if not uic:
            uic = SaxoClient.KNOWN_UICS.get(symbol, 123456)

        # 4. Place Order on Saxo
        record["approved_at"] = now_iso
        record["status"] = "EXECUTING"
        database.save_staged_trade(record)

        try:
            saxo_res = self.saxo_client.place_order(
                uic=uic,
                asset_type=asset_type,
                amount=contracts,
                buy_sell=buy_sell,
                order_type="Limit",
                order_price=premium_est if asset_type == "StockOption" else spot_price,
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
            logger.error(f"Saxo order placement failed for {trade_id}: {e}")
            record["status"] = "EXECUTION_ERROR"
            record["saxo_order_response"] = json.dumps({"error": str(e)})
            database.save_staged_trade(record)
            return {
                "status": "EXECUTION_ERROR",
                "trade_id": trade_id,
                "reasons": [str(e)],
                "error": str(e),
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
