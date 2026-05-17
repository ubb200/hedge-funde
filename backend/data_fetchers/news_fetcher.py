import yfinance as yf
from datetime import datetime, timezone


def get_news_and_sentiment(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    result = {"fetched_at": datetime.now(timezone.utc).isoformat()}

    # --- News ---
    try:
        raw_news = ticker.news or []
        news = []
        for item in raw_news[:8]:
            content = item.get("content", {}) if isinstance(item.get("content"), dict) else {}
            title = content.get("title") or item.get("title", "")
            summary = content.get("summary") or item.get("summary", "")
            publisher = (content.get("provider", {}) or {}).get("displayName") or item.get("publisher", "")
            if title:
                news.append({
                    "title": title[:200],
                    "publisher": publisher,
                    "summary": summary[:300] if summary else "",
                })
        result["news"] = news
    except Exception as e:
        result["news"] = []
        result["news_error"] = str(e)

    # --- Analystenempfehlungen ---
    try:
        recs = ticker.recommendations
        if recs is not None and not recs.empty:
            latest = recs.tail(4)
            rec_list = []
            for _, row in latest.iterrows():
                rec_list.append({
                    "period": str(row.get("period", "")),
                    "strongBuy": int(row.get("strongBuy", 0)),
                    "buy": int(row.get("buy", 0)),
                    "hold": int(row.get("hold", 0)),
                    "sell": int(row.get("sell", 0)),
                    "strongSell": int(row.get("strongSell", 0)),
                })
            result["analyst_recommendations"] = rec_list
        else:
            result["analyst_recommendations"] = []
    except Exception:
        result["analyst_recommendations"] = []

    # --- Insider-Transaktionen ---
    try:
        insiders = ticker.insider_transactions
        if insiders is not None and not insiders.empty:
            insider_list = []
            for _, row in insiders.head(6).iterrows():
                insider_list.append({
                    "insider": str(row.get("Insider", row.get("insider", ""))),
                    "relation": str(row.get("Relation", row.get("relation", ""))),
                    "transaction": str(row.get("Transaction", row.get("transaction", ""))),
                    "shares": str(row.get("Shares", row.get("shares", ""))),
                    "value": str(row.get("Value", row.get("value", ""))),
                })
            result["insider_transactions"] = insider_list
        else:
            result["insider_transactions"] = []
    except Exception:
        result["insider_transactions"] = []

    return result
