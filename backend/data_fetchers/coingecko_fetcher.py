import requests
from datetime import datetime, timezone

CG_BASE = "https://api.coingecko.com/api/v3"
FG_BASE = "https://api.alternative.me/fng/"

SYMBOL_TO_ID = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "BNB-USD": "binancecoin",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "AVAX-USD": "avalanche-2",
    "LINK-USD": "chainlink",
    "DOT-USD": "polkadot",
    "MATIC-USD": "matic-network",
    "UNI-USD": "uniswap",
    "LTC-USD": "litecoin",
}


def _cg_get(path: str, params: dict = None) -> dict | list | None:
    try:
        resp = requests.get(f"{CG_BASE}{path}", params=params or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_fear_greed() -> dict:
    try:
        resp = requests.get(FG_BASE, params={"limit": 1}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [{}])[0]
        return {
            "value": int(data.get("value", 50)),
            "label": data.get("value_classification", "Neutral"),
        }
    except Exception:
        return {"value": 50, "label": "Neutral"}


def get_global_market() -> dict:
    data = _cg_get("/global")
    if not data or "data" not in data:
        return {}
    d = data["data"]
    return {
        "btc_dominance": round(d.get("market_cap_percentage", {}).get("btc", 0), 2),
        "eth_dominance": round(d.get("market_cap_percentage", {}).get("eth", 0), 2),
        "total_market_cap_usd": d.get("total_market_cap", {}).get("usd"),
        "market_cap_change_24h_pct": round(d.get("market_cap_change_percentage_24h_usd", 0), 2),
    }


def get_crypto_data(symbol: str) -> dict:
    coin_id = SYMBOL_TO_ID.get(symbol.upper())
    if not coin_id:
        return {"error": f"Kein CoinGecko-ID für {symbol} bekannt"}

    coin_data = _cg_get(f"/coins/{coin_id}", params={
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
    })

    if not coin_data:
        return {"error": "CoinGecko nicht erreichbar"}

    md = coin_data.get("market_data", {})

    def safe(d, *keys, default=None):
        v = d
        for k in keys:
            if not isinstance(v, dict):
                return default
            v = v.get(k, default)
        try:
            return round(float(v), 4) if v is not None else default
        except (TypeError, ValueError):
            return default

    price = safe(md, "current_price", "usd")
    ath = safe(md, "ath", "usd")
    from_ath = round((price / ath - 1) * 100, 2) if price and ath else None

    global_data = get_global_market()
    fear_greed = get_fear_greed()

    return {
        "symbol": symbol,
        "coin_id": coin_id,
        "price_usd": price,
        "market_cap_usd": safe(md, "market_cap", "usd"),
        "market_cap_rank": coin_data.get("market_cap_rank"),
        "volume_24h": safe(md, "total_volume", "usd"),
        "vol_mcap_ratio": round(
            safe(md, "total_volume", "usd") / safe(md, "market_cap", "usd"), 4
        ) if safe(md, "market_cap", "usd") else None,
        "change_24h": safe(md, "price_change_percentage_24h"),
        "change_7d": safe(md, "price_change_percentage_7d"),
        "change_30d": safe(md, "price_change_percentage_30d"),
        "ath_usd": ath,
        "from_ath_pct": from_ath,
        "btc_dominance": global_data.get("btc_dominance"),
        "total_mcap_change_24h": global_data.get("market_cap_change_24h_pct"),
        "fear_greed_value": fear_greed["value"],
        "fear_greed_label": fear_greed["label"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
