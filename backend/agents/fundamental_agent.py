from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.yfinance_fetcher import get_fundamental_data
import asyncio


class FundamentalAgent(BaseAgent):
    name = "fundamental"
    system_prompt = """Du bist ein fundamentaler Aktienanalyst bei einem Hedge Fund.
Du bewertest Aktien und ETFs anhand von Bewertung, Wachstumsqualität und Bilanzgesundheit.
Du analysierst KEIN Krypto.

Regeln:
- Bewertung allein ist kein Signal; Wachstum muss die Multiples rechtfertigen
- PEG unter 1.0 = möglicherweise unterbewertet; PEG über 2.5 = teuer
- Earnings-Beats in 3/4 oder 4/4 Quartalen = starkes Qualitätssignal → erhöht BUY-Confidence
- Debt/Equity über 2.0 = Warnsignal; unter 0.5 = starke Bilanz
- Nettomarge über 20% + Umsatzwachstum über 15% = Quality-Growth = BUY-Bias
- ETFs: gib HOLD mit Confidence 0.1 und erkläre kurz warum keine Fundamentaldaten
- Sei entscheidungsfreudig: bei klaren Daten BUY oder SELL, nicht immer HOLD"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        if asset_type == "crypto":
            skip = SKIP_SIGNAL.copy()
            skip["reasoning"] = "Fundamentalanalyse gilt nicht für Krypto-Assets. Weiter an den Krypto-Spezialisten."
            return skip

        fund = await asyncio.to_thread(get_fundamental_data, symbol)

        def fmt(v, suffix="", pct=False):
            if v is None:
                return "N/A"
            if pct:
                return f"{round(v * 100, 1)}%"
            return f"{round(float(v), 2)}{suffix}"

        beats = fund.get("beats_last_4", 0)
        total_q = len(fund.get("earnings_history", []))
        beat_str = f"{beats}/{total_q} Quartale" if total_q > 0 else "keine Daten"

        user_prompt = f"""Asset: {symbol} (Typ: {asset_type})
Sektor: {fund.get('sector', 'N/A')} | Branche: {fund.get('industry', 'N/A')}

BEWERTUNGS-KENNZAHLEN:
- KGV (trailing): {fmt(fund.get('pe_trailing'))}
- KGV (forward): {fmt(fund.get('pe_forward'))}
- PEG-Ratio: {fmt(fund.get('peg'))}
- KUV: {fmt(fund.get('ps_ratio'))}
- KBV: {fmt(fund.get('pb_ratio'))}
- EV/EBITDA: {fmt(fund.get('ev_ebitda'))}

WACHSTUM & PROFITABILITÄT:
- Umsatzwachstum: {fmt(fund.get('revenue_growth'), pct=True)}
- Gewinnwachstum: {fmt(fund.get('earnings_growth'), pct=True)}
- Nettomarge: {fmt(fund.get('profit_margin'), pct=True)}

BILANZ:
- Debt/Equity: {fmt(fund.get('debt_to_equity'))}
- Current Ratio: {fmt(fund.get('current_ratio'))}

EARNINGS-HISTORY (letzte 4 Quartale):
- Übertroffen: {beat_str}

Fundamentales Urteil für {symbol}? Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "pe_forward": fund.get("pe_forward"),
            "pe_trailing": fund.get("pe_trailing"),
            "peg": fund.get("peg"),
            "revenue_growth": fund.get("revenue_growth"),
            "earnings_beats": f"{beats}/{total_q}",
            "debt_to_equity": fund.get("debt_to_equity"),
        }
        return result
