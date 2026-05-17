import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import AUTO_TRADE_ENABLED, AUTO_TRADE_HOUR
from database import (
    get_conn, insert_analysis, insert_benchmark,
    insert_screener_results, mark_screener_analyzed,
)
from orchestrator import run_analysis
from paper_trading import get_portfolio_with_value, execute_from_analysis
from data_fetchers.yfinance_fetcher import get_current_price
from screener import run_screener

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_daily_analysis():
    logger.info("=== Tägliche Auto-Analyse gestartet ===")

    # Stufe 1: Screener — alle ~200 Symbole scannen, Top 25 finden
    logger.info("Stufe 1: Screener läuft...")
    screened = await run_screener(top_n=25)
    if not screened:
        logger.warning("Screener hat keine Kandidaten gefunden — Analyse abgebrochen")
        return

    run_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        insert_screener_results(conn, run_at, screened)

    symbols = [s["symbol"] for s in screened]
    logger.info(f"Stufe 1 abgeschlossen: {len(symbols)} Kandidaten — {', '.join(symbols[:10])}...")

    # Stufe 2: Claude-Tiefenanalyse der Top-Kandidaten
    logger.info("Stufe 2: Tiefenanalyse mit Claude-Agenten...")
    with get_conn() as conn:
        portfolio_data = get_portfolio_with_value(conn)

    results = []
    for symbol in symbols:
        try:
            logger.info(f"  Analysiere {symbol}...")
            result = await run_analysis(
                symbol=symbol,
                portfolio=portfolio_data,
                positions=portfolio_data.get("positions", []),
            )

            with get_conn() as conn:
                insert_analysis(
                    conn,
                    symbol=result["symbol"],
                    asset_type=result["asset_type"],
                    orchestrator=result["orchestrator"],
                    signals=result["signals"],
                )
                mark_screener_analyzed(conn, symbol)

            if AUTO_TRADE_ENABLED:
                trade = execute_from_analysis(result)
                if trade:
                    logger.info(
                        f"  Trade: {trade['direction']} {symbol} "
                        f"@ CHF {trade['price_chf']:.2f}"
                    )
                else:
                    logger.info(f"  → HOLD für {symbol}")

            results.append(result)

        except Exception as e:
            logger.error(f"Fehler bei {symbol}: {e}", exc_info=True)

    await _take_benchmark_snapshot()
    logger.info(f"=== Analyse abgeschlossen: {len(results)}/{len(symbols)} erfolgreich ===")


async def _take_benchmark_snapshot():
    try:
        with get_conn() as conn:
            portfolio_data = get_portfolio_with_value(conn)

        sp500 = await asyncio.to_thread(get_current_price, "SPY")
        btc = await asyncio.to_thread(get_current_price, "BTC-USD")
        today = datetime.now(timezone.utc).date().isoformat()

        with get_conn() as conn:
            insert_benchmark(
                conn,
                date=today,
                sp500=sp500,
                btc=btc,
                portfolio_chf=portfolio_data["total_value_chf"],
            )
        logger.info(
            f"Benchmark-Snapshot: Portfolio={portfolio_data['total_value_chf']:.0f} CHF, "
            f"SPY={sp500}, BTC={btc}"
        )
    except Exception as e:
        logger.error(f"Benchmark-Snapshot fehlgeschlagen: {e}")


def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Europe/Zurich")
    _scheduler.add_job(
        run_daily_analysis,
        CronTrigger(hour=AUTO_TRADE_HOUR, minute=0, timezone="Europe/Zurich"),
        id="daily_analysis",
        name="Tägliche AI-Hedge-Fund-Analyse",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"Scheduler gestartet — täglich {AUTO_TRADE_HOUR:02d}:00 Uhr (Zürich)")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler gestoppt")
