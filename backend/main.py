import asyncio
import json
import logging
import math
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from datetime import datetime, timezone

from database import (
    get_conn, init_db, get_analyses, get_trades, get_benchmarks,
    insert_analysis, get_latest_analysis,
    insert_screener_results, get_screener_results,
)
from orchestrator import run_analysis
from paper_trading import (
    get_portfolio_with_value, execute_buy, execute_sell,
    execute_from_analysis, InsufficientCashError, NoPositionError,
)
from scheduler import run_daily_analysis, start_scheduler, stop_scheduler
from screener import run_screener
from config import WATCHLIST_PATH
import kraken_client
import telegram_commander

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


_db_ready = False
_db_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_ready, _db_error
    try:
        init_db()
        _db_ready = True
        logger.info("Datenbank initialisiert")
    except Exception as exc:
        _db_error = f"{type(exc).__name__}: {exc}"
        logger.error(f"Datenbank-Initialisierung fehlgeschlagen: {exc}", exc_info=True)
    start_scheduler()
    telegram_commander.start()
    yield
    telegram_commander.stop()
    stop_scheduler()


app = FastAPI(
    title="AI Hedge Fund",
    description="Multi-Agenten KI-Handelssystem mit Paper Trading",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_raw = os.getenv("CORS_ORIGINS", "*")
_cors_origins = _cors_raw.split(",") if _cors_raw != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class TradeRequest(BaseModel):
    symbol: str
    direction: str           # BUY | SELL
    size_chf: Optional[float] = None
    quantity: Optional[float] = None
    asset_type: Optional[str] = None


class WatchlistUpdate(BaseModel):
    stocks: list[str] = []
    etfs: list[str] = []
    crypto: list[str] = []


# --- Portfolio ---

@app.get("/portfolio")
async def portfolio():
    with get_conn() as conn:
        return get_portfolio_with_value(conn)


# --- Analysis ---

@app.post("/analyze/{symbol}")
async def analyze(symbol: str):
    symbol = symbol.upper()
    with get_conn() as conn:
        portfolio_data = get_portfolio_with_value(conn)

    try:
        result = await run_analysis(
            symbol=symbol,
            portfolio=portfolio_data,
            positions=portfolio_data.get("positions", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    with get_conn() as conn:
        analysis_id = insert_analysis(
            conn,
            symbol=result["symbol"],
            asset_type=result["asset_type"],
            orchestrator=result["orchestrator"],
            signals=result["signals"],
        )

    return {**result, "analysis_id": analysis_id}


@app.get("/analyses")
async def list_analyses(limit: int = 50):
    with get_conn() as conn:
        return get_analyses(conn, limit=limit)


@app.get("/analyses/latest/{symbol}")
async def latest_analysis(symbol: str):
    symbol = symbol.upper()
    with get_conn() as conn:
        result = get_latest_analysis(conn, symbol)
    if not result:
        raise HTTPException(status_code=404, detail=f"Keine Analyse für {symbol} gefunden")
    return result


# --- Trades ---

@app.post("/trade/execute")
async def trade_execute(req: TradeRequest):
    symbol = req.symbol.upper()
    direction = req.direction.upper()

    if direction not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="direction muss BUY oder SELL sein")

    # Asset-Type aus letzter Analyse holen oder bestimmen
    asset_type = req.asset_type
    if not asset_type:
        with get_conn() as conn:
            latest = get_latest_analysis(conn, symbol)
        asset_type = latest["asset_type"] if latest else "stock"

    try:
        if direction == "BUY":
            size = req.size_chf or 5000.0
            result = execute_buy(symbol, asset_type, size)
        else:
            result = execute_sell(symbol, asset_type, quantity=req.quantity)
    except InsufficientCashError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoPositionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@app.post("/trade/auto/{symbol}")
async def trade_auto(symbol: str):
    """Analysiert und führt Trade automatisch aus (wie der Scheduler)."""
    symbol = symbol.upper()
    with get_conn() as conn:
        portfolio_data = get_portfolio_with_value(conn)

    result = await run_analysis(
        symbol=symbol,
        portfolio=portfolio_data,
        positions=portfolio_data.get("positions", []),
    )

    with get_conn() as conn:
        insert_analysis(conn, result["symbol"], result["asset_type"],
                        result["orchestrator"], result["signals"])

    trade = execute_from_analysis(result)
    return {
        "analysis": result,
        "trade_executed": trade,
    }


@app.get("/trades")
async def list_trades(limit: int = 100):
    with get_conn() as conn:
        return get_trades(conn, limit=limit)


# --- Performance ---

@app.get("/performance")
async def performance():
    with get_conn() as conn:
        trades = get_trades(conn, limit=1000)
        benchmarks = get_benchmarks(conn, days=365)
        portfolio_data = get_portfolio_with_value(conn)

    completed_trades = [t for t in trades if t.get("pnl_chf") is not None]
    wins = [t for t in completed_trades if t["pnl_chf"] > 0]
    losses = [t for t in completed_trades if t["pnl_chf"] < 0]
    win_rate = len(wins) / len(completed_trades) * 100 if completed_trades else 0.0

    total_pnl = sum(t["pnl_chf"] for t in completed_trades)
    best_trade = max(completed_trades, key=lambda t: t["pnl_chf"]) if completed_trades else None
    worst_trade = min(completed_trades, key=lambda t: t["pnl_chf"]) if completed_trades else None

    # Sharpe Ratio aus Benchmark-Snapshots
    sharpe = None
    if len(benchmarks) >= 5:
        import numpy as np
        values = [b["portfolio_value_chf"] for b in benchmarks]
        returns = [(values[i] - values[i - 1]) / values[i - 1] for i in range(1, len(values))]
        if len(returns) > 1:
            mean_r = np.mean(returns)
            std_r = np.std(returns)
            if std_r > 0:
                # Annualisiert (täglich → *sqrt(252))
                sharpe = round(mean_r / std_r * math.sqrt(252), 3)

    from config import STARTING_CAPITAL_CHF
    total_return_pct = (portfolio_data["total_value_chf"] / STARTING_CAPITAL_CHF - 1) * 100

    return {
        "total_value_chf": portfolio_data["total_value_chf"],
        "total_return_pct": round(total_return_pct, 2),
        "total_pnl_chf": round(total_pnl, 2),
        "num_trades": len(trades),
        "num_completed": len(completed_trades),
        "win_rate_pct": round(win_rate, 1),
        "wins": len(wins),
        "losses": len(losses),
        "sharpe_ratio": sharpe,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "benchmarks": benchmarks,
    }


# --- Watchlist ---

@app.get("/watchlist")
async def get_watchlist():
    try:
        with open(WATCHLIST_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"stocks": [], "etfs": [], "crypto": []}


@app.put("/watchlist")
async def update_watchlist(data: WatchlistUpdate):
    watchlist = {
        "stocks": [s.upper() for s in data.stocks],
        "etfs": [s.upper() for s in data.etfs],
        "crypto": [s.upper() for s in data.crypto],
    }
    with open(WATCHLIST_PATH, "w") as f:
        json.dump(watchlist, f, indent=2)
    return watchlist


# --- Scheduler manuell auslösen ---

@app.post("/scheduler/run-now")
async def scheduler_run_now():
    """Sofortige tägliche Analyse ausführen (ohne auf 09:00 zu warten)."""
    await run_daily_analysis()
    return {"status": "done"}


# --- Screener ---

@app.get("/screener/results")
async def screener_results():
    """Letztes Screener-Ergebnis aus der DB."""
    with get_conn() as conn:
        return get_screener_results(conn)


@app.post("/screener/run")
async def screener_run(top_n: int = 25):
    """Screener sofort ausführen — scannt ~200 Symbole, gibt Top N zurück."""
    results = await run_screener(top_n=top_n)
    run_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        insert_screener_results(conn, run_at, results)
    return {"count": len(results), "run_at": run_at, "results": results}


@app.get("/universe")
async def get_universe():
    """Gibt die komplette Symbol-Universum-Liste zurück."""
    from universe import STOCKS, CRYPTO, ETFS, ALL_SYMBOLS
    return {
        "total": len(ALL_SYMBOLS),
        "stocks": len(STOCKS),
        "crypto": len(CRYPTO),
        "etfs": len(ETFS),
        "symbols": ALL_SYMBOLS,
    }


@app.get("/kraken/balance")
async def kraken_balance():
    """Zeigt echte Kraken-Kontostände (nur wenn KRAKEN_LIVE_ENABLED=true)."""
    if not kraken_client.is_kraken_enabled():
        raise HTTPException(status_code=503, detail="Kraken nicht konfiguriert (KRAKEN_LIVE_ENABLED=false oder Keys fehlen)")
    try:
        client = kraken_client.get_client()
        balance = await asyncio.to_thread(client.get_balance)
        # Nur relevante Assets zurückgeben (kein Staub unter 0.0001)
        fiat = {"ZEUR", "ZUSD", "ZGBP", "ZCAD", "KFEE"}
        crypto_balance = {k: v for k, v in balance.items() if v > 0.0001 or k in fiat and v > 0.01}
        held_symbols = await asyncio.to_thread(kraken_client.get_held_symbols)
        return {
            "enabled": True,
            "balance": crypto_balance,
            "tradeable_symbols": held_symbols,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "AI Hedge Fund Backend",
        "db": "connected" if _db_ready else "unavailable",
    }
