import asyncio
import logging
from typing import Optional

import pandas as pd
import yfinance as yf

from universe import ALL_SYMBOLS

logger = logging.getLogger(__name__)


def _calc_rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-10)
    return float((100 - (100 / (1 + rs))).iloc[-1])


def _calc_ema(series: pd.Series, period: int) -> float:
    if len(series) < period:
        return float(series.iloc[-1]) if len(series) > 0 else 0.0
    return float(series.ewm(span=period, adjust=False).mean().iloc[-1])


def _score_symbol(close: pd.Series, volume: Optional[pd.Series]) -> tuple[float, str]:
    if len(close) < 20:
        return 0.0, "Zu wenig Daten"

    score = 0.0
    reasons: list[str] = []
    bullish = 0
    bearish = 0

    current = float(close.iloc[-1])

    # --- RSI ---
    rsi = _calc_rsi(close)
    if rsi < 35:
        score += (35 - rsi) / 35 * 0.40
        reasons.append(f"RSI oversold {rsi:.0f}")
        bullish += 1
    elif rsi > 65:
        score -= (rsi - 65) / 35 * 0.40
        reasons.append(f"RSI overbought {rsi:.0f}")
        bearish += 1

    # --- EMA-Trend (20 vs 50) ---
    ema20 = _calc_ema(close, 20)
    ema50 = _calc_ema(close, 50)
    if ema20 > ema50 and current > ema20:
        score += 0.20
        reasons.append("EMA Aufwärtstrend")
        bullish += 1
    elif ema20 < ema50 and current < ema20:
        score -= 0.20
        reasons.append("EMA Abwärtstrend")
        bearish += 1

    # --- 5-Tage-Momentum ---
    if len(close) >= 6:
        ret_5d = (current / float(close.iloc[-6]) - 1) * 100
        if abs(ret_5d) > 2:
            score += ret_5d / 20
            reasons.append(f"{ret_5d:+.1f}% (5d)")
            bullish += 1 if ret_5d > 0 else 0
            bearish += 1 if ret_5d < 0 else 0

    # --- 20-Tage-Momentum ---
    if len(close) >= 21:
        ret_20d = (current / float(close.iloc[-21]) - 1) * 100
        if abs(ret_20d) > 5:
            score += ret_20d / 60

    # --- SMA200 Marktregime ---
    if len(close) >= 200:
        sma200 = float(close.iloc[-200:].mean())
        pct_vs_sma200 = (current / sma200 - 1) * 100
        if pct_vs_sma200 > 5:
            score += 0.10
            bullish += 1
        elif pct_vs_sma200 < -5:
            score -= 0.10
            bearish += 1

    # --- Volume-Bestätigung ---
    if volume is not None and len(volume) >= 21 and volume.iloc[-1] > 0:
        vol_avg = float(volume.iloc[-21:-1].mean())
        if vol_avg > 0:
            vol_ratio = float(volume.iloc[-1]) / vol_avg
            if vol_ratio > 2.0:
                score += 0.15 if score >= 0 else -0.15
                reasons.append(f"Vol {vol_ratio:.1f}x")

    # --- 52-Wochen-Hoch / -Tief ---
    lookback = min(252, len(close))
    if lookback >= 50:
        period_slice = close.iloc[-lookback:]
        high52 = float(period_slice.max())
        low52 = float(period_slice.min())
        if current >= high52 * 0.97:
            score += 0.15
            reasons.append("~52w Hoch")
            bullish += 1
        elif current <= low52 * 1.03:
            score -= 0.15
            reasons.append("~52w Tief")
            bearish += 1

    # --- Confluence Bonus: mehrere Signale stimmen überein ---
    if bullish >= 3:
        score += 0.15
        reasons.append(f"Confluence ({bullish} bullisch)")
    elif bearish >= 3:
        score -= 0.15
        reasons.append(f"Confluence ({bearish} bärisch)")

    return score, " | ".join(reasons) if reasons else "Neutral"


async def run_screener(top_n: int = 25) -> list[dict]:
    """Scannt ~200 Symbole per Batch-Download, gibt Top N nach Interest-Score zurück."""
    symbols = ALL_SYMBOLS
    logger.info(f"Screener: {len(symbols)} Symbole werden geladen...")

    loop = asyncio.get_event_loop()

    def _download() -> pd.DataFrame:
        return yf.download(
            symbols,
            period="6mo",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

    try:
        data = await loop.run_in_executor(None, _download)
    except Exception as e:
        logger.error(f"Screener-Download fehlgeschlagen: {e}")
        return []

    if data.empty:
        logger.warning("Screener: leeres DataFrame")
        return []

    if isinstance(data.columns, pd.MultiIndex):
        close_all: pd.DataFrame = data["Close"]
        volume_all: pd.DataFrame = data["Volume"] if "Volume" in data.columns.get_level_values(0) else pd.DataFrame()
    else:
        logger.warning("Screener: unerwartetes DataFrame-Format")
        return []

    results: list[dict] = []

    for symbol in symbols:
        try:
            if symbol not in close_all.columns:
                continue
            close = close_all[symbol].dropna()
            volume = volume_all[symbol].dropna() if symbol in volume_all.columns else None

            if len(close) < 20:
                continue

            score, reason = _score_symbol(close, volume)

            if abs(score) < 0.05:
                continue

            results.append({
                "symbol": symbol,
                "score": round(score, 4),
                "reason": reason,
                "price": round(float(close.iloc[-1]), 4),
                "direction": "BUY" if score > 0 else "SELL",
            })
        except Exception as e:
            logger.debug(f"Screener überspringe {symbol}: {e}")
            continue

    results.sort(key=lambda x: abs(x["score"]), reverse=True)
    logger.info(
        f"Screener: {len(results)} interessante Symbole, "
        f"Top {min(top_n, len(results))} für Claude-Analyse"
    )
    return results[:top_n]
