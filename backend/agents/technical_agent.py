from agents.base_agent import BaseAgent
from data_fetchers.yfinance_fetcher import get_technical_data
import asyncio


class TechnicalAgent(BaseAgent):
    name = "technical"
    system_prompt = """Du bist ein technischer Analyst bei einem quantitativen Hedge Fund.
Du interpretierst berechnete Indikatoren — du rechnest nie selbst, das wurde vorgelagert gemacht.
Deine Aufgabe: die wichtigsten Muster-Signale identifizieren und zu einem klaren Richtungs-Urteil kombinieren.

Regeln:
- Preis über SMA200 = langfristiger Bulle; darunter = Bär — das ist deine Grundhaltung
- Confluence ist entscheidend: RSI bullisch + MACD bullisch + Preis über SMA50 = starkes BUY-Signal
- RSI unter 35 UND Preis nahe 52-Wochen-Tief = potenzielle Trendwende, aber nur mit Volume-Bestätigung
- MACD-Histogramm wächst = Momentum aufbaut sich; schrumpft = nachlässt
- Bollinger-Band-Kompression (enge Bands) gefolgt von Ausbruch = hohe Confidence
- ATR über 3% des Preises = erhöhte Volatilität → reduziere Confidence leicht
- Entscheide KLAR: bei guten Confluences BUY oder SELL mit Confidence >0.6, nicht immer HOLD"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        tech = await asyncio.to_thread(get_technical_data, symbol)

        def fmt(v, decimals=2):
            return round(float(v), decimals) if v is not None else "N/A"

        rsi = tech.get("rsi")
        rsi_label = "überverkauft" if rsi and rsi < 30 else ("überkauft" if rsi and rsi > 70 else "neutral")

        macd_hist = tech.get("macd_hist")
        macd_label = "bullisch" if macd_hist and macd_hist > 0 else "bärisch"

        user_prompt = f"""Asset: {symbol} — Aktueller Preis: {fmt(tech.get('price'), 4)}
Analysezeitraum: letzte 252 Handelstage

TECHNISCHE INDIKATOREN (vorberechnet):
- RSI(14): {fmt(rsi)} [{rsi_label}]
- MACD-Linie: {fmt(tech.get('macd'), 4)}, Signal: {fmt(tech.get('macd_signal'), 4)}, Histogramm: {fmt(macd_hist, 4)} [{macd_label}]
- SMA20: {fmt(tech.get('sma20'), 4)} | SMA50: {fmt(tech.get('sma50'), 4)} | SMA200: {fmt(tech.get('sma200'), 4)}
- Preis vs SMA20: {fmt(tech.get('pct_vs_sma20'))}% | vs SMA50: {fmt(tech.get('pct_vs_sma50'))}% | vs SMA200: {fmt(tech.get('pct_vs_sma200'))}%
- Bollinger Upper: {fmt(tech.get('bb_upper'), 4)} | Mid: {fmt(tech.get('bb_mid'), 4)} | Lower: {fmt(tech.get('bb_lower'), 4)}
- Preis-Position in BB: {fmt(tech.get('bb_pct'), 1)}% (0=unteres Band, 100=oberes Band)
- ATR(14): {fmt(tech.get('atr'), 4)} ({fmt(tech.get('atr_pct'))}% des Preises = aktuelle Volatilität)
- Volumen heute vs 20T-Durchschnitt: {fmt(tech.get('volume_ratio'))}x

Preisbewegung:
- 5T-Rendite: {fmt(tech.get('ret_5d'))}% | 20T-Rendite: {fmt(tech.get('ret_20d'))}% | 60T-Rendite: {fmt(tech.get('ret_60d'))}%

Technisches Urteil für {symbol}? Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "rsi": rsi,
            "macd_hist": macd_hist,
            "pct_vs_sma200": tech.get("pct_vs_sma200"),
            "bb_pct": tech.get("bb_pct"),
            "volume_ratio": tech.get("volume_ratio"),
            "ret_20d": tech.get("ret_20d"),
        }
        return result
