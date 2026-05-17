import requests
from datetime import datetime, timezone
from config import FRED_API_KEY

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES = {
    "fedfunds": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "dgs10": "DGS10",
    "dgs2": "DGS2",
    "unrate": "UNRATE",
    "gdp_growth": "A191RL1Q225SBEA",
}


def _fetch_series(series_id: str, limit: int = 6) -> list[dict]:
    if not FRED_API_KEY or "HIER" in FRED_API_KEY:
        return []
    try:
        resp = requests.get(
            FRED_BASE,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "limit": limit,
                "sort_order": "desc",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("observations", [])
    except Exception:
        return []


def _latest_value(obs: list[dict]) -> float | None:
    for o in obs:
        try:
            v = float(o["value"])
            return v
        except (ValueError, KeyError):
            continue
    return None


def _trend(obs: list[dict], n: int = 3) -> str:
    values = []
    for o in obs[:n]:
        try:
            values.append(float(o["value"]))
        except (ValueError, KeyError):
            pass
    if len(values) < 2:
        return "unknown"
    if values[0] > values[-1]:
        return "rising"
    elif values[0] < values[-1]:
        return "falling"
    return "stable"


def get_macro_data() -> dict:
    data = {}
    for key, series_id in SERIES.items():
        obs = _fetch_series(series_id, limit=6)
        data[key] = _latest_value(obs)
        data[f"{key}_trend"] = _trend(obs)

    fedfunds_obs = _fetch_series("FEDFUNDS", limit=6)
    trend = _trend(fedfunds_obs)
    if trend == "rising":
        data["fed_policy"] = "hiking"
    elif trend == "falling":
        data["fed_policy"] = "cutting"
    else:
        data["fed_policy"] = "paused"

    dgs10 = data.get("dgs10")
    dgs2 = data.get("dgs2")
    if dgs10 is not None and dgs2 is not None:
        data["yield_spread"] = round(dgs10 - dgs2, 3)
        data["yield_curve_inverted"] = dgs10 < dgs2
    else:
        data["yield_spread"] = None
        data["yield_curve_inverted"] = None

    data["fetched_at"] = datetime.now(timezone.utc).isoformat()
    data["available"] = FRED_API_KEY and "HIER" not in FRED_API_KEY
    return data
