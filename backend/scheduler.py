import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import AUTO_TRADE_ENABLED, AUTO_TRADE_HOUR, MAX_POSITION_PCT, KRAKEN_TRADE_SIZE_EUR
from database import (
    get_conn, get_positions, insert_analysis, insert_benchmark,
    insert_screener_results, mark_screener_analyzed,
)
from orchestrator import run_analysis
from paper_trading import get_portfolio_with_value, execute_from_analysis, execute_sell
from data_fetchers.yfinance_fetcher import get_current_price
from screener import run_screener
import kraken_client

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

STOP_LOSS_PCT = -0.08   # -8%  Verlust → automatisch verkaufen
TAKE_PROFIT_PCT = 0.25  # +25% Gewinn  → automatisch verkaufen


async def _stop_loss_take_profit_sweep():
    """Überprüft alle offenen Positionen auf Stop-Loss / Take-Profit."""
    with get_conn() as conn:
        positions = get_positions(conn)

    if not positions:
        return

    logger.info(f"Stop-Loss/Take-Profit Sweep: {len(positions)} Positionen prüfen...")

    for pos in positions:
        try:
            symbol = pos["symbol"]
            price = await asyncio.to_thread(get_current_price, symbol)
            if price is None:
                continue

            pnl_pct = (price - pos["avg_buy_price"]) / pos["avg_buy_price"]

            if pnl_pct <= STOP_LOSS_PCT:
                logger.warning(
                    f"STOP-LOSS: {symbol} {pnl_pct:+.1%} "
                    f"(Einstieg {pos['avg_buy_price']:.2f} → jetzt {price:.2f}) — verkaufe"
                )
                execute_sell(symbol, pos["asset_type"])

            elif pnl_pct >= TAKE_PROFIT_PCT:
                logger.info(
                    f"TAKE-PROFIT: {symbol} {pnl_pct:+.1%} "
                    f"(Einstieg {pos['avg_buy_price']:.2f} → jetzt {price:.2f}) — verkaufe"
                )
                execute_sell(symbol, pos["asset_type"])

        except Exception as e:
            logger.error(f"Stop-Loss/TP Fehler bei {pos['symbol']}: {e}")


async def _rebalance_oversized_positions():
    """Trimmt Positionen die mehr als 1.5x MAX_POSITION_PCT des Portfolios ausmachen."""
    trim_threshold = MAX_POSITION_PCT * 1.5

    with get_conn() as conn:
        portfolio = get_portfolio_with_value(conn)

    total = portfolio.get("total_value_chf", 0)
    if total <= 0:
        return

    for pos in portfolio.get("positions", []):
        pos_value = pos.get("position_value_chf") or 0
        if pos_value <= 0:
            continue

        pos_pct = pos_value / total
        if pos_pct > trim_threshold:
            target_value = total * MAX_POSITION_PCT
            excess_value = pos_value - target_value
            excess_qty = (excess_value / pos_value) * pos["quantity"]
            logger.info(
                f"REBALANCING: {pos['symbol']} = {pos_pct:.1%} des Portfolios "
                f"(Limit {trim_threshold:.0%}) — trimme {excess_qty:.4f} Einheiten"
            )
            try:
                execute_sell(pos["symbol"], pos["asset_type"], quantity=excess_qty)
            except Exception as e:
                logger.error(f"Rebalancing Fehler bei {pos['symbol']}: {e}")


async def run_daily_analysis():
    logger.info("=== Tägliche Auto-Analyse gestartet ===")

    # Stufe 0a: Rebalancing — übergrosse Positionen trimmen
    logger.info("Stufe 0a: Rebalancing Sweep...")
    await _rebalance_oversized_positions()

    # Stufe 0b: Stop-Loss / Take-Profit — Verluste begrenzen, Gewinne sichern
    logger.info("Stufe 0b: Stop-Loss / Take-Profit Sweep...")
    await _stop_loss_take_profit_sweep()

    # Stufe 1: Screener — ~200 Symbole scannen, Top 25 finden
    logger.info("Stufe 1: Screener läuft...")
    screened = await run_screener(top_n=25)
    if not screened:
        logger.warning("Screener hat keine Kandidaten — Analyse abgebrochen")
        return

    run_at = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        insert_screener_results(conn, run_at, screened)

    screened_symbols = [s["symbol"] for s in screened]
    logger.info(f"Stufe 1 abgeschlossen: {len(screened_symbols)} Kandidaten")

    # Bestehende Positionen IMMER analysieren (Exit-Signale nicht verpassen)
    with get_conn() as conn:
        existing_positions = get_positions(conn)
    existing_symbols = [p["symbol"] for p in existing_positions]

    # Dedupliziert: bestehende Positionen zuerst, dann neue Kandidaten
    all_symbols = list(dict.fromkeys(existing_symbols + screened_symbols))
    logger.info(
        f"Analyse-Queue: {len(existing_symbols)} bestehend + "
        f"{len(screened_symbols)} neu = {len(all_symbols)} total"
    )

    # Stufe 2: Claude-Tiefenanalyse
    logger.info("Stufe 2: Tiefenanalyse mit Claude-Agenten...")
    with get_conn() as conn:
        portfolio_data = get_portfolio_with_value(conn)

    results = []
    for symbol in all_symbols:
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
                if symbol in screened_symbols:
                    mark_screener_analyzed(conn, symbol)

            if AUTO_TRADE_ENABLED:
                trade = execute_from_analysis(result)
                if trade:
                    logger.info(
                        f"  Paper-Trade: {trade['direction']} {symbol} "
                        f"@ CHF {trade['price_chf']:.2f}"
                    )
                else:
                    logger.info(f"  → HOLD für {symbol}")

                # Kraken Live Trade — nur für Krypto mit sehr guter Analyse
                orch = result.get("orchestrator", {})
                kraken_result = kraken_client.execute_live_trade(
                    symbol=symbol,
                    action=orch.get("action", "HOLD"),
                    confidence=orch.get("confidence", 0.0),
                    weighted_score=orch.get("weighted_score", 0.0),
                    size_eur=KRAKEN_TRADE_SIZE_EUR,
                )
                if kraken_result:
                    logger.info(
                        f"  KRAKEN LIVE: {orch.get('action')} {symbol} "
                        f"— Order IDs: {kraken_result.get('order_ids')}"
                    )

            results.append(result)

        except Exception as e:
            logger.error(f"Fehler bei {symbol}: {e}", exc_info=True)

    await _take_benchmark_snapshot()
    logger.info(f"=== Analyse abgeschlossen: {len(results)}/{len(all_symbols)} erfolgreich ===")


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
