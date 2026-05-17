from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.coingecko_fetcher import get_crypto_data
import asyncio


class CryptoAgent(BaseAgent):
    name = "crypto"
    system_prompt = """Du bist ein Krypto-Marktanalyst spezialisiert auf On-Chain-Metriken und krypto-spezifische Marktdynamik.
Du verstehst, dass Krypto-Märkte durch andere Kräfte getrieben werden als Aktien: Liquiditätszyklen, BTC-Dominanz-Verschiebungen, Sentiment-Extreme und On-Chain-Akkumulationsmuster.

Regeln:
- Steigende BTC-Dominanz = Alts underperformen BTC; favorisiere BTC gegenüber Altcoins
- Fear & Greed extreme Angst (<20) ist historisch eine Akkumulationszone
- Extreme Gier (>80) deutet auf Vorsicht hin, aber nicht unbedingt auf Exit
- Entfernung vom Allzeithoch ist wichtig für Momentum und psychologische Widerstände
- Vol/Market-Cap-Ratio über 0.1 bedeutet hohe Aktivität/Aufmerksamkeit"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        if asset_type != "crypto":
            skip = SKIP_SIGNAL.copy()
            skip["reasoning"] = "Krypto-Analyse gilt nicht für Aktien/ETFs. Weiter an den Fundamentalanalysten."
            return skip

        crypto = await asyncio.to_thread(get_crypto_data, symbol)

        if "error" in crypto:
            skip = SKIP_SIGNAL.copy()
            skip["reasoning"] = f"Krypto-Daten nicht verfügbar: {crypto['error']}"
            return skip

        def fmt(v, suffix=""):
            return f"{v}{suffix}" if v is not None else "N/A"

        user_prompt = f"""Asset: {symbol} (Krypto)
Datum: {crypto.get('fetched_at', 'N/A')[:10]}

KRYPTO-MARKTDATEN:
- Aktueller Preis: ${fmt(crypto.get('price_usd'))}
- 24h-Änderung: {fmt(crypto.get('change_24h'))}%
- Market Cap: ${fmt(crypto.get('market_cap_usd'))} | Rang: #{fmt(crypto.get('market_cap_rank'))}
- Vol/Market-Cap-Ratio: {fmt(crypto.get('vol_mcap_ratio'))} (>0.1 = hohe Aktivität)
- Vom Allzeithoch: {fmt(crypto.get('from_ath_pct'))}%
- 7T-Änderung: {fmt(crypto.get('change_7d'))}% | 30T-Änderung: {fmt(crypto.get('change_30d'))}%

MARKT-SENTIMENT:
- Fear & Greed Index: {fmt(crypto.get('fear_greed_value'))}/100 ({fmt(crypto.get('fear_greed_label'))})
- BTC-Dominanz: {fmt(crypto.get('btc_dominance'))}%
- Gesamt-Krypto-Marktänderung 24h: {fmt(crypto.get('total_mcap_change_24h'))}%

Krypto-Urteil für {symbol}? Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "price_usd": crypto.get("price_usd"),
            "fear_greed": crypto.get("fear_greed_value"),
            "fear_greed_label": crypto.get("fear_greed_label"),
            "btc_dominance": crypto.get("btc_dominance"),
            "from_ath_pct": crypto.get("from_ath_pct"),
            "change_30d": crypto.get("change_30d"),
        }
        return result
