"""
Telegram-Commander: verarbeitet eingehende Befehle via Long-Polling.
Läuft als Background-Task parallel zum Haupt-Server.
Nur Nachrichten von der konfigurierten TELEGRAM_CHAT_ID werden akzeptiert.
"""
import asyncio
import logging
import os

import requests

logger = logging.getLogger(__name__)

_running = False
_offset = 0
_task: asyncio.Task | None = None


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", "")


def is_configured() -> bool:
    return bool(_token()) and bool(_chat_id())


def _send(text: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{_token()}/sendMessage",
            json={"chat_id": _chat_id(), "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as exc:
        logger.error(f"Telegram send error: {exc}")


def _get_updates(offset: int) -> list:
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{_token()}/getUpdates",
            params={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message"],
            },
            timeout=40,
        )
        return resp.json().get("result", [])
    except Exception as exc:
        logger.error(f"Telegram getUpdates error: {exc}")
        return []


async def _handle(text: str) -> None:
    from database import get_conn, get_trades as _get_trades
    from paper_trading import get_portfolio_with_value

    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "/status":
        with get_conn() as conn:
            p = get_portfolio_with_value(conn)
        positions = p.get("positions", [])
        lines = [
            "<b>Portfolio</b>",
            f"Kasse:      CHF {p['cash_chf']:>12,.2f}",
            f"Positionen: CHF {p['positions_value_chf']:>12,.2f}",
            f"<b>Total:      CHF {p['total_value_chf']:>12,.2f}</b>",
        ]
        if positions:
            lines.append("\n<b>Positionen:</b>")
            for pos in positions:
                cur = pos.get("current_price") or pos["avg_buy_price"]
                pct = (cur - pos["avg_buy_price"]) / pos["avg_buy_price"] * 100
                lines.append(
                    f"  {pos['symbol']}: {pos['quantity']:.4f} "
                    f"@ {pos['avg_buy_price']:.2f} ({pct:+.1f}%)"
                )
        else:
            lines.append("\nKeine offenen Positionen.")
        await asyncio.to_thread(_send, "\n".join(lines))

    elif cmd == "/analyse":
        if len(parts) < 2:
            await asyncio.to_thread(_send, "Verwendung: /analyse SYMBOL\nBeispiel: /analyse BTC-USD")
            return
        symbol = parts[1].upper()
        await asyncio.to_thread(_send, f"Analysiere <b>{symbol}</b>... (dauert 2-5 Min)")
        try:
            from orchestrator import run_analysis
            with get_conn() as conn:
                portfolio = get_portfolio_with_value(conn)
            result = await run_analysis(
                symbol=symbol,
                portfolio=portfolio,
                positions=portfolio.get("positions", []),
            )
            orch = result["orchestrator"]
            reasoning = orch.get("reasoning", "")[:500]
            msg = (
                f"<b>Analyse: {symbol}</b>\n\n"
                f"Empfehlung: <b>{orch['action']}</b>\n"
                f"Konfidenz: {orch['confidence']:.0%}\n"
                f"Score: {orch['weighted_score']:+.3f}\n\n"
                f"<i>{reasoning}</i>"
            )
            await asyncio.to_thread(_send, msg)
        except Exception as exc:
            await asyncio.to_thread(_send, f"Fehler bei {symbol}: {exc}")

    elif cmd == "/run":
        await asyncio.to_thread(
            _send, "Tagesanalyse gestartet... (dauert 15-30 Min, du kriegst Bescheid)"
        )
        try:
            from scheduler import run_daily_analysis
            await run_daily_analysis()
            await asyncio.to_thread(_send, "Tagesanalyse abgeschlossen.")
        except Exception as exc:
            await asyncio.to_thread(_send, f"Fehler bei Tagesanalyse: {exc}")

    elif cmd == "/trades":
        with get_conn() as conn:
            trades = _get_trades(conn, limit=10)
        if not trades:
            await asyncio.to_thread(_send, "Noch keine Trades.")
            return
        lines = ["<b>Letzte 10 Trades:</b>"]
        for t in trades:
            pnl = f" | P&amp;L CHF {t['pnl_chf']:+.2f}" if t.get("pnl_chf") is not None else ""
            lines.append(f"{t['direction']} {t['symbol']} — CHF {t['total_chf']:.2f}{pnl}")
        await asyncio.to_thread(_send, "\n".join(lines))

    elif cmd in ("/help", "/start"):
        await asyncio.to_thread(_send, (
            "<b>AI Hedge Fund — Befehle</b>\n\n"
            "/status — Portfolio &amp; Positionen\n"
            "/analyse SYMBOL — Analyse starten\n"
            "  Beispiel: /analyse BTC-USD\n"
            "/run — Tagesanalyse sofort starten\n"
            "/trades — Letzte 10 Trades\n"
            "/help — Diese Hilfe"
        ))

    else:
        await asyncio.to_thread(_send, "Unbekannter Befehl. Schreibe /help für alle Befehle.")


async def _loop():
    global _offset, _running
    logger.info("Telegram-Commander gestartet")
    while _running:
        try:
            updates = await asyncio.to_thread(_get_updates, _offset)
            for upd in updates:
                _offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg:
                    continue
                if str(msg.get("chat", {}).get("id")) != _chat_id():
                    continue
                text = msg.get("text", "")
                if text.startswith("/"):
                    asyncio.create_task(_handle(text))
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Telegram-Commander Fehler: {exc}", exc_info=True)
            await asyncio.sleep(5)

        if not updates:
            await asyncio.sleep(1)
    logger.info("Telegram-Commander gestoppt")


def start():
    global _running, _task
    if not is_configured():
        logger.info("Telegram nicht konfiguriert — Commander nicht gestartet")
        return
    _running = True
    _task = asyncio.ensure_future(_loop())
    logger.info("Telegram-Commander Task gestartet")


def stop():
    global _running, _task
    _running = False
    if _task and not _task.done():
        _task.cancel()
