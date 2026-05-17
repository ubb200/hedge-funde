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
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def _score_symbol(close: pd.Series, volume: Optional[pd.Series]) -> tuple[float, str]:
    if len(close) < 20:
        return 0.0, "Zu wenig Daten"

    score = 0.0
    reasons: list[str] = []

    # RSI
    rsi = _calc_rsi(close)
    if rsi < 30:
        score += (30 - rsi) / 30 * 0.5
        reasons.append(f"RSI oversold {rsi:.0f}")
    elif rsi > 70:
        score -= (rsi - 70) / 30 * 0.5
        reasons.append(f"RSI overbought {rsi:.0f}")

    # Volume spike (letzter Tag vs 20-Tage-Durchschnitt)
    if volume is not None and len(volume) >= 21 and volume.iloc[-1] > 0:
        vol_avg = float(volume.iloc[-21:-1].mean())
        if vol_avg > 0:
            vol_ratio = float(volume.iloc[-1]) / vol_avg
            if vol_ratio > 2.5:
                score += 0.2 if score >= 0 else -0.2
                reasons.append(f"Vol {vol_ratio:.1f}x")

    # 5-Tage-Momentum
    if len(close) >= 6:
        ret_5d = (float(close.iloc[-1]) / float(close.iloc[-6]) - 1) * 100
        if abs(ret_5d) > 3:
            score += ret_5d / 25
            reasons.append(f"{ret_5d:+.1f}% (5d)")

    # 20-Tage-Momentum
    if len(close) >= 21:
        ret_20d = (float(close.iloc[-1]) / float(close.iloc[-21]) - 1) * 100
        if abs(ret_20d) > 8:
            score += ret_20d / 80

    # Abstand SMA50
    if len(close) >= 50:
        sma50 = float(close.iloc[-50:].mean())
        pct_vs_sma50 = (float(close.iloc[-1]) / sma50 - 1) * 100
        if abs(pct_vs_sma50) > 10:
            score += pct_vs_sma50 / 150

    # 52-Wochen-Hoch / -Tief
    lookback = min(252, len(close))
    if lookback >= 50:
        period_slice = close.iloc[-lookback:]
        high = float(period_slice.max())
        low = float(period_slice.min())
        current = float(close.iloc[-1])
        if current >= high * 0.98:
            score += 0.15
            reasons.append("~52w Hoch")
        elif current <= low * 1.02:
            score -= 0.15
            reasons.append("~52w Tief")

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

    # Spalten extrahieren (MultiIndex bei mehreren Symbolen)
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
