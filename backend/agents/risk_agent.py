from agents.base_agent import BaseAgent
from data_fetchers.yfinance_fetcher import get_correlation_matrix
import asyncio
import json


class RiskAgent(BaseAgent):
    name = "risk"
    system_prompt = """Du bist ein Risikomanager bei einem Hedge Fund.
Deine Aufgabe ist NICHT eine Meinung zur Kursentwicklung zu haben. Deine Aufgabe ist das Portfolio zu schützen.
Du schaust auf Positionsgrössen, Korrelationsrisiken und ob ein neuer Trade das Portfolio fragiler macht.

Regeln:
- Keine einzelne Position sollte mehr als 15% des Portfolios überschreiten
- Korrelierte Positionen (r > 0.7) gelten als ein Risiko-Bucket — nicht verdoppeln
- Cash unter 20% des Portfolios ist ein Warnsignal — das Portfolio ist überinvestiert
- Krypto gesamt sollte 30% des Portfolios nicht überschreiten
- Du KANNST und SOLLST HOLD sagen, auch wenn andere Agenten BUY sagen — Risk überschreibt Enthusiasmus
- Das risk_flags-Feld ist das Wichtigste in deinem Output"""

    async def analyze(self, symbol: str, asset_type: str,
                      portfolio: dict, positions: list[dict],
                      proposed_action: str, proposed_size_chf: float,
                      other_signals: dict, **kwargs) -> dict:

        total_value = portfolio.get("total_value_chf", 100000)
        cash = portfolio.get("cash_chf", total_value)
        cash_pct = round(cash / total_value * 100, 1) if total_value > 0 else 100.0

        all_symbols = [p["symbol"] for p in positions] + [symbol]
        corr_matrix = await asyncio.to_thread(get_correlation_matrix, all_symbols)

        corr_lines = []
        for pos in positions:
            sym = pos["symbol"]
            corr_val = None
            try:
                corr_val = corr_matrix.get(symbol, {}).get(sym)
            except Exception:
                pass
            if corr_val is not None:
                corr_lines.append(f"  {symbol} vs {sym}: {round(corr_val, 3)}")

        corr_text = "\n".join(corr_lines) if corr_lines else "  Keine bestehenden Positionen"

        pos_values = [(p["symbol"], p["quantity"] * p.get("current_price", p["avg_buy_price"])) for p in positions]
        biggest = max(pos_values, key=lambda x: x[1]) if pos_values else (None, 0)
        biggest_pct = round(biggest[1] / total_value * 100, 1) if total_value > 0 else 0
        trade_pct = round(proposed_size_chf / total_value * 100, 1) if total_value > 0 else 0

        other_str = ", ".join(
            f"{k}: {v.get('action','?')}/{round(v.get('confidence', 0), 2)}"
            for k, v in other_signals.items()
        )

        user_prompt = f"""PORTFOLIO-ZUSTAND:
- Gesamtwert: {round(total_value, 0)} CHF | Cash: {round(cash, 0)} CHF ({cash_pct}%)
- Offene Positionen: {len(positions)}
- Grösste Einzelposition: {biggest[0] or 'keine'} ({biggest_pct}% des Portfolios)

VORGESCHLAGENER TRADE:
- Symbol: {symbol} (Typ: {asset_type}) | Richtung: {proposed_action}
- Vorgeschlagene Grösse: {round(proposed_size_chf, 0)} CHF ({trade_pct}% des Portfolios)

KORRELATION MIT BESTEHENDEN POSITIONEN:
{corr_text}
(Über 0.7 = hohe Korrelation)

ANDERE AGENTEN-SIGNALE: {other_str}

Ist dieser Trade für das Portfolio angemessen? Antworte nur mit JSON."""

        result = await asyncio.to_thread(self._call_claude, user_prompt)
        result["key_metrics"] = {
            "cash_pct": cash_pct,
            "biggest_position_pct": biggest_pct,
            "proposed_trade_pct": trade_pct,
            "num_positions": len(positions),
        }
        return result
