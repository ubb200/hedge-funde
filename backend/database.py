import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional
from config import DATABASE_PATH, STARTING_CAPITAL_CHF


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY,
                cash_chf REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                asset_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_buy_price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                opened_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sp500_price REAL,
                btc_usd_price REAL,
                portfolio_value_chf REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS screener_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                score REAL NOT NULL,
                direction TEXT NOT NULL,
                reason TEXT,
                price REAL,
                was_analyzed INTEGER DEFAULT 0
            );
        """)

        # Migrationen — neue Spalten sicher hinzufügen
        for migration in [
            "ALTER TABLE analyses ADD COLUMN sentiment_signal TEXT",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass  # Spalte existiert bereits

        row = conn.execute("SELECT id FROM portfolio WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO portfolio (id, cash_chf, updated_at) VALUES (1, ?, ?)",
                (STARTING_CAPITAL_CHF, _now()),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Portfolio ---

def get_portfolio(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT * FROM portfolio WHERE id = 1").fetchone()
    return dict(row)


def update_cash(conn: sqlite3.Connection, new_cash: float):
    conn.execute(
        "UPDATE portfolio SET cash_chf = ?, updated_at = ? WHERE id = 1",
        (round(new_cash, 4), _now()),
    )


# --- Positions ---

def get_positions(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM positions ORDER BY opened_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_position(conn: sqlite3.Connection, symbol: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM positions WHERE symbol = ?", (symbol,)).fetchone()
    return dict(row) if row else None


def upsert_position(conn: sqlite3.Connection, symbol: str, asset_type: str,
                    quantity: float, avg_price: float, currency: str = "USD"):
    existing = get_position(conn, symbol)
    if existing:
        new_qty = existing["quantity"] + quantity
        new_avg = (existing["avg_buy_price"] * existing["quantity"] + avg_price * quantity) / new_qty
        conn.execute(
            "UPDATE positions SET quantity = ?, avg_buy_price = ? WHERE symbol = ?",
            (round(new_qty, 8), round(new_avg, 6), symbol),
        )
    else:
        conn.execute(
            "INSERT INTO positions (symbol, asset_type, quantity, avg_buy_price, currency, opened_at) VALUES (?,?,?,?,?,?)",
            (symbol, asset_type, round(quantity, 8), round(avg_price, 6), currency, _now()),
        )


def reduce_or_close_position(conn: sqlite3.Connection, symbol: str, quantity: float) -> bool:
    existing = get_position(conn, symbol)
    if not existing:
        return False
    new_qty = existing["quantity"] - quantity
    if new_qty <= 1e-8:
        conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
    else:
        conn.execute(
            "UPDATE positions SET quantity = ? WHERE symbol = ?",
            (round(new_qty, 8), symbol),
        )
    return True


# --- Trades ---

def insert_trade(conn: sqlite3.Connection, symbol: str, asset_type: str,
                 direction: str, quantity: float, price_usd: float,
                 price_chf: float, total_chf: float,
                 pnl_chf: Optional[float], agent_signals: Optional[dict]) -> int:
    cur = conn.execute(
        """INSERT INTO trades
           (symbol, asset_type, direction, quantity, price_usd, price_chf, total_chf, pnl_chf, agent_signals, executed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (symbol, asset_type, direction, round(quantity, 8),
         round(price_usd, 6), round(price_chf, 6), round(total_chf, 4),
         round(pnl_chf, 4) if pnl_chf is not None else None,
         json.dumps(agent_signals) if agent_signals else None,
         _now()),
    )
    return cur.lastrowid


def get_trades(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?", (limit,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("agent_signals"):
            d["agent_signals"] = json.loads(d["agent_signals"])
        result.append(d)
    return result


# --- Analyses ---

def insert_analysis(conn: sqlite3.Connection, symbol: str, asset_type: str,
                    orchestrator: dict, signals: dict) -> int:
    cur = conn.execute(
        """INSERT INTO analyses
           (symbol, asset_type, orchestrator_action, orchestrator_confidence,
            orchestrator_reasoning, orchestrator_score,
            macro_signal, technical_signal, fundamental_signal, crypto_signal, risk_signal, sentiment_signal, analyzed_at)
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
    return cur.lastrowid


def get_analyses(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM analyses ORDER BY analyzed_at DESC LIMIT ?", (limit,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for key in ("macro_signal", "technical_signal", "fundamental_signal", "crypto_signal", "risk_signal", "sentiment_signal"):
            if d.get(key):
                d[key] = json.loads(d[key])
        result.append(d)
    return result


def get_latest_analysis(conn: sqlite3.Connection, symbol: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM analyses WHERE symbol = ? ORDER BY analyzed_at DESC LIMIT 1", (symbol,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    for key in ("macro_signal", "technical_signal", "fundamental_signal", "crypto_signal", "risk_signal", "sentiment_signal"):
        if d.get(key):
            d[key] = json.loads(d[key])
    return d


# --- Benchmarks ---

def insert_benchmark(conn: sqlite3.Connection, date: str, sp500: Optional[float],
                     btc: Optional[float], portfolio_chf: float):
    conn.execute(
        "INSERT INTO benchmarks (date, sp500_price, btc_usd_price, portfolio_value_chf) VALUES (?,?,?,?)",
        (date, sp500, btc, round(portfolio_chf, 4)),
    )


def get_benchmarks(conn: sqlite3.Connection, days: int = 180) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM benchmarks ORDER BY date DESC LIMIT ?", (days,)
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


# --- Screener ---

def insert_screener_results(conn: sqlite3.Connection, run_at: str, results: list[dict]):
    conn.execute("DELETE FROM screener_results")
    conn.executemany(
        """INSERT INTO screener_results (run_at, symbol, score, direction, reason, price)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(run_at, r["symbol"], r["score"], r["direction"], r["reason"], r.get("price")) for r in results],
    )


def get_screener_results(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM screener_results ORDER BY ABS(score) DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def mark_screener_analyzed(conn: sqlite3.Connection, symbol: str):
    conn.execute(
        "UPDATE screener_results SET was_analyzed = 1 WHERE symbol = ?", (symbol,)
    )
