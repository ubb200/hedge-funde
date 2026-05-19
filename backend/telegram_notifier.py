"""
Telegram-Benachrichtigung mit Bestätigung vor echten Kraken-Trades.
Erfordert: TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID in den Env-Variablen.
"""
import asyncio
import json
import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

APPROVAL_TIMEOUT_SEC = 900  # 15 Minuten


def _url(method: str) -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    return f"https://api.telegram.org/bot{token}/{method}"


def _send(chat_id: str, text: str, keyboard: dict | None = None) -> dict:
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        resp = requests.post(_url("sendMessage"), json=payload, timeout=15)
        return resp.json()
    except Exception as exc:
        logger.error(f"Telegram sendMessage Fehler: {exc}")
        return {}


def _get_updates(offset: int = 0, timeout: int = 30) -> list:
    try:
        resp = requests.get(
            _url("getUpdates"),
            params={
                "offset": offset,
                "timeout": timeout,
                "allowed_updates": ["callback_query"],
            },
            timeout=timeout + 10,
        )
        return resp.json().get("result", [])
    except Exception as exc:
        logger.error(f"Telegram getUpdates Fehler: {exc}")
        return []


def _answer_callback(callback_id: str, text: str) -> None:
    try:
        requests.post(
            _url("answerCallbackQuery"),
            json={"callback_query_id": callback_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def _is_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN")) and bool(os.getenv("TELEGRAM_CHAT_ID"))


async def request_trade_approval(
    symbol: str,
    action: str,
    size_eur: float,
    confidence: float,
    weighted_score: float,
) -> bool:
    """
    Sendet eine Telegram-Nachricht mit Ja/Nein-Buttons und wartet auf Bestätigung.
    Gibt True zurück wenn genehmigt, False bei Ablehnung oder Timeout.
    Falls Telegram nicht konfiguriert: gibt True zurück (Trade läuft durch).
    """
    if not _is_configured():
        logger.warning("Telegram nicht konfiguriert — Kraken-Trade BLOCKIERT (Sicherheitsschutz)")
        return False

    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    emoji = "🟢" if action == "BUY" else "🔴"

    text = (
        f"{emoji} <b>Trade-Anfrage</b>\n\n"
        f"<b>Symbol:</b> {symbol}\n"
        f"<b>Aktion:</b> {action}\n"
        f"<b>Betrag:</b> EUR {size_eur:.0f}\n"
        f"<b>Konfidenz:</b> {confidence:.0%}\n"
        f"<b>Score:</b> {weighted_score:+.3f}\n\n"
        f"⏳ <i>Du hast 15 Minuten zum Bestätigen.</i>"
    )

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Ja, ausführen", "callback_data": "approve"},
            {"text": "❌ Nein, überspringen", "callback_data": "reject"},
        ]]
    }

    result = await asyncio.to_thread(_send, chat_id, text, keyboard)
    if not result.get("ok"):
        logger.error(f"Telegram Nachricht fehlgeschlagen: {result}")
        return False

    logger.info(f"Telegram Bestätigung angefordert für {action} {symbol}")

    # Aktuellen Update-Offset setzen (alte Messages ignorieren)
    initial = await asyncio.to_thread(_get_updates, offset=0, timeout=0)
    offset = (initial[-1]["update_id"] + 1) if initial else 0

    deadline = time.time() + APPROVAL_TIMEOUT_SEC

    while time.time() < deadline:
        remaining = deadline - time.time()
        poll_timeout = min(30, int(remaining))
        if poll_timeout <= 0:
            break

        updates = await asyncio.to_thread(_get_updates, offset=offset, timeout=poll_timeout)

        for upd in updates:
            offset = upd["update_id"] + 1
            cb = upd.get("callback_query")
            if not cb:
                continue

            decision = cb.get("data")
            if decision == "approve":
                await asyncio.to_thread(
                    _answer_callback, cb["id"], "✅ Trade wird ausgeführt!"
                )
                logger.info(f"Telegram: {action} {symbol} GENEHMIGT")
                return True
            else:
                await asyncio.to_thread(
                    _answer_callback, cb["id"], "❌ Trade übersprungen."
                )
                logger.info(f"Telegram: {action} {symbol} ABGELEHNT")
                return False

    # Timeout
    logger.warning(f"Telegram Timeout für {action} {symbol} — Trade übersprungen")
    await asyncio.to_thread(
        _send, chat_id,
        f"⏰ Timeout — <b>{action} {symbol}</b> wurde übersprungen (keine Antwort in 15 Min)."
    )
    return False


# yfinance-Symbol → Kraken xStock Asset-Name (für manuelle Trades)
XSTOCK_NAMES: dict[str, str] = {
    "MSFT":  "MSFTx.T",
    "AAPL":  "AAPLx.T",
    "NVDA":  "NVDAx.T",
    "TSLA":  "TSLAx.T",
    "GOOGL": "GOOGLx.T",
    "AMZN":  "AMZNx.T",
    "META":  "METAx.T",
    "PLTR":  "PLTRx.T",
    "COIN":  "COINx.T",
    "AMD":   "AMDx.T",
    "INTC":  "INTCx.T",
    "NFLX":  "NFLXx.T",
    "JPM":   "JPMx.T",
    "JNJ":   "JNJx.T",
    "XOM":   "XOMx.T",
    "SPY":   "SPYx.T",
    "QQQ":   "QQQx.T",
    "GLD":   "GLDx.T",
    "SLV":   "SLVx.T",
    "VT":    "VTx.T",
    "ARKK":  "ARKKx.T",
}

# Schwelle für reine Signal-Notifications (niedriger als Auto-Trade)
SIGNAL_MIN_CONFIDENCE = 0.65


async def send_signal_notification(
    symbol: str,
    action: str,
    confidence: float,
    weighted_score: float,
    reasoning: str,
    kraken_asset: str | None = None,
) -> None:
    """
    Sendet eine reine Signal-Info (kein Trade-Button) für Symbole
    die der Bot nicht automatisch handeln kann (xStocks, Aktien, ETFs).
    """
    if not _is_configured():
        return
    if action == "HOLD":
        return
    if confidence < SIGNAL_MIN_CONFIDENCE:
        return

    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    emoji = "🟢" if action == "BUY" else "🔴"
    kraken_line = f"\n<b>Kraken Asset:</b> <code>{kraken_asset}</code>" if kraken_asset else ""
    short_reason = reasoning[:200] + "…" if len(reasoning) > 200 else reasoning

    text = (
        f"{emoji} <b>Signal: {symbol}</b>{kraken_line}\n\n"
        f"<b>Empfehlung:</b> {action}\n"
        f"<b>Konfidenz:</b> {confidence:.0%}\n"
        f"<b>Score:</b> {weighted_score:+.3f}\n\n"
        f"<i>{short_reason}</i>\n\n"
        f"⚠️ <b>Manuell handeln</b> — Bot kann dieses Asset nicht automatisch traden."
    )

    await asyncio.to_thread(_send, chat_id, text)
    logger.info(f"Telegram Signal gesendet: {action} {symbol} (Konfidenz {confidence:.0%})")


async def send_trade_confirmation(
    symbol: str,
    action: str,
    volume: float,
    price_eur: float,
    order_ids: list,
) -> None:
    """Sendet eine Bestätigung nach erfolgreichem Trade."""
    if not _is_configured():
        return
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    total = volume * price_eur
    emoji = "✅🟢" if action == "BUY" else "✅🔴"
    text = (
        f"{emoji} <b>Trade ausgeführt</b>\n\n"
        f"<b>Symbol:</b> {symbol}\n"
        f"<b>Aktion:</b> {action}\n"
        f"<b>Menge:</b> {volume:.6f}\n"
        f"<b>Preis:</b> EUR {price_eur:.2f}\n"
        f"<b>Total:</b> EUR {total:.2f}\n"
        f"<b>Order-ID:</b> {', '.join(str(o) for o in order_ids)}"
    )
    await asyncio.to_thread(_send, chat_id, text)
