"""
db.py — Unified SQLite database module for OptionsLab.

Refactored from sessions.py to serve as a single entry point for all
persistent data: tutor sessions, portfolios, and portfolio tickers.

Stores data in /data/optionslab.db inside the container,
falling back to a local path for development.
"""

import sqlite3
import json
import uuid
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Database Path ─────────────────────────────────────────────────────────────
_DATA_DIR = os.environ.get(
    "DB_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)
_DB_PATH = os.path.join(_DATA_DIR, "optionslab.db")


# ── Firestore Initialization (with SQLite fallback) ──────────────────────────
_USE_FIRESTORE = False
_firestore_client = None

if os.getenv("USE_FIRESTORE", "false").lower() == "true" or os.getenv("K_SERVICE"):
    try:
        from google.cloud import firestore
        _firestore_client = firestore.Client()
        _USE_FIRESTORE = True
        logger.info("Firestore storage initialized for Socratic tutor sessions.")
    except Exception as e:
        logger.warning(f"Could not initialize Firestore client: {e}. Falling back to SQLite for sessions.")
else:
    logger.info("Using SQLite database for local sessions storage.")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Create all tables if they don't exist."""
    with _get_conn() as conn:
        # ── Tutor Sessions ────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id              TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                messages        TEXT NOT NULL,
                key_learnings   TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN key_learnings TEXT")
        except sqlite3.OperationalError:
            pass
        # ── Portfolios ────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                source_url  TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        # ── Portfolio Tickers ─────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_tickers (
                id            TEXT PRIMARY KEY,
                portfolio_id  TEXT NOT NULL,
                symbol        TEXT NOT NULL,
                name          TEXT,
                current_price REAL,
                change        REAL,
                high          REAL,
                low           REAL,
                volume        INTEGER,
                last_synced   TEXT,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                UNIQUE(portfolio_id, symbol)
            )
        """)
        # ── Saxo Live Cache ──────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saxo_cache (
                key         TEXT PRIMARY KEY,
                data        TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        # ── Staged Trades Lifecycle Table ────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS staged_trades (
                trade_id              TEXT PRIMARY KEY,
                symbol                TEXT NOT NULL,
                strategy              TEXT NOT NULL,
                direction             TEXT NOT NULL,
                strike                REAL NOT NULL,
                delta                 REAL,
                dte                   INTEGER,
                premium_estimate      REAL,
                contracts             INTEGER DEFAULT 1,
                spot_price            REAL,
                max_margin_impact_pct REAL,
                collateral_required   REAL,
                thesis                TEXT,
                edge_source           TEXT,
                risk_rating           INTEGER DEFAULT 3,
                margin_check_result   TEXT,
                safety_check_result   TEXT,
                status                TEXT NOT NULL,
                saxo_order_id         TEXT,
                saxo_order_response   TEXT,
                proposed_at           TEXT NOT NULL,
                approved_at           TEXT,
                executed_at           TEXT,
                week_label            TEXT NOT NULL,
                bid_price             REAL,
                ask_price             REAL,
                spread                REAL,
                pricing_source        TEXT
            )
        """)
        # Dynamic schema migration for existing databases
        for col, col_type in [
            ("bid_price", "REAL"),
            ("ask_price", "REAL"),
            ("spread", "REAL"),
            ("pricing_source", "TEXT")
        ]:
            try:
                conn.execute(f"ALTER TABLE staged_trades ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        conn.commit()


# Initialise on import
_init_db()


# ═══════════════════════════════════════════════════════════════════════════════
#  TUTOR SESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_key_learnings(messages: List[Dict[str, str]]) -> str:
    try:
        from .tutor import SocraticTutor
        tutor = SocraticTutor()
        return tutor.summarize_learnings(messages)
    except Exception as e:
        logger.error(f"Failed to generate key learnings: {e}")
        return "- Discussed financial markets and quantitative modeling strategies."

def list_sessions() -> List[Dict[str, Any]]:
    """Return all sessions ordered by last update (newest first), without messages."""
    if _USE_FIRESTORE and _firestore_client:
        try:
            from google.cloud import firestore
            docs = _firestore_client.collection("tutor_sessions").order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
            results = []
            for doc in docs:
                d = doc.to_dict()
                d.pop("messages", None)
                results.append(d)
            return results
        except Exception as e:
            logger.error(f"Firestore list_sessions failed: {e}. Falling back to SQLite.")

    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at, key_learnings FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_session(title: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Persist a new session and return it."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    learnings = get_key_learnings(messages)

    if _USE_FIRESTORE and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            session_data = {
                "id": session_id,
                "title": title,
                "created_at": now,
                "updated_at": now,
                "messages": messages,
                "key_learnings": learnings
            }
            doc_ref.set(session_data)
            return session_data
        except Exception as e:
            logger.error(f"Firestore create_session failed: {e}. Falling back to SQLite.")

    messages_json = json.dumps(messages)

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at, messages, key_learnings) VALUES (?,?,?,?,?,?)",
            (session_id, title, now, now, messages_json, learnings)
        )
        conn.commit()

    return {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": messages,
        "key_learnings": learnings
    }


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a full session by ID (including messages)."""
    if _USE_FIRESTORE and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Firestore get_session failed: {e}. Falling back to SQLite.")

    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["messages"] = json.loads(data["messages"])
    return data


def update_session(
    session_id: str, 
    messages: List[Dict[str, str]], 
    title: Optional[str] = None,
    generate_learnings: bool = False
) -> Optional[Dict[str, Any]]:
    """Append / overwrite messages for an existing session."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Only invoke LLM summarization on explicit title updates or when requested
    learnings = None
    if generate_learnings or (title is not None and len(messages) >= 4):
        learnings = get_key_learnings(messages)

    if _USE_FIRESTORE and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            update_data: Dict[str, Any] = {
                "messages": messages,
                "updated_at": now,
            }
            if title:
                update_data["title"] = title
            if learnings:
                update_data["key_learnings"] = learnings
            doc_ref.set(update_data, merge=True)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Firestore update_session failed: {e}. Falling back to SQLite.")

    messages_json = json.dumps(messages)

    with _get_conn() as conn:
        if title and learnings:
            conn.execute(
                "UPDATE sessions SET messages=?, updated_at=?, title=?, key_learnings=? WHERE id=?",
                (messages_json, now, title, learnings, session_id)
            )
        elif title:
            conn.execute(
                "UPDATE sessions SET messages=?, updated_at=?, title=? WHERE id=?",
                (messages_json, now, title, session_id)
            )
        elif learnings:
            conn.execute(
                "UPDATE sessions SET messages=?, updated_at=?, key_learnings=? WHERE id=?",
                (messages_json, now, learnings, session_id)
            )
        else:
            conn.execute(
                "UPDATE sessions SET messages=?, updated_at=? WHERE id=?",
                (messages_json, now, session_id)
            )
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["messages"] = json.loads(data["messages"])
    return data


def delete_session(session_id: str) -> bool:
    """Delete a session by ID. Returns True if found and deleted."""
    if _USE_FIRESTORE and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"Firestore delete_session failed: {e}. Falling back to SQLite.")

    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
    return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIOS
# ═══════════════════════════════════════════════════════════════════════════════

def list_portfolios() -> List[Dict[str, Any]]:
    """Return all portfolios with their tickers and ticker counts."""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT id, name, source_url, created_at, updated_at
            FROM portfolios
            ORDER BY updated_at DESC
        """).fetchall()
        
        portfolios = []
        for r in rows:
            p = dict(r)
            tickers = conn.execute(
                "SELECT * FROM portfolio_tickers WHERE portfolio_id=? ORDER BY symbol",
                (p["id"],)
            ).fetchall()
            ticker_list = []
            for t in tickers:
                td = dict(t)
                td["price"] = td.get("current_price", 0.0)
                ticker_list.append(td)
            p["tickers"] = ticker_list
            p["ticker_count"] = len(tickers)
            portfolios.append(p)
            
    return portfolios


def create_portfolio(name: str, source_url: Optional[str] = None) -> Dict[str, Any]:
    """Create a new portfolio."""
    portfolio_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolios (id, name, source_url, created_at, updated_at) VALUES (?,?,?,?,?)",
            (portfolio_id, name, source_url, now, now)
        )
        conn.commit()

    return {
        "id": portfolio_id,
        "name": name,
        "source_url": source_url,
        "created_at": now,
        "updated_at": now,
        "ticker_count": 0
    }


def get_portfolio(portfolio_id: str) -> Optional[Dict[str, Any]]:
    """Get a portfolio with all its tickers."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM portfolios WHERE id=?", (portfolio_id,)).fetchone()
        if row is None:
            return None

        tickers = conn.execute(
            "SELECT * FROM portfolio_tickers WHERE portfolio_id=? ORDER BY symbol",
            (portfolio_id,)
        ).fetchall()

    data = dict(row)
    ticker_list = []
    for t in tickers:
        td = dict(t)
        td["price"] = td.get("current_price", 0.0)
        ticker_list.append(td)
    data["tickers"] = ticker_list
    return data


def delete_portfolio(portfolio_id: str) -> bool:
    """Delete a portfolio and all its tickers (cascade)."""
    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM portfolios WHERE id=?", (portfolio_id,))
        conn.commit()
    return cursor.rowcount > 0


def upsert_portfolio_tickers(
    portfolio_id: str,
    tickers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Insert or update tickers for a portfolio. Returns the final ticker list."""
    now = datetime.now(timezone.utc).isoformat()

    with _get_conn() as conn:
        for t in tickers:
            ticker_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO portfolio_tickers
                    (id, portfolio_id, symbol, name, current_price, change, high, low, volume, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                    name=excluded.name,
                    current_price=excluded.current_price,
                    change=excluded.change,
                    high=excluded.high,
                    low=excluded.low,
                    volume=excluded.volume,
                    last_synced=excluded.last_synced
            """, (
                ticker_id,
                portfolio_id,
                t.get("symbol", "").upper().strip(),
                t.get("name"),
                t.get("current_price"),
                t.get("change"),
                t.get("high"),
                t.get("low"),
                t.get("volume"),
                now
            ))

        # Update portfolio timestamp
        conn.execute(
            "UPDATE portfolios SET updated_at=? WHERE id=?",
            (now, portfolio_id)
        )
        conn.commit()

        # Return final list
        rows = conn.execute(
            "SELECT * FROM portfolio_tickers WHERE portfolio_id=? ORDER BY symbol",
            (portfolio_id,)
        ).fetchall()

    res = []
    for r in rows:
        rd = dict(r)
        rd["price"] = rd.get("current_price", 0.0)
        res.append(rd)
    return res


# ═══════════════════════════════════════════════════════════════════════════════
#  SAXO LIVE PERSISTENT CACHE
# ═══════════════════════════════════════════════════════════════════════════════

def set_saxo_cache(key: str, data: Any):
    """Store Saxo broker data in SQLite cache."""
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO saxo_cache (key, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(data), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to write saxo cache for {key}: {e}")

def get_saxo_cache(key: str) -> Optional[Any]:
    """Retrieve cached Saxo broker data from SQLite."""
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT data FROM saxo_cache WHERE key = ?", (key,)).fetchone()
            if row:
                return json.loads(row["data"])
    except Exception as e:
        logger.error(f"Failed to read saxo cache for {key}: {e}")
    return None

def clear_saxo_cache():
    """Wipes all cached Saxo broker data on disconnect."""
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM saxo_cache")
            conn.commit()
            logger.info("Cleared all Saxo cache records from SQLite.")
    except Exception as e:
        logger.error(f"Failed to clear saxo cache: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGED TRADES LIFECYCLE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def save_staged_trade(record: Dict[str, Any]):
    """Inserts or updates a staged trade record in SQLite."""
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO staged_trades (
                    trade_id, symbol, strategy, direction, strike, delta, dte,
                    premium_estimate, contracts, spot_price, max_margin_impact_pct,
                    collateral_required, thesis, edge_source, risk_rating,
                    margin_check_result, safety_check_result, status,
                    saxo_order_id, saxo_order_response, proposed_at,
                    approved_at, executed_at, week_label,
                    bid_price, ask_price, spread, pricing_source
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?
                )
                ON CONFLICT(trade_id) DO UPDATE SET
                    status = excluded.status,
                    margin_check_result = excluded.margin_check_result,
                    safety_check_result = excluded.safety_check_result,
                    saxo_order_id = excluded.saxo_order_id,
                    saxo_order_response = excluded.saxo_order_response,
                    approved_at = excluded.approved_at,
                    executed_at = excluded.executed_at,
                    bid_price = COALESCE(excluded.bid_price, staged_trades.bid_price),
                    ask_price = COALESCE(excluded.ask_price, staged_trades.ask_price),
                    spread = COALESCE(excluded.spread, staged_trades.spread),
                    pricing_source = COALESCE(excluded.pricing_source, staged_trades.pricing_source)
                """,
                (
                    record.get("trade_id"), record.get("symbol"), record.get("strategy"), record.get("direction"),
                    record.get("strike"), record.get("delta"), record.get("dte"), record.get("premium_estimate"),
                    record.get("contracts", 1), record.get("spot_price"), record.get("max_margin_impact_pct"),
                    record.get("collateral_required"), record.get("thesis"), record.get("edge_source"), record.get("risk_rating", 3),
                    record.get("margin_check_result"), record.get("safety_check_result"), record.get("status", "PROPOSED"),
                    record.get("saxo_order_id"), record.get("saxo_order_response"), record.get("proposed_at"),
                    record.get("approved_at"), record.get("executed_at"), record.get("week_label"),
                    record.get("bid_price"), record.get("ask_price"), record.get("spread"), record.get("pricing_source")
                )
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save staged trade {record.get('trade_id')}: {e}")

def get_staged_trade_by_id(trade_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a staged trade record by trade_id."""
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM staged_trades WHERE trade_id = ?", (trade_id,)).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"Failed to fetch staged trade {trade_id}: {e}")
    return None

def find_proposed_trade(symbol: str, week_label: str) -> Optional[Dict[str, Any]]:
    """Finds an existing proposed trade for a specific symbol and week."""
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM staged_trades WHERE symbol = ? AND week_label = ? AND status = 'PROPOSED' LIMIT 1",
                (symbol.upper(), week_label)
            ).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"Failed to find proposed trade for {symbol}: {e}")
    return None

def list_staged_trades(week_label: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists staged trades filtered by optional week_label and status."""
    try:
        with _get_conn() as conn:
            query = "SELECT * FROM staged_trades WHERE 1=1"
            params = []
            if week_label:
                query += " AND week_label = ?"
                params.append(week_label)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY proposed_at DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to list staged trades: {e}")
        return []



