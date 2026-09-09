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
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Database Path ─────────────────────────────────────────────────────────────
_DATA_DIR = os.environ.get(
    "DB_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
)
_DB_PATH = os.path.join(_DATA_DIR, "optionslab.db")


# ── Storage Configuration (SQLite Primary, Configurable Firestore Override/Fallback) ──
# Local SQLite is the primary database for OptionsLab offline/local operations.
# To override and persist to Firestore, set TUTOR_STORAGE_BACKEND="firestore" or USE_FIRESTORE="true".
_USE_FIRESTORE = False
_firestore_client = None

_storage_backend_env = os.getenv("TUTOR_STORAGE_BACKEND", "sqlite").lower()
if _storage_backend_env == "firestore" or os.getenv("USE_FIRESTORE", "false").lower() == "true":
    try:
        from google.cloud import firestore
        _firestore_client = firestore.Client()
        _USE_FIRESTORE = True
        logger.info("Firestore storage initialized for Socratic tutor sessions (override active).")
    except Exception as e:
        logger.warning(f"Could not initialize Firestore client: {e}. Falling back to local SQLite.")
        _USE_FIRESTORE = False
else:
    logger.info("Using local SQLite database for Socratic tutor sessions (primary).")


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
        # ── Broker Tokens (Persistent OAuth Credentials) ─────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broker_tokens (
                broker_id     TEXT PRIMARY KEY,
                access_token  TEXT NOT NULL,
                refresh_token TEXT,
                token_type    TEXT DEFAULT 'Bearer',
                expires_at    TEXT,
                updated_at    TEXT NOT NULL
            )
        """)
        # ── Macro News Memory (Accumulated Weekly Headlines) ────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_news_memory (
                headline_hash TEXT PRIMARY KEY,
                source        TEXT NOT NULL,
                title         TEXT NOT NULL,
                summary       TEXT,
                category      TEXT,
                published_at  TEXT NOT NULL,
                ingested_at   TEXT NOT NULL
            )
        """)
        # ── AI Corporate Interlink Fundamentals Cache ───────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interlink_fundamentals_cache (
                ticker           TEXT PRIMARY KEY,
                capex_annual     REAL,
                revenue_annual   REAL,
                inventory_dsi    REAL,
                rpo_backlog      REAL,
                ppa_gw_capacity  REAL,
                node_type        TEXT,
                sector_tier      TEXT,
                metrics_json     TEXT,
                updated_at       TEXT NOT NULL
            )
        """)
        # ── Macro Category Taxonomy & Dynamic Keyword Corpus ───────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_category_corpus (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                category           TEXT NOT NULL,
                keyword            TEXT NOT NULL UNIQUE,
                weight             REAL NOT NULL DEFAULT 1.0,
                directional_bias   TEXT NOT NULL DEFAULT 'BULLISH_CSP',
                default_impact     INTEGER NOT NULL DEFAULT 4,
                default_tickers    TEXT NOT NULL DEFAULT '',
                source             TEXT NOT NULL DEFAULT 'SYSTEM_SEED',
                updated_at         TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_corpus_category ON macro_category_corpus(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_corpus_keyword ON macro_category_corpus(keyword)")
        conn.commit()


# Initialise on import
_init_db()


def save_broker_tokens(
    broker_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    token_type: str = "Bearer",
    expires_at: Optional[str] = None
):
    """Persists broker OAuth access & refresh tokens to SQLite."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO broker_tokens (broker_id, access_token, refresh_token, token_type, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(broker_id) DO UPDATE SET
                access_token=excluded.access_token,
                refresh_token=COALESCE(excluded.refresh_token, broker_tokens.refresh_token),
                token_type=excluded.token_type,
                expires_at=excluded.expires_at,
                updated_at=excluded.updated_at
        """, (broker_id, access_token, refresh_token, token_type, expires_at, now_iso))
        conn.commit()


def get_broker_tokens(broker_id: str = "saxo") -> Optional[Dict[str, Any]]:
    """Retrieves persistent broker tokens from SQLite."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM broker_tokens WHERE broker_id = ?", (broker_id,)).fetchone()
        if row:
            return dict(row)
    return None


def clear_broker_tokens(broker_id: str = "saxo"):
    """Wipes persistent broker tokens from SQLite."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM broker_tokens WHERE broker_id = ?", (broker_id,))
        conn.commit()



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

def list_sessions(backend: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all sessions ordered by last update (newest first), without messages."""
    use_firestore = (backend == "firestore") or (_USE_FIRESTORE and backend != "sqlite")
    if use_firestore and _firestore_client:
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


def create_session(
    title: str, 
    messages: List[Dict[str, Any]], 
    session_id: Optional[str] = None,
    backend: Optional[str] = None
) -> Dict[str, Any]:
    """Persist a new session and return it."""
    if not session_id:
        session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Lightweight learnings generation for fast saving
    if len(messages) >= 4:
        learnings = get_key_learnings(messages)
    else:
        learnings = f"- Session initialized on topic: {title}"

    use_firestore = (backend == "firestore") or (_USE_FIRESTORE and backend != "sqlite")
    if use_firestore and _firestore_client:
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


def get_session(session_id: str, backend: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a full session by ID (including messages)."""
    use_firestore = (backend == "firestore") or (_USE_FIRESTORE and backend != "sqlite")
    if use_firestore and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
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
    messages: List[Dict[str, Any]], 
    title: Optional[str] = None,
    generate_learnings: bool = False,
    backend: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Append / overwrite messages for an existing session."""
    now = datetime.now(timezone.utc).isoformat()
    
    # Only invoke LLM summarization on explicit title updates or when requested
    learnings = None
    if generate_learnings or (title is not None and len(messages) >= 4):
        learnings = get_key_learnings(messages)

    use_firestore = (backend == "firestore") or (_USE_FIRESTORE and backend != "sqlite")
    if use_firestore and _firestore_client:
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


def delete_session(session_id: str, backend: Optional[str] = None) -> bool:
    """Delete a session by ID. Returns True if found and deleted."""
    use_firestore = (backend == "firestore") or (_USE_FIRESTORE and backend != "sqlite")
    if use_firestore and _firestore_client:
        try:
            doc_ref = _firestore_client.collection("tutor_sessions").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.delete()
                # Also delete from SQLite if present
                with _get_conn() as conn:
                    conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
                    conn.commit()
                return True
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
#  SAXO LIVE PERSISTENT CACHE & HISTORICAL VALUATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def set_saxo_cache(key: str, data: Any) -> None:
    """
    Descriptive Summary:
        Stores Saxo broker responses or derived state in SQLite cache (`saxo_cache` table)
        with ISO UTC timestamping. Automatically synchronizes both 'account_summary' and
        'balances' alias keys to permanently prevent runtime lookup mismatch bugs.

    Parameters:
        key (str): The unique cache key identifier (e.g. 'account_summary', 'balances', 'positions').
        data (Any): Arbitrary JSON-serializable payload (dictionary, list, or primitive).

    Returns:
        None.

    Exceptions / Side Effects:
        Catches and logs serialization or database write exceptions without crashing caller.
        Writes to persistent SQLite `saxo_cache` table.

    Usage Example:
        >>> set_saxo_cache('account_summary', {'total_equity': 102192.51, 'cash_available': 71984.46})
        >>> bal = get_saxo_cache('balances')
        >>> print(bal['total_equity'])
        102192.51
    """
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(data)
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO saxo_cache (key, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (key, serialized, now_iso)
            )
            # Automatic key synchronization between account_summary and balances
            if key == "account_summary":
                conn.execute(
                    """
                    INSERT INTO saxo_cache (key, data, updated_at)
                    VALUES ('balances', ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        updated_at = excluded.updated_at
                    """,
                    (serialized, now_iso)
                )
            elif key == "balances":
                conn.execute(
                    """
                    INSERT INTO saxo_cache (key, data, updated_at)
                    VALUES ('account_summary', ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data = excluded.data,
                        updated_at = excluded.updated_at
                    """,
                    (serialized, now_iso)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to write saxo cache for {key}: {e}")

def get_saxo_cache(key: str) -> Optional[Any]:
    """
    Descriptive Summary:
        Retrieves cached broker data from SQLite by key. Features intelligent alias fallback
        between 'balances' and 'account_summary' so callers querying either key receive
        identical verified broker state.

    Parameters:
        key (str): Primary cache key to query (e.g. 'account_summary', 'balances', 'positions').

    Returns:
        Optional[Any]: Deserialized JSON payload if key exists in cache, or None if missing/invalid.

    Exceptions / Side Effects:
        Catches and logs deserialization or database exceptions gracefully. Read-only operation.

    Usage Example:
        >>> cached = get_saxo_cache('account_summary')
        >>> if cached:
        ...     print(cached.get('cash_available'))
        71984.46
    """
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT data FROM saxo_cache WHERE key = ?", (key,)).fetchone()
            if row:
                return json.loads(row["data"])
            
            # Intelligent alias fallback between account_summary and balances
            if key == "balances":
                row_alt = conn.execute("SELECT data FROM saxo_cache WHERE key = 'account_summary'").fetchone()
                if row_alt:
                    return json.loads(row_alt["data"])
            elif key == "account_summary":
                row_alt = conn.execute("SELECT data FROM saxo_cache WHERE key = 'balances'").fetchone()
                if row_alt:
                    return json.loads(row_alt["data"])
    except Exception as e:
        logger.error(f"Failed to read saxo cache for {key}: {e}")
    return None

def clear_saxo_cache() -> None:
    """
    Descriptive Summary:
        Wipes all cached Saxo broker data on user disconnect or manual reset.

    Parameters:
        None.

    Returns:
        None.

    Exceptions / Side Effects:
        Catches and logs deletion errors. Modifies `saxo_cache` table by deleting all rows.

    Usage Example:
        >>> clear_saxo_cache()
    """
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM saxo_cache")
            conn.commit()
            logger.info("Cleared all Saxo cache records from SQLite.")
    except Exception as e:
        logger.error(f"Failed to clear saxo cache: {e}")

def get_latest_saxo_report() -> Optional[Dict[str, Any]]:
    """
    Descriptive Summary:
        Queries SQLite for the most recent authentic historical Saxo bank/broker
        account report statement, extracting verified total account net equity (final_value),
        cash balance, PnL, and reporting period dates.

    Parameters:
        None.

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing authentic report metrics if available,
        or None if no reports have been ingested. Fields include:
            - 'report_id' (str): Unique report identifier (e.g. 'REP-33888_221497-19-Aug-2026').
            - 'account_id' (str): Client account ID.
            - 'client_name' (str): Account holder name.
            - 'from_date' (str): Reporting period start date.
            - 'to_date' (str): Reporting period end date.
            - 'currency' (str): Base currency code (e.g. 'USD').
            - 'total_return_pct' (float): Cumulative return percentage.
            - 'total_pnl' (float): Total profit/loss in dollars.
            - 'initial_value' (float): Opening account value.
            - 'final_value' (float): Closing account net equity.
            - 'net_transfers' (float): Net deposits/withdrawals.
            - 'cash_balance' (float): Authentic cash balance.
            - 'created_at' (str): Ingestion timestamp.

    Exceptions / Side Effects:
        Catches SQLite operational errors (e.g. table not yet initialized) and returns None.

    Usage Example:
        >>> report = get_latest_saxo_report()
        >>> if report:
        ...     print(report['account_id'], report['final_value'], report['cash_balance'])
        33888/221497 102192.51 71984.46
    """
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM saxo_reports ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.debug(f"Could not retrieve latest saxo report from SQLite: {e}")
    return None

def get_portfolio_holdings_valuation() -> Dict[str, Any]:
    """
    Descriptive Summary:
        Computes aggregate market value and unrealized profit/loss across all recorded
        portfolio holdings in SQLite, prioritizing authentic Saxo holdings history
        (`saxo_holdings_history`) and falling back to watched portfolio tickers (`portfolio_tickers`).

    Parameters:
        None.

    Returns:
        Dict[str, Any]: Aggregate valuation dictionary containing:
            - 'total_holdings_value' (float): Market value of open long equities/ETFs in USD.
            - 'total_unrealized_pnl' (float): Net unrealized gain/loss in USD.
            - 'positions_count' (int): Count of distinct positions evaluated.
            - 'valuation_source' (str): 'saxo_holdings_history', 'portfolio_tickers', or 'EMPTY'.
            - 'holdings' (List[Dict[str, Any]]): Array of individual position summaries.

    Exceptions / Side Effects:
        Catches any database read exceptions, logging errors and returning a zeroed structure.

    Usage Example:
        >>> val = get_portfolio_holdings_valuation()
        >>> print(val['total_holdings_value'], val['positions_count'])
        30405.0 5
    """
    try:
        with _get_conn() as conn:
            # Check saxo_holdings_history first
            holdings_rows = conn.execute(
                "SELECT symbol, name, asset_type, qty, open_price, current_price, unrealized_pnl "
                "FROM saxo_holdings_history"
            ).fetchall()
            
            if holdings_rows:
                holdings = []
                total_value = 0.0
                total_pnl = 0.0
                for r in holdings_rows:
                    qty = float(r["qty"] or 0.0)
                    price = float(r["current_price"] or 0.0)
                    pnl = float(r["unrealized_pnl"] or 0.0)
                    # For long stock/ETF positions, value is qty * price
                    if qty > 0:
                        total_value += (qty * price)
                    total_pnl += pnl
                    holdings.append({
                        "symbol": r["symbol"],
                        "name": r["name"],
                        "asset_type": r["asset_type"],
                        "qty": qty,
                        "current_price": price,
                        "unrealized_pnl": pnl,
                        "market_value": round(qty * price, 2) if qty > 0 else 0.0
                    })
                return {
                    "total_holdings_value": round(total_value, 2),
                    "total_unrealized_pnl": round(total_pnl, 2),
                    "positions_count": len(holdings),
                    "valuation_source": "saxo_holdings_history",
                    "holdings": holdings
                }

            # Fallback to portfolio_tickers
            ticker_rows = conn.execute(
                "SELECT symbol, name, current_price, volume FROM portfolio_tickers WHERE current_price > 0"
            ).fetchall()
            if ticker_rows:
                holdings = []
                total_value = 0.0
                for r in ticker_rows:
                    price = float(r["current_price"] or 0.0)
                    # Use standard 100-share options lot unit when volume is institutional share count
                    shares = 100.0
                    pos_val = round(shares * price, 2)
                    total_value += pos_val
                    holdings.append({
                        "symbol": r["symbol"],
                        "name": r["name"],
                        "asset_type": "Stock",
                        "qty": shares,
                        "current_price": price,
                        "unrealized_pnl": 0.0,
                        "market_value": pos_val
                    })
                return {
                    "total_holdings_value": round(total_value, 2),
                    "total_unrealized_pnl": 0.0,
                    "positions_count": len(holdings),
                    "valuation_source": "portfolio_tickers",
                    "holdings": holdings
                }
    except Exception as e:
        logger.error(f"Failed to calculate portfolio holdings valuation: {e}")

    return {
        "total_holdings_value": 0.0,
        "total_unrealized_pnl": 0.0,
        "positions_count": 0,
        "valuation_source": "EMPTY",
        "holdings": []
    }


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


# ═══════════════════════════════════════════════════════════════════════════════
#  MACRO NEWS MEMORY HELPERS (Accumulated Weekly Headlines & Deduplication)
# ═══════════════════════════════════════════════════════════════════════════════

def save_macro_headlines(headlines: List[Dict[str, Any]]) -> int:
    """
    Descriptive Summary:
        Persists a collection of macro financial news headlines into SQLite with SHA-256 deduplication.

    Parameters:
        headlines (List[Dict[str, Any]]): List of headline dictionaries. Each dictionary must contain:
            - 'title' (str): The headline string.
            - 'source' (str, optional): Publication source (e.g. 'Saxo Wire', 'Reuters'). Defaults to 'Saxo Wire'.
            - 'summary' (str, optional): Summary text or snippet. Defaults to ''.
            - 'category' (str, optional): Classification tag ('Monetary', 'Earnings', 'Interlink', 'Liquidity', 'General'). Defaults to 'General'.
            - 'published_at' (str, optional): ISO timestamp of publication. Defaults to current UTC time.

    Returns:
        int: Number of new unique headlines successfully inserted into the database.

    Exceptions / Side Effects:
        Writes new unique records to the 'macro_news_memory' table in optionslab.db.
        Silently skips duplicates matching existing SHA-256 headline hashes.

    Usage Example:
        >>> news_items = [
        ...     {"title": "Fed signals potential rate adjustments as inflation stabilizes", "source": "Saxo Wire", "category": "Monetary"}
        ... ]
        >>> count = save_macro_headlines(news_items)
        >>> print(f"Inserted {count} new headlines")
        Inserted 1 new headlines
    """
    if not headlines:
        return 0

    inserted_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with _get_conn() as conn:
            for item in headlines:
                title = item.get("title", "").strip()
                if not title:
                    continue

                source = item.get("source", "Saxo Wire").strip()
                summary = item.get("summary", "").strip()
                category = item.get("category", "General").strip()
                published_at = item.get("published_at") or now_iso

                # Compute deterministic SHA-256 identifier
                hash_input = f"{source}:{title.lower()}".encode("utf-8")
                headline_hash = hashlib.sha256(hash_input).hexdigest()

                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO macro_news_memory (
                        headline_hash, source, title, summary, category, published_at, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (headline_hash, source, title, summary, category, published_at, now_iso)
                )
                if cursor.rowcount > 0:
                    inserted_count += 1
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save macro headlines: {e}")

    return inserted_count


def get_weekly_macro_headlines(days: int = 7, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Descriptive Summary:
        Retrieves accumulated macro news headlines ingested over a trailing rolling window (default 7 days).

    Parameters:
        days (int, optional): Rolling lookback window in calendar days. Defaults to 7.
        category (str, optional): Optional category filter ('Monetary', 'Earnings', 'Interlink', 'Liquidity'). Defaults to None.

    Returns:
        List[Dict[str, Any]]: List of persisted headline records sorted by published_at DESC. Each dictionary contains:
            - 'headline_hash' (str): SHA-256 identifier.
            - 'source' (str): Publication source.
            - 'title' (str): Headline text.
            - 'summary' (str): Article synopsis.
            - 'category' (str): Macro classification tag.
            - 'published_at' (str): ISO publication timestamp.
            - 'ingested_at' (str): ISO database ingestion timestamp.

    Exceptions / Side Effects:
        Executes a read-only query against 'macro_news_memory' in SQLite.

    Usage Example:
        >>> headlines = get_weekly_macro_headlines(days=5, category="Monetary")
        >>> for item in headlines:
        ...     print(item["published_at"], item["title"])
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        with _get_conn() as conn:
            query = "SELECT * FROM macro_news_memory WHERE published_at >= ?"
            params: List[Any] = [cutoff]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " ORDER BY published_at DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch weekly macro headlines: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  AI CORPORATE INTERLINK FUNDAMENTALS CACHE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def save_interlink_fundamentals(record: Dict[str, Any]) -> None:
    """
    Descriptive Summary:
        Persists or updates balance sheet, CapEx, inventory DSI, and utility capacity fundamentals for an AI Interlink node.

    Parameters:
        record (Dict[str, Any]): Interlink company metrics dictionary containing:
            - 'ticker' (str): Canonical ticker symbol (e.g. 'NVDA', 'TSM', 'NEE'). Required.
            - 'capex_annual' (float, optional): Annualized CapEx in Billions USD. Defaults to 0.0.
            - 'revenue_annual' (float, optional): Annualized Revenue in Billions USD. Defaults to 0.0.
            - 'inventory_dsi' (float, optional): Days Sales of Inventory. Defaults to 0.0.
            - 'rpo_backlog' (float, optional): Remaining Performance Obligation in Billions USD. Defaults to 0.0.
            - 'ppa_gw_capacity' (float, optional): Power Purchase Agreement capacity in Gigawatts. Defaults to 0.0.
            - 'node_type' (str, optional): 'Anchor' or 'Challenger'. Defaults to 'Anchor'.
            - 'sector_tier' (str, optional): 'Silicon', 'Cloud', 'Power', or 'Enterprise'. Defaults to 'Silicon'.
            - 'metrics_json' (dict or str, optional): Extended metrics serialized as JSON string.

    Returns:
        None

    Exceptions / Side Effects:
        Performs an UPSERT into 'interlink_fundamentals_cache' in optionslab.db.

    Usage Example:
        >>> save_interlink_fundamentals({
        ...     "ticker": "NVDA", "capex_annual": 3.8, "revenue_annual": 120.0,
        ...     "inventory_dsi": 72.5, "node_type": "Anchor", "sector_tier": "Silicon"
        ... })
    """
    ticker = record.get("ticker", "").strip().upper()
    if not ticker:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    metrics_json = record.get("metrics_json", "")
    if isinstance(metrics_json, dict):
        metrics_json = json.dumps(metrics_json)

    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO interlink_fundamentals_cache (
                    ticker, capex_annual, revenue_annual, inventory_dsi,
                    rpo_backlog, ppa_gw_capacity, node_type, sector_tier,
                    metrics_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    capex_annual = excluded.capex_annual,
                    revenue_annual = excluded.revenue_annual,
                    inventory_dsi = excluded.inventory_dsi,
                    rpo_backlog = excluded.rpo_backlog,
                    ppa_gw_capacity = excluded.ppa_gw_capacity,
                    node_type = excluded.node_type,
                    sector_tier = excluded.sector_tier,
                    metrics_json = excluded.metrics_json,
                    updated_at = excluded.updated_at
                """,
                (
                    ticker,
                    record.get("capex_annual", 0.0),
                    record.get("revenue_annual", 0.0),
                    record.get("inventory_dsi", 0.0),
                    record.get("rpo_backlog", 0.0),
                    record.get("ppa_gw_capacity", 0.0),
                    record.get("node_type", "Anchor"),
                    record.get("sector_tier", "Silicon"),
                    metrics_json,
                    now_iso,
                )
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save interlink fundamentals for {ticker}: {e}")


def get_interlink_fundamentals(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Descriptive Summary:
        Retrieves cached balance sheet and operational interlink metrics for a specific corporate ticker.

    Parameters:
        ticker (str): Canonical stock symbol (e.g., 'MSFT', 'NEE', 'GE').

    Returns:
        Optional[Dict[str, Any]]: Cached record dictionary if found, else None. Contains:
            - 'ticker' (str): Canonical symbol.
            - 'capex_annual' (float): Annual CapEx in $B.
            - 'revenue_annual' (float): Annual Revenue in $B.
            - 'inventory_dsi' (float): Days Sales of Inventory.
            - 'rpo_backlog' (float): RPO Backlog in $B.
            - 'ppa_gw_capacity' (float): Gigawatts power contracted.
            - 'node_type' (str): 'Anchor' or 'Challenger'.
            - 'sector_tier' (str): Industry segment.
            - 'metrics_json' (str): Serialized extended metrics.
            - 'updated_at' (str): Timestamp of last refresh.

    Exceptions / Side Effects:
        Performs a SELECT query on 'interlink_fundamentals_cache' in SQLite.

    Usage Example:
        >>> metrics = get_interlink_fundamentals("MSFT")
        >>> if metrics:
        ...     print(metrics["capex_annual"], metrics["rpo_backlog"])
    """
    clean_ticker = ticker.strip().upper()
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM interlink_fundamentals_cache WHERE ticker = ?",
                (clean_ticker,)
            ).fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"Failed to get interlink fundamentals for {ticker}: {e}")
    return None


def list_all_interlink_fundamentals() -> List[Dict[str, Any]]:
    """
    Descriptive Summary:
        Lists all cached corporate interlink nodes across Silicon, Cloud, Power, and Enterprise AI tiers.

    Parameters:
        None

    Returns:
        List[Dict[str, Any]]: List of all stored node metric dictionaries ordered by sector_tier, ticker ASC.

    Exceptions / Side Effects:
        Executes a SELECT query on 'interlink_fundamentals_cache' in SQLite.

    Usage Example:
        >>> nodes = list_all_interlink_fundamentals()
        >>> print(f"Loaded {len(nodes)} interlink nodes")
    """
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM interlink_fundamentals_cache ORDER BY sector_tier, ticker ASC"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to list all interlink fundamentals: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  MACRO CATEGORY TAXONOMY & DYNAMIC KEYWORD CORPUS
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_MACRO_TAXONOMY_SEEDS = [
    # ── AI Semiconductors & Compute Infrastructure ───────────────────────────
    {"category": "AI_SEMICONDUCTORS", "keyword": "ai", "weight": 1.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,PLTR,TSM,AMD,AVGO"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "compute", "weight": 1.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,PLTR,TSM,AMD,AVGO"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "nvidia", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,TSM"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "gpu", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,AMD"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "palantir", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "PLTR"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "semiconductor", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "TSM,AMD,AVGO,NVDA"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "blackwell", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,TSM"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "hbm", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "MU,TSM,NVDA"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "asic", "weight": 1.4, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "AVGO,MRVL"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "datacenter", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,MSFT,AMZN"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "accelerator", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "NVDA,AMD,GOOGL"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "agent", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,PLTR,MSFT,GOOGL"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "agentic", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,PLTR,MSFT"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "agentic platform", "weight": 2.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "PLTR,MSFT,NVDA"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "agentic app development", "weight": 3.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "PLTR,MSFT,GOOGL"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "autonomous agent", "weight": 2.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "PLTR,MSFT,NVDA"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "multi-agent", "weight": 2.5, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "MSFT,GOOGL,PLTR"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "reasoning models", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,MSFT,GOOGL"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "llm inference", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,AVGO,AMD"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "foundation model", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "MSFT,GOOGL,META"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "sovereign ai", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NVDA,TSM"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "chips", "weight": 1.0, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "TSM,NVDA,INTC"},
    {"category": "AI_SEMICONDUCTORS", "keyword": "wafer", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "TSM,ASML"},

    # ── Fed Rates, Inflation & Macro Monetary Policy ─────────────────────────
    {"category": "FED_RATES_INFLATION", "keyword": "fed", "weight": 1.0, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 5, "default_tickers": "TLT,QQQ,SPY,BAC"},
    {"category": "FED_RATES_INFLATION", "keyword": "rate cut", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "QQQ,SPY,TLT"},
    {"category": "FED_RATES_INFLATION", "keyword": "rate hike", "weight": 1.8, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "TLT,QQQ,BAC"},
    {"category": "FED_RATES_INFLATION", "keyword": "powell", "weight": 1.5, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 5, "default_tickers": "QQQ,SPY,TLT"},
    {"category": "FED_RATES_INFLATION", "keyword": "inflation", "weight": 1.2, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "TLT,SPY"},
    {"category": "FED_RATES_INFLATION", "keyword": "cpi", "weight": 1.5, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 5, "default_tickers": "SPY,QQQ,TLT"},
    {"category": "FED_RATES_INFLATION", "keyword": "fomc", "weight": 1.8, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 5, "default_tickers": "SPY,QQQ,TLT"},
    {"category": "FED_RATES_INFLATION", "keyword": "yield", "weight": 1.0, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "TLT,BAC"},
    {"category": "FED_RATES_INFLATION", "keyword": "treasury", "weight": 1.2, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "TLT,IEF"},
    {"category": "FED_RATES_INFLATION", "keyword": "interest rates", "weight": 1.5, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "TLT,QQQ,SPY"},
    {"category": "FED_RATES_INFLATION", "keyword": "basis points", "weight": 1.5, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "TLT,QQQ"},
    {"category": "FED_RATES_INFLATION", "keyword": "quantitative tightening", "weight": 2.0, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "SPY,TLT"},

    # ── Enterprise Software & Cloud Hyperscalers ─────────────────────────────
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "enterprise software", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "MSFT,CRM,NOW"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "cloud", "weight": 1.0, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "MSFT,AMZN,GOOGL"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "saas", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "CRM,NOW,SNOW"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "hyperscaler", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "MSFT,AMZN,GOOGL,META"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "azure", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "MSFT"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "aws", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "AMZN"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "google cloud", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "GOOGL"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "crm", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "CRM"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "cybersecurity", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "CRWD,PANW"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "cloud spending", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "MSFT,AMZN,GOOGL"},
    {"category": "ENTERPRISE_SOFTWARE_CLOUD", "keyword": "software revenue", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "MSFT,PLTR,CRM"},

    # ── Energy, Nuclear Power & Datacenter Infrastructure ─────────────────────
    {"category": "ENERGY_POWER_INFRA", "keyword": "nuclear", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "CEG,VST,CCJ"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "smr", "weight": 2.0, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "SMR,OKLO,CEG"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "power grid", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "NEE,GEV,ETN"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "clean energy", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "NEE,FSLR"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "electricity demand", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "NEE,CEG,VST"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "datacenter power", "weight": 2.2, "directional_bias": "BULLISH_CSP", "default_impact": 5, "default_tickers": "NEE,CEG,GEV,ETN"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "utility", "weight": 1.2, "directional_bias": "BULLISH_CSP", "default_impact": 3, "default_tickers": "NEE,DUK,SO"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "geothermal", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 3, "default_tickers": "ORMAT,NEE"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "substation", "weight": 1.5, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "ETN,GEV"},
    {"category": "ENERGY_POWER_INFRA", "keyword": "transmission line", "weight": 1.8, "directional_bias": "BULLISH_CSP", "default_impact": 4, "default_tickers": "NEE,PWR"},

    # ── Consumer Spending, Retail & Employment ───────────────────────────────
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "retail sales", "weight": 1.8, "directional_bias": "HEDGED_PUT", "default_impact": 3, "default_tickers": "WMT,COST,AMZN,TGT"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "consumer spending", "weight": 1.8, "directional_bias": "HEDGED_PUT", "default_impact": 3, "default_tickers": "AMZN,COST,HD"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "unemployment", "weight": 1.5, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "SPY,QQQ"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "payrolls", "weight": 1.8, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "SPY,QQQ"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "jobs report", "weight": 1.8, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 4, "default_tickers": "SPY,QQQ,TLT"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "credit card debt", "weight": 1.8, "directional_bias": "HEDGED_PUT", "default_impact": 3, "default_tickers": "COF,DFS,BAC,JPM"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "consumer confidence", "weight": 1.5, "directional_bias": "NEUTRAL_CALENDAR", "default_impact": 3, "default_tickers": "XLY,XLP,SPY"},
    {"category": "CONSUMER_EMPLOYMENT_RETAIL", "keyword": "discretionary spending", "weight": 1.8, "directional_bias": "HEDGED_PUT", "default_impact": 3, "default_tickers": "NKE,SBUX,HD"},

    # ── Geopolitics & Global Trade Restrictions ──────────────────────────────
    {"category": "GEOPOLITICS_TRADE", "keyword": "tariff", "weight": 1.8, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "TSM,AAPL,NVDA"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "trade war", "weight": 2.0, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "SPY,TSM,AAPL"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "sanctions", "weight": 1.5, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "XOM,CVX,NVDA"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "export controls", "weight": 2.0, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "ASML,NVDA,KLAC"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "taiwan strait", "weight": 2.2, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "TSM,NVDA,AAPL"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "geopolitics", "weight": 1.2, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "SPY,GLD,USO"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "chip ban", "weight": 2.0, "directional_bias": "DEFENSIVE_CC", "default_impact": 5, "default_tickers": "NVDA,TSM,ASML"},
    {"category": "GEOPOLITICS_TRADE", "keyword": "supply chain restriction", "weight": 2.0, "directional_bias": "DEFENSIVE_CC", "default_impact": 4, "default_tickers": "AAPL,TSM,NVDA"}
]


def init_macro_category_corpus() -> int:
    """
    Descriptive Summary:
        Seeds the SQLite macro_category_corpus table with institutional category taxonomy,
        directional biases, impact weights, and thematic keywords if empty.

    Parameters:
        None

    Returns:
        int: Number of default corpus keywords successfully seeded into SQLite.

    Exceptions / Side Effects:
        Executes INSERT OR IGNORE operations on 'macro_category_corpus' table.
        Safe for concurrent executions; commits changes immediately.

    Usage Example:
        >>> count = init_macro_category_corpus()
        >>> print(f"Corpus initialized with {count} seed keywords")
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    seeded = 0
    try:
        with _get_conn() as conn:
            # Check if already seeded
            count = conn.execute("SELECT COUNT(*) FROM macro_category_corpus").fetchone()[0]
            if count > 0:
                logger.info(f"macro_category_corpus already populated with {count} keywords.")
                return count

            for item in DEFAULT_MACRO_TAXONOMY_SEEDS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO macro_category_corpus (
                        category, keyword, weight, directional_bias,
                        default_impact, default_tickers, source, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["category"],
                        item["keyword"].strip().lower(),
                        item.get("weight", 1.0),
                        item.get("directional_bias", "BULLISH_CSP"),
                        item.get("default_impact", 4),
                        item.get("default_tickers", ""),
                        "SYSTEM_SEED",
                        now_iso,
                    )
                )
                seeded += 1
            conn.commit()
            logger.info(f"Initialized macro_category_corpus with {seeded} seed keywords.")
            return seeded
    except Exception as e:
        logger.error(f"Failed to initialize macro_category_corpus: {e}")
        return 0


def get_macro_category_corpus(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Descriptive Summary:
        Retrieves active macro classification keywords, weights, and execution biases
        from SQLite, optionally filtered by a specific category taxonomy.

    Parameters:
        category (Optional[str]): Optional category filter (e.g., 'AI_SEMICONDUCTORS').
            Defaults to None to return all registered keywords across all categories.

    Returns:
        List[Dict[str, Any]]: List of keyword dictionary records containing:
            - 'id' (int): Primary key identifier.
            - 'category' (str): Macro category taxonomy key.
            - 'keyword' (str): Normalized lower-case matching string or phrase.
            - 'weight' (float): Matching importance multiplier (e.g., 1.0 to 3.0).
            - 'directional_bias' (str): Strategy bias ('BULLISH_CSP', 'DEFENSIVE_CC', etc.).
            - 'default_impact' (int): Event volatility impact scale (1-5).
            - 'default_tickers' (str): Comma-separated associated underlying tickers.
            - 'source' (str): Keyword origin ('SYSTEM_SEED', 'DYNAMIC_DISCOVERY', 'MANUAL').
            - 'updated_at' (str): ISO-8601 UTC timestamp of last modification.

    Exceptions / Side Effects:
        Performs SELECT query on 'macro_category_corpus' table.

    Usage Example:
        >>> corpus = get_macro_category_corpus("AI_SEMICONDUCTORS")
        >>> for item in corpus:
        ...     print(item["keyword"], item["weight"])
    """
    try:
        with _get_conn() as conn:
            if category:
                rows = conn.execute(
                    """
                    SELECT * FROM macro_category_corpus
                    WHERE category = ?
                    ORDER BY weight DESC, keyword ASC
                    """,
                    (category.strip().upper(),)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM macro_category_corpus
                    ORDER BY category ASC, weight DESC, keyword ASC
                    """
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to retrieve macro_category_corpus: {e}")
        return []


def add_or_update_corpus_keyword(
    category: str,
    keyword: str,
    weight: float = 1.0,
    directional_bias: str = "BULLISH_CSP",
    default_impact: int = 4,
    default_tickers: str = "",
    source: str = "MANUAL"
) -> Dict[str, Any]:
    """
    Descriptive Summary:
        Creates a new keyword entry or updates an existing entry in the SQLite
        macro_category_corpus table, enabling dynamic vocabulary expansion.

    Parameters:
        category (str): Macro category identifier (e.g., 'AI_SEMICONDUCTORS').
        keyword (str): Search string or phrase to match (auto-normalized to lowercase).
        weight (float): Salience score multiplier for classification (default: 1.0).
        directional_bias (str): Quantitative options bias (default: 'BULLISH_CSP').
        default_impact (int): Market volatility impact rating (1 to 5, default: 4).
        default_tickers (str): Comma-delimited list of primary ticker beneficiaries.
        source (str): Origin marker ('MANUAL', 'SYSTEM_SEED', 'DYNAMIC_DISCOVERY').

    Returns:
        Dict[str, Any]: The upserted keyword record dictionary from SQLite.

    Exceptions / Side Effects:
        Executes INSERT ON CONFLICT DO UPDATE on 'macro_category_corpus' table.

    Usage Example:
        >>> record = add_or_update_corpus_keyword(
        ...     category="AI_SEMICONDUCTORS",
        ...     keyword="agentic app development",
        ...     weight=3.0,
        ...     directional_bias="BULLISH_CSP",
        ...     default_tickers="NVDA,PLTR,MSFT"
        ... )
        >>> print(record["id"], record["keyword"])
    """
    clean_cat = category.strip().upper()
    clean_kw = keyword.strip().lower()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO macro_category_corpus (
                    category, keyword, weight, directional_bias,
                    default_impact, default_tickers, source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    category = excluded.category,
                    weight = excluded.weight,
                    directional_bias = excluded.directional_bias,
                    default_impact = excluded.default_impact,
                    default_tickers = excluded.default_tickers,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    clean_cat,
                    clean_kw,
                    float(weight),
                    directional_bias.strip(),
                    int(default_impact),
                    default_tickers.strip(),
                    source.strip(),
                    now_iso
                )
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM macro_category_corpus WHERE keyword = ?",
                (clean_kw,)
            ).fetchone()
            return dict(row) if row else {}
    except Exception as e:
        logger.error(f"Failed to upsert corpus keyword '{clean_kw}': {e}")
        return {}


def delete_corpus_keyword(keyword: str) -> bool:
    """
    Descriptive Summary:
        Removes a keyword from the SQLite macro_category_corpus table by its exact string match.

    Parameters:
        keyword (str): The keyword or phrase to delete (case-insensitive).

    Returns:
        bool: True if a record was found and deleted; False if keyword did not exist.

    Exceptions / Side Effects:
        Executes DELETE FROM macro_category_corpus in SQLite and commits transaction.

    Usage Example:
        >>> deleted = delete_corpus_keyword("obsolete keyword")
        >>> print(f"Deleted: {deleted}")
    """
    clean_kw = keyword.strip().lower()
    try:
        with _get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM macro_category_corpus WHERE keyword = ?",
                (clean_kw,)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to delete corpus keyword '{clean_kw}': {e}")
        return False


def bulk_upsert_corpus_keywords(records: List[Dict[str, Any]]) -> int:
    """
    Descriptive Summary:
        Performs high-throughput bulk insertion and updates of novel or updated
        vocabulary records into the SQLite macro_category_corpus table.

    Parameters:
        records (List[Dict[str, Any]]): List of dictionaries, each containing:
            - 'category' (str): Taxonomy category.
            - 'keyword' (str): Matching token or n-gram.
            - Optional keys: 'weight', 'directional_bias', 'default_impact', 'default_tickers', 'source'.

    Returns:
        int: Total number of records successfully written or updated.

    Exceptions / Side Effects:
        Executes executemany transaction on SQLite database.

    Usage Example:
        >>> items = [
        ...     {"category": "AI_SEMICONDUCTORS", "keyword": "agentic platform", "weight": 2.5},
        ...     {"category": "AI_SEMICONDUCTORS", "keyword": "reasoning models", "weight": 2.0}
        ... ]
        >>> count = bulk_upsert_corpus_keywords(items)
        >>> print(f"Upserted {count} items")
    """
    if not records:
        return 0
    now_iso = datetime.now(timezone.utc).isoformat()
    count = 0
    try:
        with _get_conn() as conn:
            for item in records:
                cat = item.get("category", "AI_SEMICONDUCTORS").strip().upper()
                kw = item.get("keyword", "").strip().lower()
                if not kw:
                    continue
                weight = float(item.get("weight", 1.0))
                bias = item.get("directional_bias", "BULLISH_CSP").strip()
                impact = int(item.get("default_impact", 4))
                tickers = item.get("default_tickers", "").strip()
                source = item.get("source", "DYNAMIC_DISCOVERY").strip()

                conn.execute(
                    """
                    INSERT INTO macro_category_corpus (
                        category, keyword, weight, directional_bias,
                        default_impact, default_tickers, source, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(keyword) DO UPDATE SET
                        category = excluded.category,
                        weight = excluded.weight,
                        directional_bias = excluded.directional_bias,
                        default_impact = excluded.default_impact,
                        default_tickers = excluded.default_tickers,
                        source = excluded.source,
                        updated_at = excluded.updated_at
                    """,
                    (cat, kw, weight, bias, impact, tickers, source, now_iso)
                )
                count += 1
            conn.commit()
            return count
    except Exception as e:
        logger.error(f"Failed to bulk upsert corpus keywords: {e}")
        return count


# Auto-seed corpus on module load if empty
try:
    init_macro_category_corpus()
except Exception as e:
    logger.warning(f"Could not auto-seed macro_category_corpus on import: {e}")




