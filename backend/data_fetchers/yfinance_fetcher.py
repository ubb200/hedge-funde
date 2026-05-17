import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Optional


def get_asset_type(symbol: str) -> str:
    symbol_upper = symbol.upper()
    crypto_suffixes = ("-USD", "-EUR", "-USDT", "-BTC")
    if any(symbol_upper.endswith(s) for s in crypto_suffixes):
        return "crypto"
    etfs = {"SPY", "QQQ", "VTI", "VOO", "ARKK", "GLD", "TLT", "IWM", "EFA", "EEM",
            "XLK", "XLF", "XLE", "XLV", "SCHD", "JEPI", "QQQM", "SPLG"}
    if symbol_upper in etfs:
        return "etf"
    return "stock"


def get_fx_rate(currency: str = "USD") -> float:
    if currency == "CHF":
        return 1.0
    try:
        ticker = yf.Ticker(f"{currency}CHF=X")
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    # fallback rates
    fallbacks = {"USD": 0.905, "EUR": 0.975}
    return fallbacks.get(currency, 1.0)


def get_current_price(symbol: str) -> Optional[float]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _calc_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def get_technical_data(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1y")

    if hist.empty or len(hist) < 50:
        raise ValueError(f"Nicht genug historische Daten für {symbol}")

    close = hist["Close"]
    volume = hist["Volume"]

    rsi = _calc_rsi(close)
    macd_line, signal_line, histogram = _calc_macd(close)

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    atr_high = hist["High"].rolling(14).max()
    atr_low = hist["Low"].rolling(14).min()
    atr = (atr_high - atr_low).rolling(14).mean()

    price = float(close.iloc[-1])
    vol_20d_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_today = float(volume.iloc[-1])

    bb_range = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
    bb_pct = ((price - float(bb_lower.iloc[-1])) / bb_range * 100) if bb_range > 0 else 50.0

    def pct_change_n(n):
        if len(close) > n:
            return round((price / float(close.iloc[-n - 1]) - 1) * 100, 2)
        return None

    def safe(series):
        v = series.iloc[-1]
        return round(float(v), 6) if not np.isnan(v) else None

    return {
        "symbol": symbol,
        "price": round(price, 4),
        "rsi": safe(rsi),
        "macd": safe(macd_line),
        "macd_signal": safe(signal_line),
        "macd_hist": safe(histogram),
        "sma20": safe(sma20),
        "sma50": safe(sma50),
        "sma200": safe(sma200),
        "pct_vs_sma20": round((price / float(sma20.iloc[-1]) - 1) * 100, 2) if safe(sma20) else None,
        "pct_vs_sma50": round((price / float(sma50.iloc[-1]) - 1) * 100, 2) if safe(sma50) else None,
        "pct_vs_sma200": round((price / float(sma200.iloc[-1]) - 1) * 100, 2) if safe(sma200) else None,
        "bb_upper": safe(bb_upper),
        "bb_mid": safe(bb_mid),
        "bb_lower": safe(bb_lower),
        "bb_pct": round(bb_pct, 1),
        "atr": safe(atr),
        "atr_pct": round(float(atr.iloc[-1]) / price * 100, 2) if safe(atr) else None,
        "volume_ratio": round(vol_today / vol_20d_avg, 2) if vol_20d_avg > 0 else 1.0,
        "ret_5d": pct_change_n(5),
        "ret_20d": pct_change_n(20),
        "ret_60d": pct_change_n(60),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_fundamental_data(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    def safe_get(key, default=None):
        v = info.get(key)
        return v if v not in (None, "N/A", "None", float("inf")) else default

    earnings_history = []
    try:
        cal = ticker.earnings_dates
        if cal is not None and not cal.empty:
            for _, row in cal.head(4).iterrows():
                est = row.get("EPS Estimate")
                actual = row.get("Reported EPS")
                if est is not None and actual is not None:
                    try:
                        earnings_history.append({
                            "estimate": float(est),
                            "actual": float(actual),
                            "beat": float(actual) > float(est),
                        })
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass

    return {
        "symbol": symbol,
        "sector": safe_get("sector"),
        "industry": safe_get("industry"),
        "pe_trailing": safe_get("trailingPE"),
        "pe_forward": safe_get("forwardPE"),
        "peg": safe_get("pegRatio"),
        "ps_ratio": safe_get("priceToSalesTrailing12Months"),
        "pb_ratio": safe_get("priceToBook"),
        "ev_ebitda": safe_get("enterpriseToEbitda"),
        "profit_margin": safe_get("profitMargins"),
        "revenue_growth": safe_get("revenueGrowth"),
        "earnings_growth": safe_get("earningsGrowth"),
        "debt_to_equity": safe_get("debtToEquity"),
        "current_ratio": safe_get("currentRatio"),
        "market_cap": safe_get("marketCap"),
        "earnings_history": earnings_history,
        "beats_last_4": sum(1 for e in earnings_history if e.get("beat")),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_correlation_matrix(symbols: list[str]) -> dict:
    if not symbols:
        return {}
    try:
        data = yf.download(symbols, period="60d", auto_adjust=True, progress=False)["Close"]
        if isinstance(data, pd.Series):
            data = data.to_frame(name=symbols[0])
        returns = data.pct_change().dropna()
        corr = returns.corr().round(3)
        return corr.to_dict()
    except Exception:
        return {}
