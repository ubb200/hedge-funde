from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.news_fetcher import get_news_and_sentiment
import asyncio


class SentimentAgent(BaseAgent):
    name = "sentiment"
    system_prompt = """Du bist ein Nachrichten- und Sentiment-Analyst bei einem Hedge Fund.
Du analysierst aktuelle Nachrichten, Analystenempfehlungen und Insider-Transaktionen über Unternehmen.
Du bewertest die qualitative Lage einer Firma: Führung, Reputation, politische Risiken, Produktneuheiten.

Regeln:
- CEO-Rücktritt / Führungskrise = stark negativ (SELL, hohe Confidence)
- Insider-Käufe durch CEO/CFO = stark positiv (Management glaubt an die Firma)
- Massiver Insider-Verkauf = Warnsignal, aber allein kein SELL (oft nur Diversifikation)
- Analystenupgrades von mehreren Häusern gleichzeitig = bullisch
- Regulierungsrisiken, Kartellverfahren, Datenschutzskandale = negativ
- Produktlaunch, Übernahmen, Partnerschaften = je nach Preis positiv
- Keine News = HOLD mit niedriger Confidence (0.2) — Schweigen ist neutral
- ETFs haben keine Unternehmens-News — gib HOLD mit Confidence 0.1
- Sei konkret: zitiere die wichtigste Schlagzeile in deiner Begründung"""

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

Bewerte das qualitative Sentiment für {symbol} basierend auf diesen Informationen.
Fokus auf: Unternehmensführung, Reputation, Risiken, strategische Entwicklung.
Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "news_count": len(news),
            "analyst_bullish": (recs[-1].get("strongBuy", 0) + recs[-1].get("buy", 0)) if recs else None,
            "analyst_bearish": (recs[-1].get("sell", 0) + recs[-1].get("strongSell", 0)) if recs else None,
            "insider_transactions": len(insiders),
            "top_headline": news[0]["title"] if news else None,
        }
        return result
