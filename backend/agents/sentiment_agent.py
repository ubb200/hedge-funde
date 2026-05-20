from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.news_fetcher import get_news_and_sentiment
import asyncio


class SentimentAgent(BaseAgent):
    name = "sentiment"
    system_prompt = """Du bist ein Nachrichten- und Thematic-Sentiment-Analyst bei einem Hedge Fund.
Du analysierst aktuelle Nachrichten auf zwei Ebenen:

EBENE 1 — THEMATIC MOMENTUM (wichtiger):
Zeigen die News, dass das Unternehmen von einem globalen Megatrend profitiert?
- Neue KI-Verträge, Rechenzentrum-Deals, GPU-Nachfrage → KI-Megatrend
- Kernkraft-Genehmigungen, Uran-Verträge, Reaktor-Aufträge → Kernenergie-Trend
- Rüstungsaufträge, Regierungsverträge, Verteidigungsbudgets → Rüstungstrend
- Insider kaufen MASSIV nach einem Rücksetzer → Management glaubt an Trend
- Analysten-Upgrades wegen eines strukturellen Themas → bullisch
- Nachrichten zeigen Gegenwind durch Regulierung/Zölle/Konkurrenz → bärisch

EBENE 2 — UNTERNEHMENS-QUALITÄT:
- CEO-Rücktritt / Führungskrise → stark negativ
- Bilanzskandale, Betrug, Kartellverfahren → stark negativ
- Produktlaunch, Übernahmen, Partnerschaften → positiv

Regeln:
- Keine News = HOLD mit Confidence 0.2
- ETFs: nur Sektor-Sentiment beurteilen (Confidence max 0.4)
- Sei KONKRET: nenne die wichtigste Schlagzeile und den Megatrend-Bezug
- Wenn News klar auf einen heissen Trend hinweisen → Confidence 0.7-0.85, klares BUY/SELL"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        if asset_type == "etf":
            skip = SKIP_SIGNAL.copy()
            skip["reasoning"] = "ETFs haben keine Unternehmens-News oder Insider-Transaktionen."
            skip["confidence"] = 0.1
            return skip

        data = await asyncio.to_thread(get_news_and_sentiment, symbol)

        news = data.get("news", [])
        recs = data.get("analyst_recommendations", [])
        insiders = data.get("insider_transactions", [])

        # News formatieren
        if news:
            news_text = "\n".join(
                f"- [{item['publisher']}] {item['title']}"
                + (f"\n  {item['summary']}" if item.get("summary") else "")
                for item in news
            )
        else:
            news_text = "Keine aktuellen News gefunden."

        # Analysten formatieren
        if recs:
            latest_rec = recs[-1]
            total = sum([latest_rec.get(k, 0) for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]])
            bullish = latest_rec.get("strongBuy", 0) + latest_rec.get("buy", 0)
            bearish = latest_rec.get("sell", 0) + latest_rec.get("strongSell", 0)
            rec_text = (
                f"Aktuell ({latest_rec.get('period', '?')}): "
                f"{bullish} bullisch / {latest_rec.get('hold', 0)} neutral / {bearish} bärisch "
                f"(von {total} Analysten)"
            )
        else:
            rec_text = "Keine Analystenempfehlungen verfügbar."

        # Insider formatieren
        if insiders:
            insider_text = "\n".join(
                f"- {i.get('insider', '?')} ({i.get('relation', '?')}): "
                f"{i.get('transaction', '?')} — {i.get('shares', '?')} Aktien"
                for i in insiders
            )
        else:
            insider_text = "Keine Insider-Transaktionen verfügbar."

        user_prompt = f"""Asset: {symbol} (Typ: {asset_type})

AKTUELLE NEWS:
{news_text}

ANALYSTENEMPFEHLUNGEN:
{rec_text}

INSIDER-TRANSAKTIONEN (letzte 6):
{insider_text}

Bewerte das Sentiment für {symbol}:
1. Welchem globalen Megatrend (KI, Kernenergie, Rüstung, Rohstoffe, Biotech, etc.) ist das Asset zuzuordnen?
2. Unterstützen die News diesen Trend oder widersprechen sie ihm?
3. Unternehmens-Qualitätssignale (Führung, Risiken, Entwicklungen)?
4. Finales Urteil: BUY / HOLD / SELL

Antworte nur mit JSON. Nenne konkret die wichtigste Schlagzeile und den Megatrend-Bezug."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "news_count": len(news),
            "analyst_bullish": (recs[-1].get("strongBuy", 0) + recs[-1].get("buy", 0)) if recs else None,
            "analyst_bearish": (recs[-1].get("sell", 0) + recs[-1].get("strongSell", 0)) if recs else None,
            "insider_transactions": len(insiders),
            "top_headline": news[0]["title"] if news else None,
        }
        return result
