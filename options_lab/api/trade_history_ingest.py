import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from .pdf_report_parser import SaxoPdfReportParser
from .config import settings

logger = logging.getLogger("trade-history-ingest")

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "optionslab.db")


class TradeHistoryIngestEngine:
    """
    Unified Ingestion & Storage Engine for Multi-Year Saxo Trade Reports & OpenAPI Data.
    """

    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self.parser = SaxoPdfReportParser()
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Creates specialized tables for report storage and forensic indexing."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_conn() as conn:
            # 1. Reports Index
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saxo_reports (
                    report_id TEXT PRIMARY KEY,
                    account_id TEXT,
                    client_name TEXT,
                    from_date TEXT,
                    to_date TEXT,
                    currency TEXT,
                    total_return_pct REAL,
                    total_pnl REAL,
                    initial_value REAL,
                    final_value REAL,
                    net_transfers REAL,
                    cash_balance REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Options History Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saxo_options_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    ticker TEXT,
                    contract TEXT,
                    strike REAL,
                    option_type TEXT,
                    expiry TEXT,
                    costs REAL,
                    pnl REAL,
                    bias_category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Stock History Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saxo_stock_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    symbol TEXT,
                    name TEXT,
                    income REAL,
                    costs REAL,
                    pnl REAL,
                    return_pct REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Quarterly Performance Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saxo_quarterly_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    quarter TEXT,
                    return_pct REAL,
                    pnl REAL,
                    costs REAL,
                    status TEXT
                )
            """)

            # 5. Holdings Snapshot Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saxo_holdings_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    symbol TEXT,
                    name TEXT,
                    asset_type TEXT,
                    qty REAL,
                    open_price REAL,
                    current_price REAL,
                    unrealized_pnl REAL,
                    weight_pct REAL
                )
            """)
            conn.commit()

    def ingest_pdf_bytes(self, pdf_bytes: bytes, filename: str = "Uploaded_Report.pdf") -> Dict[str, Any]:
        """Parses and ingests a raw PDF report into SQLite database."""
        parsed = self.parser.parse_pdf_bytes(pdf_bytes)
        return self._save_parsed_data(parsed, filename)

    def ingest_default_sample(self) -> Dict[str, Any]:
        """Ingests the verified 16-page baseline Saxo Portfolio report data."""
        parsed = self.parser.parse_raw_text("")
        return self._save_parsed_data(parsed, "Saxo_Portfolio_Report_2026.pdf")

    def _save_parsed_data(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        meta = data.get("metadata", {})
        acc = data.get("account_summary", {})
        report_id = f"REP-{meta.get('account_id', 'ACC').replace('/', '_')}-{meta.get('to_date', '2026')}"

        with self._get_conn() as conn:
            # 1. Upsert Report
            conn.execute("""
                INSERT OR REPLACE INTO saxo_reports 
                (report_id, account_id, client_name, from_date, to_date, currency, total_return_pct, total_pnl, initial_value, final_value, net_transfers, cash_balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                meta.get("account_id"),
                meta.get("client_name"),
                meta.get("from_date"),
                meta.get("to_date"),
                meta.get("currency"),
                acc.get("total_return_pct"),
                acc.get("total_pnl"),
                acc.get("initial_account_value"),
                acc.get("final_account_value"),
                acc.get("net_deposits_transfers"),
                acc.get("cash_balance")
            ))

            # 2. Options Trades
            conn.execute("DELETE FROM saxo_options_history WHERE report_id = ?", (report_id,))
            for opt in data.get("options_trades", []):
                conn.execute("""
                    INSERT INTO saxo_options_history 
                    (report_id, ticker, contract, strike, option_type, expiry, costs, pnl, bias_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    opt.get("ticker"),
                    opt.get("contract"),
                    opt.get("strike"),
                    opt.get("option_type"),
                    opt.get("expiry"),
                    opt.get("costs"),
                    opt.get("pnl"),
                    opt.get("bias")
                ))

            # 3. Stock Trades
            conn.execute("DELETE FROM saxo_stock_history WHERE report_id = ?", (report_id,))
            for stk in data.get("stock_trades", []):
                conn.execute("""
                    INSERT INTO saxo_stock_history 
                    (report_id, symbol, name, income, costs, pnl, return_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    stk.get("symbol"),
                    stk.get("name"),
                    stk.get("income"),
                    stk.get("costs"),
                    stk.get("pnl"),
                    stk.get("return_pct")
                ))

            # 4. Quarterly
            conn.execute("DELETE FROM saxo_quarterly_performance WHERE report_id = ?", (report_id,))
            for q in data.get("quarterly_performance", []):
                conn.execute("""
                    INSERT INTO saxo_quarterly_performance 
                    (report_id, quarter, return_pct, pnl, costs, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    q.get("quarter"),
                    q.get("return_pct"),
                    q.get("pnl"),
                    q.get("costs"),
                    q.get("status")
                ))

            # 5. Holdings
            conn.execute("DELETE FROM saxo_holdings_history WHERE report_id = ?", (report_id,))
            for h in data.get("open_holdings", []):
                conn.execute("""
                    INSERT INTO saxo_holdings_history 
                    (report_id, symbol, name, asset_type, qty, open_price, current_price, unrealized_pnl, weight_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    h.get("symbol"),
                    h.get("name"),
                    h.get("type"),
                    h.get("qty"),
                    h.get("open_price"),
                    h.get("current_price"),
                    h.get("unrealized_pnl"),
                    h.get("weight_pct")
                ))
            conn.commit()

        logger.info(f"Successfully ingested and persisted Saxo report: {report_id}")
        return {
            "status": "SUCCESS",
            "report_id": report_id,
            "filename": filename,
            "records_stored": {
                "options_trades": len(data.get("options_trades", [])),
                "stock_trades": len(data.get("stock_trades", [])),
                "quarterly_periods": len(data.get("quarterly_performance", [])),
                "holdings": len(data.get("open_holdings", []))
            },
            "summary": acc
        }

    def get_ingested_reports(self) -> List[Dict[str, Any]]:
        """Lists all ingested historical reports."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM saxo_reports ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_options_history(self, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches granular options history."""
        with self._get_conn() as conn:
            if report_id:
                rows = conn.execute("SELECT * FROM saxo_options_history WHERE report_id = ? ORDER BY pnl ASC", (report_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM saxo_options_history ORDER BY pnl ASC").fetchall()
            return [dict(r) for r in rows]

    def get_stock_history(self, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches stock positions history."""
        with self._get_conn() as conn:
            if report_id:
                rows = conn.execute("SELECT * FROM saxo_stock_history WHERE report_id = ? ORDER BY pnl DESC", (report_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM saxo_stock_history ORDER BY pnl DESC").fetchall()
            return [dict(r) for r in rows]

    def get_quarterly_performance(self, report_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            if report_id:
                rows = conn.execute("SELECT * FROM saxo_quarterly_performance WHERE report_id = ?", (report_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM saxo_quarterly_performance").fetchall()
            return [dict(r) for r in rows]
