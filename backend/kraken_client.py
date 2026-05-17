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

# yfinance-Symbol → Kraken-Tradingpair (in EUR)
SYMBOL_TO_PAIR: dict[str, str] = {
    "BTC-USD":   "XBTEUR",
    "ETH-USD":   "XETHZEUR",
    "SOL-USD":   "SOLEUR",
    "XRP-USD":   "XXRPZEUR",
    "ADA-USD":   "ADAEUR",
    "DOGE-USD":  "XDGZEUR",
    "LINK-USD":  "LINKEUR",
    "DOT-USD":   "DOTEUR",
    "AVAX-USD":  "AVAXEUR",
    "LTC-USD":   "XLTCZEUR",
    "ATOM-USD":  "ATOMEUR",
    "MATIC-USD": "MATICEUR",
}

# Kraken-Asset-Name für Balance-Abfrage
PAIR_TO_ASSET: dict[str, str] = {
    "XBTEUR":   "XXBT",
    "XETHZEUR": "XETH",
    "SOLEUR":   "SOL",
    "XXRPZEUR": "XXRP",
    "ADAEUR":   "ADA",
    "XDGZEUR":  "XXDG",
    "LINKEUR":  "LINK",
    "DOTEUR":   "DOT",
    "AVAXEUR":  "AVAX",
    "XLTCZEUR": "XLTC",
    "ATOMEUR":  "ATOM",
    "MATICEUR": "MATIC",
}

# Minimale Ordervolumina (Kraken-Anforderung)
MIN_VOLUME: dict[str, float] = {
    "XBTEUR":   0.0001,
    "XETHZEUR": 0.01,
    "SOLEUR":   0.5,
    "XXRPZEUR": 10.0,
    "ADAEUR":   15.0,
    "XDGZEUR":  50.0,
    "LINKEUR":  0.5,
    "DOTEUR":   0.5,
    "AVAXEUR":  0.2,
    "XLTCZEUR": 0.1,
    "ATOMEUR":  0.5,
    "MATICEUR": 10.0,
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


def execute_live_trade(
    symbol: str,
    action: str,
    confidence: float,
    weighted_score: float,
    size_eur: float,
) -> dict | None:
    """
    Führt einen echten Kraken-Trade durch — nur bei sehr guter Analyse.
    Gibt None zurück wenn deaktiviert, Symbol nicht unterstützt, oder Fehler.
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

    client = get_client()
    if not client:
        return None

    try:
        if action == "BUY":
            logger.info(
                f"KRAKEN LIVE BUY: {symbol} → {pair} | "
                f"EUR {size_eur:.2f} | Konfidenz={confidence:.1%} | Score={weighted_score:+.3f}"
            )
            return client.buy(pair, size_eur)

        elif action == "SELL":
            logger.info(
                f"KRAKEN LIVE SELL: {symbol} → {pair} | "
                f"Konfidenz={confidence:.1%} | Score={weighted_score:+.3f}"
            )
            return client.sell_all(pair)

    except Exception as exc:
        logger.error(f"Kraken Live Trade fehlgeschlagen [{symbol}]: {exc}")

    return None
