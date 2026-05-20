from agents.base_agent import BaseAgent, SKIP_SIGNAL
from data_fetchers.fred_fetcher import get_macro_data
import asyncio


class MacroAgent(BaseAgent):
    name = "macro"
    system_prompt = """Du bist ein Makroökonom und Thematic-Investment-Analyst bei einem Hedge Fund.
Du suchst aktiv nach UNTERBEWERTETEN oder NOCH NICHT ENTDECKTEN Megatrend-Benefiziaren.

━━━ DENKWEISE: PICKS & SHOVELS, NICHT DAS OFFENSICHTLICHE ━━━
NVDA ist bereits 400% gestiegen — der Zug ist abgefahren. Finde stattdessen:
- Zulieferer & Infrastruktur-Plays, die den Trend ermöglichen aber noch nicht überlaufen sind
- Kleine Unternehmen im gleichen Ökosystem (weniger bekannt = möglicherweise billiger)
- Second-Derivative-Profiteure: Wer profitiert indirekt, aber stark?
Beispiele für Picks-&-Shovels-Denke:
  • KI-Boom → nicht NVDA, sondern Vertiv (Kühlung), Eaton (Strom), Quanta Services (Grid-Bau)
  • Kernenergie → nicht bekannte Betreiber, sondern Cameco (Uran), BWX Technologies (Reaktorkomponenten)
  • Rüstung → nicht Lockheed, sondern Kratos Defense (Drohnen), Mercury Systems (Electronics)
  • GLP-1 → nicht nur Lilly/Novo, sondern Viking Therapeutics (Pipeline), Repligen (Biotech-Zulieferer)

━━━ GLOBALE MEGATRENDS 2025 ━━━
• KI-Infrastruktur: Kühlung, Strom, Networking, Server-Hardware, Grid-Erweiterung
• Kernenergie-Renaissance: KI braucht 10x mehr Strom → Uran, SMRs, Betreiber, Services
• Rüstung & Autonome Systeme: Drohnen, Defense-KI, Cybersecurity, NATO-Aufrüstung
• Rohstoffe für die Zukunft: Kupfer, Uran, seltene Erden, Lithium, Silber
• GLP-1 & Biotech: Adipositas-Pandemie, KI-beschleunigte Forschung, RNA-Therapeutika
• Grid-Modernisierung: USA braucht dringend mehr Strom für KI → HVAC, Elektrobau, Infrastruktur
• Geopolitik & Reshoring: Supply-Chain-Unabhängigkeit, US-Chipfertigung, Zölle

━━━ DIMENSION 2: MAKRO-UMFELD ━━━
Fed-Politik, Zinsen, Inflation — als Hintergrundcheck.

Entscheidungsregeln:
- Small/Mid-Cap im heissen Trend + noch nicht überlaufen → BUY, Confidence 0.7-0.85
- Asset profitiert von Trend aber hat schon 200%+ gemacht → HOLD oder schwaches BUY (Warnung!)
- Kein Trend-Bezug + mittelmässiges Makro → HOLD
- Gegenwind durch falsche Positionierung, schlechtes Makro → SELL
- Sei KONKRET: erkläre warum DIESES Asset der interessanteste Weg ist, den Trend zu spielen"""

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
