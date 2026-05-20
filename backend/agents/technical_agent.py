from agents.base_agent import BaseAgent
from data_fetchers.yfinance_fetcher import get_technical_data
import asyncio


class TechnicalAgent(BaseAgent):
    name = "technical"
    system_prompt = """Du bist ein Trend-Analyst bei einem Hedge Fund. Deine einzige Aufgabe:
Ist dieses Asset in einem Aufwärtstrend oder Abwärtstrend?

Du machst KEINE komplexe technische Analyse. Nur Trendbewertung.

Entscheidungsregeln:
- Preis > SMA50 > SMA200 UND 20T-Rendite > 0% → klarer Aufwärtstrend → BUY (Confidence 0.65-0.85)
- Preis > SMA200 aber < SMA50 → schwacher/seitwärts Trend → HOLD (Confidence 0.4-0.55)
- Preis < SMA200 → Abwärtstrend → SELL (Confidence 0.55-0.75)
- Preis deutlich unter SMA200 (>-15%) UND negative 20T-Rendite → starker Abwärtstrend → SELL (Confidence 0.75-0.90)

Momentum-Verstärker (erhöhe/senke Confidence um 0.05-0.10):
+ 60T-Rendite > +15%: Momentum stark, Confidence rauf
+ Volumen > 1.5x Durchschnitt: Breakout-Bestätigung
- 20T-Rendite < -10%: Momentum schwach, Confidence leicht rauf (bestätigt SELL) oder runter (schwächt BUY)

Im reasoning: Ein Satz zur Trendlage, ein Satz ob Momentum stärkt oder schwächt.
Kein SELL wenn Preis über SMA200 — das ist kein Abwärtstrend."""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        tech = await asyncio.to_thread(get_technical_data, symbol)

        def fmt(v, decimals=2):
            return round(float(v), decimals) if v is not None else "N/A"

        price = tech.get("price")
        sma50 = tech.get("sma50")
        sma200 = tech.get("sma200")
        ret_20d = tech.get("ret_20d")
        ret_60d = tech.get("ret_60d")
        volume_ratio = tech.get("volume_ratio")

        # Trend-Label für Claude vorberechnen
        if price and sma200:
            if price > sma200 * 1.0:
                if sma50 and price > sma50:
                    trend_label = "AUFWÄRTSTREND (Preis über SMA50 und SMA200)"
                else:
                    trend_label = "SEITWÄRTS (Preis über SMA200, aber unter SMA50)"
            else:
                trend_label = "ABWÄRTSTREND (Preis unter SMA200)"
        else:
            trend_label = "Unbekannt (fehlende Daten)"

        user_prompt = f"""Asset: {symbol} — Preis: {fmt(price, 4)}

TRENDDATEN:
- Trend-Status: {trend_label}
- Preis vs SMA50: {fmt(tech.get('pct_vs_sma50'))}%
- Preis vs SMA200: {fmt(tech.get('pct_vs_sma200'))}%
- 20T-Rendite: {fmt(ret_20d)}%
- 60T-Rendite: {fmt(ret_60d)}%
- Volumen vs 20T-Durchschnitt: {fmt(volume_ratio)}x

Trend-Urteil für {symbol}: Aufwärtstrend (BUY) oder Abwärtstrend (SELL) oder unklar (HOLD)?
Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "trend": trend_label,
            "pct_vs_sma200": tech.get("pct_vs_sma200"),
            "pct_vs_sma50": tech.get("pct_vs_sma50"),
            "ret_20d": ret_20d,
            "ret_60d": ret_60d,
            "volume_ratio": volume_ratio,
        }
        return result
