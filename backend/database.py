"""
Datenbankschicht: SQLite lokal, PostgreSQL auf Render (via DATABASE_URL).
Umgebungserkennung automatisch — kein Code-Wechsel nötig.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from config import DATABASE_PATH, STARTING_CAPITAL_CHF

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


# ── Verbindung ────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _q(sql: str) -> str:
    """Ersetzt ? durch %s für PostgreSQL."""
    return sql.replace("?", "%s") if USE_POSTGRES else sql


@contextmanager
def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _fetchall(conn, sql: str, params=()) -> list[dict]:
    cur = conn.cursor()
    cur.execute(_q(sql), params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def _fetchone(conn, sql: str, params=()) -> Optional[dict]:
    cur = conn.cursor()
    cur.execute(_q(sql), params)
    row = cur.fetchone()
    return dict(row) if row else None


def _execute(conn, sql: str, params=()) -> int:
    """Führt Statement aus und gibt lastrowid/id zurück."""
    cur = conn.cursor()
    if USE_POSTGRES:
        # RETURNING id anhängen wenn INSERT
        if sql.strip().upper().startswith("INSERT") and "RETURNING" not in sql.upper():
            sql = _q(sql) + " RETURNING id"
            cur.execute(sql, params)
            row = cur.fetchone()
            return row["id"] if row else 0
        cur.execute(_q(sql), params)
        return 0
    else:
        cur.execute(sql, params)
        return cur.lastrowid or 0


def _execute_many(conn, sql: str, rows):
    cur = conn.cursor()
    cur.executemany(_q(sql), rows)


# ── Schema ────────────────────────────────────────────────────────────────────

_SERIAL = "SERIAL" if USE_POSTGRES else "INTEGER"
_AUTOINC = "" if USE_POSTGRES else "AUTOINCREMENT"

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS portfolio (
    id {_SERIAL} PRIMARY KEY,
    cash_chf REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    id {_SERIAL} PRIMARY KEY {_AUTOINC},
    symbol TEXT NOT NULL UNIQUE,
    asset_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_buy_price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    opened_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id {_SERIAL} PRIMARY KEY {_AUTOINC},
    symbol TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    quantity REAL NOT NULL,
    price_usd REAL NOT NULL,
    price_chf REAL NOT NULL,
    total_chf REAL NOT NULL,
    pnl_chf REAL,
    agent_signals TEXT,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id {_SERIAL} PRIMARY KEY {_AUTOINC},
    symbol TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    orchestrator_action TEXT,
    orchestrator_confidence REAL,
    orchestrator_reasoning TEXT,
    orchestrator_score REAL,
    macro_signal TEXT,
    technical_signal TEXT,
    fundamental_signal TEXT,
    crypto_signal TEXT,
    risk_signal TEXT,
    sentiment_signal TEXT,
    analyzed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id {_SERIAL} PRIMARY KEY {_AUTOINC},
    date TEXT NOT NULL,
    sp500_price REAL,
    btc_usd_price REAL,
    portfolio_value_chf REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS screener_results (
    id {_SERIAL} PRIMARY KEY {_AUTOINC},
    run_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    score REAL NOT NULL,
    direction TEXT NOT NULL,
    reason TEXT,
    price REAL,
    was_analyzed INTEGER DEFAULT 0
);
"""


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        for stmt in _SCHEMA.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)

        # Migrationen — PostgreSQL: IF NOT EXISTS verhindert Transaktionsabbruch
        if USE_POSTGRES:
            migrations = [
                "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sentiment_signal TEXT",
            ]
        else:
            migrations = [
                "ALTER TABLE analyses ADD COLUMN sentiment_signal TEXT",
            ]
        for migration in migrations:
            try:
                cur.execute(migration)
            except Exception:
                pass

        # Startkapital einmalig setzen
        row = _fetchone(conn, "SELECT id FROM portfolio WHERE id = 1")
        if not row:
            _execute(
                conn,
                "INSERT INTO portfolio (id, cash_chf, updated_at) VALUES (?, ?, ?)",
                (1, STARTING_CAPITAL_CHF, _now()),
            )


# ── Portfolio ─────────────────────────────────────────────────────────────────

def get_portfolio(conn) -> dict:
    return _fetchone(conn, "SELECT * FROM portfolio WHERE id = 1")


def update_cash(conn, new_cash: float):
    _execute(
        conn,
        "UPDATE portfolio SET cash_chf = ?, updated_at = ? WHERE id = 1",
        (round(new_cash, 4), _now()),
    )


# ── Positions ─────────────────────────────────────────────────────────────────

def get_positions(conn) -> list[dict]:
    return _fetchall(conn, "SELECT * FROM positions ORDER BY opened_at DESC")


def get_position(conn, symbol: str) -> Optional[dict]:
    return _fetchone(conn, "SELECT * FROM positions WHERE symbol = ?", (symbol,))


def upsert_position(conn, symbol: str, asset_type: str,
                    quantity: float, avg_price: float, currency: str = "USD"):
    existing = get_position(conn, symbol)
    if existing:
        new_qty = existing["quantity"] + quantity
        new_avg = (existing["avg_buy_price"] * existing["quantity"] + avg_price * quantity) / new_qty
        _execute(
            conn,
            "UPDATE positions SET quantity = ?, avg_buy_price = ? WHERE symbol = ?",
            (round(new_qty, 8), round(new_avg, 6), symbol),
        )
    else:
        _execute(
            conn,
            "INSERT INTO positions (symbol, asset_type, quantity, avg_buy_price, currency, opened_at) VALUES (?,?,?,?,?,?)",
            (symbol, asset_type, round(quantity, 8), round(avg_price, 6), currency, _now()),
        )


def reduce_or_close_position(conn, symbol: str, quantity: float) -> bool:
    existing = get_position(conn, symbol)
    if not existing:
        return False
    new_qty = existing["quantity"] - quantity
    if new_qty <= 1e-8:
        _execute(conn, "DELETE FROM positions WHERE symbol = ?", (symbol,))
    else:
        _execute(conn, "UPDATE positions SET quantity = ? WHERE symbol = ?",
                 (round(new_qty, 8), symbol))
    return True


# ── Trades ────────────────────────────────────────────────────────────────────

def insert_trade(conn, symbol: str, asset_type: str, direction: str,
                 quantity: float, price_usd: float, price_chf: float,
                 total_chf: float, pnl_chf: Optional[float],
                 agent_signals: Optional[dict]) -> int:
    return _execute(
        conn,
        """INSERT INTO trades
           (symbol, asset_type, direction, quantity, price_usd, price_chf,
            total_chf, pnl_chf, agent_signals, executed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (symbol, asset_type, direction, round(quantity, 8),
         round(price_usd, 6), round(price_chf, 6), round(total_chf, 4),
         round(pnl_chf, 4) if pnl_chf is not None else None,
         json.dumps(agent_signals) if agent_signals else None,
         _now()),
    )


def get_trades(conn, limit: int = 100) -> list[dict]:
    rows = _fetchall(conn, "SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?", (limit,))
    for r in rows:
        if r.get("agent_signals"):
            if isinstance(r["agent_signals"], str):
                r["agent_signals"] = json.loads(r["agent_signals"])
    return rows


# ── Analyses ──────────────────────────────────────────────────────────────────

def insert_analysis(conn, symbol: str, asset_type: str,
                    orchestrator: dict, signals: dict) -> int:
    return _execute(
        conn,
        """INSERT INTO analyses
           (symbol, asset_type, orchestrator_action, orchestrator_confidence,
            orchestrator_reasoning, orchestrator_score,
            macro_signal, technical_signal, fundamental_signal,
            crypto_signal, risk_signal, sentiment_signal, analyzed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (symbol, asset_type,
         orchestrator.get("action"), orchestrator.get("confidence"),
         orchestrator.get("reasoning"), orchestrator.get("weighted_score"),
         json.dumps(signals.get("macro")),
         json.dumps(signals.get("technical")),
         json.dumps(signals.get("fundamental")),
         json.dumps(signals.get("crypto")),
         json.dumps(signals.get("risk")),
         json.dumps(signals.get("sentiment")),
         _now()),
    )


def _parse_analysis_signals(d: dict) -> dict:
    for key in ("macro_signal", "technical_signal", "fundamental_signal",
                "crypto_signal", "risk_signal", "sentiment_signal"):
        if d.get(key) and isinstance(d[key], str):
            d[key] = json.loads(d[key])
    return d


def get_analyses(conn, limit: int = 50) -> list[dict]:
    rows = _fetchall(conn, "SELECT * FROM analyses ORDER BY analyzed_at DESC LIMIT ?", (limit,))
    return [_parse_analysis_signals(r) for r in rows]


def get_latest_analysis(conn, symbol: str) -> Optional[dict]:
    row = _fetchone(
        conn,
        "SELECT * FROM analyses WHERE symbol = ? ORDER BY analyzed_at DESC LIMIT 1",
        (symbol,),
    )
    return _parse_analysis_signals(row) if row else None


# ── Benchmarks ────────────────────────────────────────────────────────────────

def insert_benchmark(conn, date: str, sp500: Optional[float],
                     btc: Optional[float], portfolio_chf: float):
    _execute(
        conn,
        "INSERT INTO benchmarks (date, sp500_price, btc_usd_price, portfolio_value_chf) VALUES (?,?,?,?)",
        (date, sp500, btc, round(portfolio_chf, 4)),
    )


def get_benchmarks(conn, days: int = 180) -> list[dict]:
    rows = _fetchall(conn, "SELECT * FROM benchmarks ORDER BY date DESC LIMIT ?", (days,))
    return list(reversed(rows))


# ── Screener ──────────────────────────────────────────────────────────────────

def insert_screener_results(conn, run_at: str, results: list[dict]):
    _execute(conn, "DELETE FROM screener_results", ())
    _execute_many(
        conn,
        "INSERT INTO screener_results (run_at, symbol, score, direction, reason, price) VALUES (?,?,?,?,?,?)",
        [(run_at, r["symbol"], r["score"], r["direction"], r["reason"], r.get("price")) for r in results],
    )


def get_screener_results(conn) -> list[dict]:
    return _fetchall(conn, "SELECT * FROM screener_results ORDER BY ABS(score) DESC")


def mark_screener_analyzed(conn, symbol: str):
    _execute(conn, "UPDATE screener_results SET was_analyzed = 1 WHERE symbol = ?", (symbol,))
