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
        trade_id = f"TRD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()

        symbol = rec.get("symbol", "UNKNOWN").upper()
        strategy = rec.get("strategy", "CSP").upper()
        direction = rec.get("direction", "BULLISH").upper()
        strike = float(rec.get("strike", 0.0))
        delta = float(rec.get("delta", 0.0))
        dte = int(rec.get("dte", 35))
        premium_est = float(rec.get("premium_estimate", 0.0))
        contracts = int(rec.get("contracts", 1))
        spot_price = float(rec.get("spot_price", 0.0))
        thesis = rec.get("thesis", "Market structure signal")
        edge_source = rec.get("edge_source", "Macro News Analysis")
        risk_rating = int(rec.get("risk_rating", 3))

        # Run pre-flight margin evaluation
        margin_eval = self.margin_guardian.validate_trade_margin(
            strategy=strategy,
            strike=strike,
            contracts=contracts,
            spot_price=spot_price,
            option_premium=premium_est
        )

        # Run pre-flight behavioral safety evaluation
        safety_eval = self.safety_shield.evaluate_order(
            symbol=symbol,
            asset_type="StockOption" if "PUT" in strategy or "CALL" in strategy else "Stock",
            buy_sell="Sell" if "CSP" in strategy or "CC" in strategy or "SHORT" in strategy else "Buy",
            strike=strike,
            delta=delta,
            dte=dte,
            order_value=strike * 100.0 * contracts if "PUT" in strategy else spot_price * 100.0 * contracts,
            projected_margin_util_pct=margin_eval.get("projected_margin_util_pct", 0.0)
        )

        staged_record = {
            "trade_id": trade_id,
            "symbol": symbol,
            "strategy": strategy,
            "direction": direction,
            "strike": strike,
            "delta": delta,
            "dte": dte,
            "premium_estimate": premium_est,
            "contracts": contracts,
            "spot_price": spot_price,
            "max_margin_impact_pct": margin_eval.get("estimated_margin_impact", 0.0),
            "collateral_required": margin_eval.get("collateral_required", 0.0),
            "thesis": thesis,
            "edge_source": edge_source,
            "risk_rating": risk_rating,
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
        symbol = record["symbol"]
        strategy = record["strategy"]
        strike = record["strike"]
        contracts = record["contracts"]
        premium_est = record["premium_estimate"]
        spot_price = record["spot_price"]

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
            delta=record["delta"],
            dte=record["dte"],
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

        # 3. Resolve UIC for instrument
        uic = SaxoClient.KNOWN_UICS.get(symbol, 0)
        if not uic:
            instruments = self.saxo_client.search_instruments(symbol, asset_types=["StockOption", "Stock"])
            if instruments and isinstance(instruments, list):
                first_inst = instruments[0]
                uic = int(first_inst.get("Uic") or first_inst.get("Identifier") or first_inst.get("PrimaryListing") or 123456)
            else:
                uic = 123456

        # Determine buy/sell action
        buy_sell = "Sell" if ("CSP" in strategy or "CC" in strategy or "SHORT" in strategy) else "Buy"
        asset_type = "StockOption" if ("CSP" in strategy or "CC" in strategy or "OPTION" in strategy) else "Stock"

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
                order_price=premium_est if asset_type == "StockOption" else spot_price
            )

            record["executed_at"] = datetime.now().isoformat()
            record["saxo_order_id"] = str(saxo_res.get("order_id", saxo_res.get("OrderId", f"ORD-SAXO-{trade_id}")))
            record["saxo_order_response"] = json.dumps(saxo_res)
            
            # Check if order went through or blocked by config flag or error
            if saxo_res.get("status") in ["LIVE_EXECUTION_BLOCKED_BY_SAFETY_SHIELD"]:
                record["status"] = "BLOCKED_SAFETY_CONFIG"
            elif "error" in saxo_res or saxo_res.get("status", "").endswith("_ERROR"):
                record["status"] = "EXECUTION_ERROR"
            else:
                record["status"] = "FILLED" if self.saxo_client.environment == "SIM" and "order_id" in saxo_res else "PLACED"

            database.save_staged_trade(record)

            return {
                "status": record["status"],
                "trade_id": trade_id,
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
