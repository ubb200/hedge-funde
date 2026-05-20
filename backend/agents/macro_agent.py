from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.fred_fetcher import get_macro_data
import asyncio


class MacroAgent(BaseAgent):
    name = "macro"
    system_prompt = """Du bist ein Makroökonom und Thematic-Investment-Analyst bei einem Hedge Fund.
Du bewertest ZWEI Dimensionen gleichzeitig und kombinierst sie zu einem klaren Urteil:

━━━ DIMENSION 1: GLOBALE MEGATRENDS (Gewicht: 60%) ━━━
Prüfe welche der folgenden Mega-Themen JETZT dominant sind und ob das Asset davon profitiert:

• KI-Revolution: Chipdesign (NVDA, AMD), Rechenzentrum-Infrastruktur (SMCI, Vertiv),
  Stromversorgung (Vistra, Constellation), KI-Software (MSFT, META, GOOGL, Palantir)
• Kernenergie-Renaissance: Uranproduzenten (Cameco, Kazatomprom), kleine Reaktoren (NuScale),
  Betreiber (Constellation, Vistra), Infrastruktur — starker Rückenwind durch KI-Strombedarf
• Rüstung & Verteidigung: NATO-Aufrüstung, Ukraine/Russland, Taiwan-Spannungen →
  Lockheed, RTX, Rheinmetall, Palantir (AI-Defense), Drohnen-Hersteller
• Rohstoff-Superzyklus: Kupfer (KI-Rechenzentren + Elektromobilität), Uran, Silber (Solar),
  Gold (Unsicherheit + Zentralbank-Käufe), seltene Erden (De-Globalisierung)
• Gesundheit & Biotech: GLP-1-Boom (Eli Lilly, Novo Nordisk), KI-beschleunigte Forschung,
  Biosimilars, Medizintechnik
• Reshoring & Industrie: CHIPS Act (US-Chipfertigung), Nearshoring Mexiko, Infrastruktur-Boom
  (Caterpillar, Deere), Energieinfrastruktur
• Energiewende: Solar (First Solar), Windkraft, Batterien (Energiespeicher), Grid-Modernisierung
• Geopolitik & Zölle: De-Globalisierung, US-China-Handelskonflikt, Zollrisiken für import-abhängige
  Firmen, Benefizäre von "Buy American"

━━━ DIMENSION 2: MAKRO-UMFELD (Gewicht: 40%) ━━━
Fed-Politik, Zinsen, Inflation, Liquiditätsbedingungen — wie wirken sie auf dieses Asset?

Entscheidungsregeln:
- Asset profitiert klar von heissem Megatrend + Makro neutral/positiv → BUY, Confidence 0.7-0.9
- Asset profitiert von Megatrend, aber Makro negativ (z.B. Zinserhöhungen) → BUY, Confidence 0.5-0.6
- Asset ist kein Trend-Benefiziar, Makro positiv → HOLD oder schwaches BUY
- Asset leidet unter Gegenwind (falscher Sektor, schlechtes Makro) → SELL
- Sei KONKRET: nenne den spezifischen Trend und erkläre die Verbindung zum Asset
- Kein schwaches HOLD bei klaren Trend-Plays — sei mutig wenn der Trend stark ist"""

    async def analyze(self, symbol: str, asset_type: str, **kwargs) -> dict:
        macro = await asyncio.to_thread(get_macro_data)

        if not macro.get("available"):
            # Ohne FRED-Daten trotzdem Thematic-Analyse durchführen
            user_prompt = f"""Asset: {symbol} (Typ: {asset_type})
FRED-Daten nicht verfügbar. Fokussiere dich auf Dimension 1: Megatrends.

Analysiere: Profitiert {symbol} von einem der aktuellen globalen Megatrends (KI, Kernenergie,
Rüstung, Rohstoffe, Biotech, Reshoring, Geopolitik)?
Sei konkret und nenne den spezifischen Trend.
Antworte nur mit JSON."""
            result = await asyncio.to_thread(self._call_claude, user_prompt)
            result["key_metrics"] = {"fred_available": False}
            return result

        def fmt(v, suffix=""):
            return f"{v}{suffix}" if v is not None else "N/A"

        inverted_note = " (INVERTIERT — Rezessionssignal)" if macro.get("yield_curve_inverted") else ""

        user_prompt = f"""Asset: {symbol} (Typ: {asset_type})
Datum: {macro.get('fetched_at', 'N/A')[:10]}

MAKRO-DATEN (FRED):
- Fed Funds Rate: {fmt(macro.get('fedfunds'), '%')}
- CPI YoY: {fmt(macro.get('cpi'), '%')} (Trend: {macro.get('cpi_trend', 'N/A')})
- 10J Treasury: {fmt(macro.get('dgs10'), '%')}
- Zinskurve (10J-2J): {fmt(macro.get('yield_spread'), '%')}{inverted_note}
- Arbeitslosigkeit: {fmt(macro.get('unrate'), '%')} (Trend: {macro.get('unrate_trend', 'N/A')})
- BIP-Wachstum: {fmt(macro.get('gdp_growth'), '%')} QoQ annualisiert
- Fed-Politik (letzte 6 Monate): {macro.get('fed_policy', 'N/A')}

AUFGABE:
1. Welchem Megatrend ist {symbol} zuzuordnen? (KI, Kernenergie, Rüstung, Rohstoffe, Biotech, etc.)
2. Wie stark profitiert/leidet das Asset von diesem Trend AKTUELL?
3. Unterstützt oder hemmt das Makro-Umfeld diesen Trend?
4. Finales Urteil: BUY / HOLD / SELL

Antworte nur mit JSON. Sei konkret — nenne Trend-Namen und die Verbindung zum Asset."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "fed_funds_rate": macro.get("fedfunds"),
            "cpi": macro.get("cpi"),
            "yield_spread": macro.get("yield_spread"),
            "yield_curve_inverted": macro.get("yield_curve_inverted"),
            "fed_policy": macro.get("fed_policy"),
        }
        return result
