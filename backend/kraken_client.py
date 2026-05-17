"""
Kraken Live Trading — nur für Krypto-Assets.
Aktiv nur wenn KRAKEN_LIVE_ENABLED=true und API-Keys gesetzt.
"""
import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse

import requests

logger = logging.getLogger(__name__)

KRAKEN_API_URL = "https://api.kraken.com"

# yfinance-Symbol → Kraken-Tradingpair (EUR)
# Pair-Namen verifiziert via Kraken Public AssetPairs API
SYMBOL_TO_PAIR: dict[str, str] = {
    # Layer 1 — Hauptcoins
    "BTC-USD":   "XXBTZEUR",
    "ETH-USD":   "XETHZEUR",
    "SOL-USD":   "SOLEUR",
    "XRP-USD":   "XXRPZEUR",
    "ADA-USD":   "ADAEUR",
    "DOGE-USD":  "XDGEUR",
    "DOT-USD":   "DOTEUR",
    "AVAX-USD":  "AVAXEUR",
    "LTC-USD":   "XLTCZEUR",
    "ATOM-USD":  "ATOMEUR",
    "LINK-USD":  "LINKEUR",
    "UNI-USD":   "UNIEUR",
    "AAVE-USD":  "AAVEEUR",
    "ALGO-USD":  "ALGOEUR",
    "BCH-USD":   "BCHEUR",
    "ETC-USD":   "XETCZEUR",
    "XLM-USD":   "XXLMZEUR",
    "XMR-USD":   "XXMRZEUR",
    "ZEC-USD":   "XZECZEUR",
    "DASH-USD":  "DASHEUR",
    # Layer 2 / DeFi
    "MATIC-USD": "POLEUR",
    "POL-USD":   "POLEUR",
    "ARB-USD":   "ARBEUR",
    "OP-USD":    "OPEUR",
    "LDO-USD":   "LDOEUR",
    "CRV-USD":   "CRVEUR",
    "SNX-USD":   "SNXEUR",
    "COMP-USD":  "COMPEUR",
    "MKR-USD":   "MEUREUR",
    "YFI-USD":   "YFIEUR",
    "BAL-USD":   "BALEUR",
    "SUSHI-USD": "SUSHIEUR",
    "GRT-USD":   "GRTEUR",
    # Neue L1s
    "NEAR-USD":  "NEAREUR",
    "ICP-USD":   "ICPEUR",
    "APT-USD":   "APTEUR",
    "SUI-USD":   "SUIEUR",
    "INJ-USD":   "INJEUR",
    "TIA-USD":   "TIAEUR",
    "SEI-USD":   "SEIEUR",
    "KSM-USD":   "KSMEUR",
    "EGLD-USD":  "EGLDEUR",
    "FIL-USD":   "FILEUR",
    "FLOW-USD":  "FLOWEUR",
    "HBAR-USD":  "HBAREUR",
    "VET-USD":   "VETEUR",
    "XTZ-USD":   "XTZEUR",
    # Meme & Trend
    "SHIB-USD":  "SHIBEUR",
    "PEPE-USD":  "PEPEEUR",
    "BONK-USD":  "BONKEUR",
    "WIF-USD":   "WIFEUR",
    "FLOKI-USD": "FLOKIEUR",
    # Gaming / Metaverse
    "SAND-USD":  "SANDEUR",
    "MANA-USD":  "MANAEUR",
    "AXS-USD":   "AXSEUR",
    "ENJ-USD":   "ENJEUR",
    "CHZ-USD":   "CHZEUR",
    # AI / Daten
    "FET-USD":   "FETEUR",
    "OCEAN-USD": "OCEANEUR",
    "RENDER-USD":"RENDEREUR",
    "TAO-USD":   "TAOEUR",
    # Sonstige populäre
    "KAS-USD":   "KASEUR",
    "TON-USD":   "TONEUR",
    "JUP-USD":   "JUPEUR",
    "JTO-USD":   "JTOEUR",
    "PYTH-USD":  "PYTHEUR",
    "WLD-USD":   "WLDEUR",
    "TRX-USD":   "TRXEUR",
    "DYDX-USD":  "DYDXEUR",
    "RPL-USD":   "RPLEUR",
    "STX-USD":   "STXEUR",
    "PENDLE-USD":"PENDLEEUR",
    "ENA-USD":   "ENAEUR",
    "ONDO-USD":  "ONDOEUR",
}

# Kraken-Asset-Code → für Balance-Abfrage
PAIR_TO_ASSET: dict[str, str] = {
    "XXBTZEUR": "XXBT",
    "XETHZEUR": "XETH",
    "SOLEUR":   "SOL",
    "XXRPZEUR": "XXRP",
    "ADAEUR":   "ADA",
    "XDGEUR":   "XXDG",
    "DOTEUR":   "DOT",
    "AVAXEUR":  "AVAX",
    "XLTCZEUR": "XLTC",
    "ATOMEUR":  "ATOM",
    "LINKEUR":  "LINK",
    "UNIEUR":   "UNI",
    "AAVEEUR":  "AAVE",
    "ALGOEUR":  "ALGO",
    "BCHEUR":   "BCH",
    "XETCZEUR": "XETC",
    "XXLMZEUR": "XXLM",
    "XXMRZEUR": "XXMR",
    "XZECZEUR": "XZEC",
    "DASHEUR":  "DASH",
    "POLEUR":   "POL",
    "ARBEUR":   "ARB",
    "OPEUR":    "OP",
    "LDOEUR":   "LDO",
    "CRVEUR":   "CRV",
    "SNXEUR":   "SNX",
    "COMPEUR":  "COMP",
    "YFIEUR":   "YFI",
    "BALEUR":   "BAL",
    "SUSHIEUR": "SUSHI",
    "GRTEUR":   "GRT",
    "NEAREUR":  "NEAR",
    "ICPEUR":   "ICP",
    "APTEUR":   "APT",
    "SUIEUR":   "SUI",
    "INJEUR":   "INJ",
    "TIAEUR":   "TIA",
    "SEIEUR":   "SEI",
    "KSMEUR":   "KSM",
    "EGLDEUR":  "EGLD",
    "FILEUR":   "FIL",
    "FLOWEUR":  "FLOW",
    "HBAREUR":  "HBAR",
    "VETEUR":   "VET",
    "XTZEUR":   "XTZ",
    "SHIBEUR":  "SHIB",
    "PEPEEUR":  "PEPE",
    "BONKEUR":  "BONK",
    "WIFEUR":   "WIF",
    "FLOKIEUR": "FLOKI",
    "SANDEUR":  "SAND",
    "MANAEUR":  "MANA",
    "AXSEUR":   "AXS",
    "ENJEUR":   "ENJ",
    "CHZEUR":   "CHZ",
    "FETEUR":   "FET",
    "OCEANEUR": "OCEAN",
    "RENDEREUR":"RENDER",
    "TAOEUR":   "TAO",
    "KASEUR":   "KAS",
    "TONEUR":   "TON",
    "JUPEUR":   "JUP",
    "JTOEUR":   "JTO",
    "PYTHEUR":  "PYTH",
    "WLDEUR":   "WLD",
    "TRXEUR":   "TRX",
    "DYDXEUR":  "DYDX",
    "RPLEUR":   "RPL",
    "STXEUR":   "STX",
    "PENDLEEUR":"PENDLE",
    "ENAEUR":   "ENA",
    "ONDOEUR":  "ONDO",
}

# Minimale Ordervolumina pro Pair (Kraken-Anforderung)
MIN_VOLUME: dict[str, float] = {
    "XXBTZEUR": 0.0001,
    "XETHZEUR": 0.01,
    "SOLEUR":   0.5,
    "XXRPZEUR": 10.0,
    "ADAEUR":   15.0,
    "XDGEUR":   50.0,
    "DOTEUR":   0.5,
    "AVAXEUR":  0.2,
    "XLTCZEUR": 0.1,
    "ATOMEUR":  0.5,
    "LINKEUR":  0.5,
    "UNIEUR":   0.5,
    "AAVEEUR":  0.05,
    "ALGOEUR":  15.0,
    "BCHEUR":   0.01,
    "XETCZEUR": 0.1,
    "XXLMZEUR": 30.0,
    "XXMRZEUR": 0.05,
    "XZECZEUR": 0.05,
    "DASHEUR":  0.05,
    "POLEUR":   10.0,
    "ARBEUR":   5.0,
    "OPEUR":    2.0,
    "LDOEUR":   1.0,
    "CRVEUR":   5.0,
    "SNXEUR":   1.0,
    "COMPEUR":  0.05,
    "YFIEUR":   0.001,
    "BALEUR":   0.5,
    "SUSHIEUR": 2.0,
    "GRTEUR":   10.0,
    "NEAREUR":  1.0,
    "ICPEUR":   0.5,
    "APTEUR":   0.5,
    "SUIEUR":   2.0,
    "INJEUR":   0.2,
    "TIAEUR":   0.5,
    "SEIEUR":   5.0,
    "KSMEUR":   0.05,
    "EGLDEUR":  0.1,
    "FILEUR":   0.5,
    "FLOWEUR":  2.0,
    "HBAREUR":  50.0,
    "VETEUR":   100.0,
    "XTZEUR":   1.0,
    "SHIBEUR":  1000000.0,
    "PEPEEUR":  1000000.0,
    "BONKEUR":  1000000.0,
    "WIFEUR":   1.0,
    "FLOKIEUR": 1000.0,
    "SANDEUR":  2.0,
    "MANAEUR":  2.0,
    "AXSEUR":   0.2,
    "ENJEUR":   2.0,
    "CHZEUR":   5.0,
    "FETEUR":   2.0,
    "OCEANEUR": 5.0,
    "RENDEREUR":0.5,
    "TAOEUR":   0.01,
    "KASEUR":   5.0,
    "TONEUR":   1.0,
    "JUPEUR":   2.0,
    "JTOEUR":   0.5,
    "PYTHEUR":  10.0,
    "WLDEUR":   0.5,
    "TRXEUR":   50.0,
    "DYDXEUR":  1.0,
    "RPLEUR":   0.1,
    "STXEUR":   2.0,
    "PENDLEEUR":0.5,
    "ENAEUR":   2.0,
    "ONDOEUR":  2.0,
}


class KrakenClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self._session = requests.Session()

    def _sign(self, urlpath: str, data: dict) -> str:
        post_data = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()

    def _private(self, endpoint: str, data: dict | None = None) -> dict:
        data = dict(data or {})
        data["nonce"] = str(int(time.time() * 1000))
        urlpath = f"/0/private/{endpoint}"
        resp = self._session.post(
            f"{KRAKEN_API_URL}{urlpath}",
            data=data,
            headers={
                "API-Key": self.api_key,
                "API-Sign": self._sign(urlpath, data),
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise ValueError(f"Kraken API Fehler: {body['error']}")
        return body["result"]

    def _public(self, endpoint: str, params: dict | None = None) -> dict:
        resp = self._session.get(
            f"{KRAKEN_API_URL}/0/public/{endpoint}",
            params=params or {},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise ValueError(f"Kraken API Fehler: {body['error']}")
        return body["result"]

    def get_balance(self) -> dict[str, float]:
        raw = self._private("Balance")
        return {k: float(v) for k, v in raw.items()}

    def get_ask_price_eur(self, pair: str) -> float:
        result = self._public("Ticker", {"pair": pair})
        data = next(iter(result.values()))
        return float(data["a"][0])

    def buy(self, pair: str, size_eur: float) -> dict:
        price = self.get_ask_price_eur(pair)
        volume = size_eur / price
        min_vol = MIN_VOLUME.get(pair, 0.0001)
        if volume < min_vol:
            raise ValueError(
                f"Zu kleines Volumen: {volume:.6f} < Minimum {min_vol} für {pair}. "
                f"Mindestens EUR {min_vol * price:.2f} nötig."
            )
        result = self._private("AddOrder", {
            "pair":      pair,
            "type":      "buy",
            "ordertype": "market",
            "volume":    f"{volume:.8f}",
            "oflags":    "fciq",
        })
        logger.info(f"Kraken BUY Order: {result}")
        return {
            "order_ids":  result.get("txid", []),
            "pair":       pair,
            "volume":     volume,
            "price_eur":  price,
            "total_eur":  size_eur,
        }

    def sell_all(self, pair: str) -> dict | None:
        asset = PAIR_TO_ASSET.get(pair)
        if not asset:
            raise ValueError(f"Unbekanntes Asset für Pair {pair}")

        balance = self.get_balance()
        volume = balance.get(asset, 0.0)
        min_vol = MIN_VOLUME.get(pair, 0.0001)

        if volume < min_vol:
            logger.info(f"Kraken SELL {pair}: Guthaben {volume:.6f} unter Minimum {min_vol} — übersprungen")
            return None

        result = self._private("AddOrder", {
            "pair":      pair,
            "type":      "sell",
            "ordertype": "market",
            "volume":    f"{volume:.8f}",
        })
        logger.info(f"Kraken SELL Order: {result}")
        return {
            "order_ids": result.get("txid", []),
            "pair":      pair,
            "volume":    volume,
        }


# ── Öffentliche Hilfsfunktionen ──────────────────────────────────────────────

def is_kraken_enabled() -> bool:
    return (
        os.getenv("KRAKEN_LIVE_ENABLED", "false").lower() == "true"
        and bool(os.getenv("KRAKEN_API_KEY"))
        and bool(os.getenv("KRAKEN_API_SECRET"))
    )


def get_client() -> KrakenClient | None:
    if not is_kraken_enabled():
        return None
    return KrakenClient(
        api_key=os.getenv("KRAKEN_API_KEY", ""),
        api_secret=os.getenv("KRAKEN_API_SECRET", ""),
    )


def symbol_to_pair(symbol: str) -> str | None:
    return SYMBOL_TO_PAIR.get(symbol.upper())


def get_held_symbols() -> list[str]:
    """
    Gibt die yfinance-Symbole zurück, für die echte Bestände auf Kraken existieren
    (über dem Minimum-Volumen). Wird täglich für Exit-Analyse genutzt.
    """
    client = get_client()
    if not client:
        return []
    try:
        balance = client.get_balance()
        held = []
        fiat = {"ZEUR", "ZUSD", "ZGBP", "ZCAD", "KFEE", "CHF"}
        for symbol, pair in SYMBOL_TO_PAIR.items():
            asset = PAIR_TO_ASSET.get(pair)
            if not asset:
                continue
            amount = balance.get(asset, 0.0)
            if amount >= MIN_VOLUME.get(pair, 0.0001):
                held.append(symbol)
        logger.info(f"Kraken-Bestände (>Minimum): {held or 'keine'}")
        return held
    except Exception as exc:
        logger.error(f"Kraken Balance-Abfrage fehlgeschlagen: {exc}")
        return []


async def execute_live_trade(
    symbol: str,
    action: str,
    confidence: float,
    weighted_score: float,
    size_eur: float,
) -> dict | None:
    """
    Sendet zuerst eine Telegram-Bestätigung, dann Kraken-Trade — nur bei sehr guter Analyse.
    Gibt None zurück wenn deaktiviert, abgelehnt, Symbol nicht unterstützt, oder Fehler.
    """
    if not is_kraken_enabled():
        return None

    pair = symbol_to_pair(symbol)
    if not pair:
        return None

    min_conf = float(os.getenv("KRAKEN_MIN_CONFIDENCE", "0.85"))
    min_score = float(os.getenv("KRAKEN_MIN_SCORE", "0.65"))

    if confidence < min_conf or abs(weighted_score) < min_score:
        logger.info(
            f"Kraken {action} {symbol}: Schwelle nicht erreicht "
            f"(Konfidenz {confidence:.1%} < {min_conf:.0%} "
            f"oder Score |{weighted_score:+.3f}| < {min_score:.2f})"
        )
        return None

    # Telegram-Bestätigung anfordern
    from telegram_notifier import request_trade_approval, send_trade_confirmation
    approved = await request_trade_approval(
        symbol=symbol,
        action=action,
        size_eur=size_eur,
        confidence=confidence,
        weighted_score=weighted_score,
    )
    if not approved:
        logger.info(f"Kraken {action} {symbol}: Nicht genehmigt — übersprungen")
        return None

    client = get_client()
    if not client:
        return None

    try:
        if action == "BUY":
            logger.info(
                f"KRAKEN LIVE BUY: {symbol} → {pair} | "
                f"EUR {size_eur:.2f} | Konfidenz={confidence:.1%} | Score={weighted_score:+.3f}"
            )
            result = client.buy(pair, size_eur)
            await send_trade_confirmation(
                symbol=symbol, action="BUY",
                volume=result["volume"], price_eur=result["price_eur"],
                order_ids=result.get("order_ids", []),
            )
            return result

        elif action == "SELL":
            logger.info(
                f"KRAKEN LIVE SELL: {symbol} → {pair} | "
                f"Konfidenz={confidence:.1%} | Score={weighted_score:+.3f}"
            )
            result = client.sell_all(pair)
            if result:
                price = client.get_ask_price_eur(pair)
                await send_trade_confirmation(
                    symbol=symbol, action="SELL",
                    volume=result["volume"], price_eur=price,
                    order_ids=result.get("order_ids", []),
                )
            return result

    except Exception as exc:
        logger.error(f"Kraken Live Trade fehlgeschlagen [{symbol}]: {exc}")

    return None
