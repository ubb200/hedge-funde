from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.fred_fetcher import get_macro_data
import asyncio


class MacroAgent(BaseAgent):
    name = "macro"
    system_prompt = """Du bist ein Makroökonom und Hedge-Fund-Analyst.
Deine Aufgabe ist es zu beurteilen, ob das aktuelle Makro-Umfeld für ein bestimmtes Asset günstig oder ungünstig ist.
Du analysierst FRED-Daten: Fed-Politik, Inflation, Zinskurve, Arbeitslosigkeit und BIP-Wachstum.

Regeln:
- HOLD ist oft die richtige Antwort — zwinge keine Meinung
- Confidence unter 0.4 bedeutet echte Unsicherheit — nutze sie ehrlich
- Erfinde keine Zahlen; verwende nur die gegebenen Daten
- Krypto reagiert stark auf Liquiditätsbedingungen und Dollar-Stärke
- Zinssensitive Assets (Long-Duration-Bonds, Growth-Aktien) leiden bei Zinserhöhungen
- Eine invertierte Zinskurve ist ein Rezessionssignal"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        macro = await asyncio.to_thread(get_macro_data)

        if not macro.get("available"):
            skip = SKIP_SIGNAL.copy()
            skip["reasoning"] = "Kein FRED API Key konfiguriert. Makro-Analyse übersprungen."
            skip["key_metrics"] = {}
            return skip

        def fmt(v, suffix=""):
            return f"{v}{suffix}" if v is not None else "N/A"

        inverted_note = " (INVERTIERT — Rezessionssignal)" if macro.get("yield_curve_inverted") else ""

        user_prompt = f"""Asset: {symbol} (Typ: {asset_type})
Datum: {macro.get('fetched_at', 'N/A')[:10]}

MAKRO-DATEN (FRED):
- Fed Funds Rate: {fmt(macro.get('fedfunds'), '%')}
- CPI YoY: {fmt(macro.get('cpi'), '%')} (Trend: {macro.get('cpi_trend', 'N/A')})
- 10J Treasury: {fmt(macro.get('dgs10'), '%')}
- 2J Treasury: {fmt(macro.get('dgs2'), '%')}
- Zinskurve (10J-2J): {fmt(macro.get('yield_spread'), '%')}{inverted_note}
- Arbeitslosigkeit: {fmt(macro.get('unrate'), '%')} (Trend: {macro.get('unrate_trend', 'N/A')})
- BIP-Wachstum QoQ annualisiert: {fmt(macro.get('gdp_growth'), '%')}

Fed-Politik (letzte 6 Monate): {macro.get('fed_policy', 'N/A')}

Beurteile auf Basis dieses Makro-Regimes: Soll man {symbol} KAUFEN, VERKAUFEN oder HALTEN?
Antworte nur mit dem JSON-Schema."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "fed_funds_rate": macro.get("fedfunds"),
            "cpi": macro.get("cpi"),
            "yield_spread": macro.get("yield_spread"),
            "yield_curve_inverted": macro.get("yield_curve_inverted"),
            "fed_policy": macro.get("fed_policy"),
        }
        return result
