"""
Self-improvement: analysiert vergangene Paper-Trades und passt Agentengewichte an.
Ab MIN_TRADES abgeschlossenen Trades (P&L bekannt) lernt der Bot aus seinen Fehlern.
"""
import json
import logging

from database import get_conn, get_trades

logger = logging.getLogger(__name__)

MIN_TRADES = 5          # Mindestanzahl bevor Lerngewichte aktiv werden
MAX_ADJUSTMENT = 0.35   # Max ±35% Abweichung vom Basisgewicht


def _parse_signals(raw) -> dict:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return raw or {}


def compute_agent_stats(trades: list[dict]) -> dict[str, dict]:
    """
    Bewertet jeden Agenten: wie oft stimmte seine Empfehlung mit dem Trade-Ergebnis überein?

    Korrekt = Agent sagte BUY → Trade gewann (pnl > 0)
             = Agent sagte SELL → Trade verlor weniger / Exit war richtig (pnl > 0 für SELL-Trade)
    HOLD-Signale werden nicht gewertet.
    """
    stats: dict[str, dict] = {}

    for trade in trades:
        pnl = trade.get("pnl_chf")
        if pnl is None:
            continue

        direction = trade.get("direction", "")
        signals = _parse_signals(trade.get("agent_signals"))

        for agent, signal in signals.items():
            if not isinstance(signal, dict):
                continue
            action = signal.get("action", "HOLD")
            if action == "HOLD":
                continue

            s = stats.setdefault(agent, {"total": 0, "correct": 0, "pnl_sum": 0.0})
            s["total"] += 1
            s["pnl_sum"] += pnl

            # Korrekt wenn Agent-Richtung == Trade-Richtung UND Trade war profitabel
            if action == direction and pnl > 0:
                s["correct"] += 1

    for s in stats.values():
        s["accuracy"] = s["correct"] / s["total"] if s["total"] > 0 else 0.5

    return stats


def get_adjusted_weights(
    base_weights: dict[str, float],
    agent_stats: dict[str, dict],
) -> dict[str, float]:
    """
    Passt Gewichte proportional zur Agent-Accuracy an.
    Accuracy 50% → Faktor 1.0 (neutral)
    Accuracy 100% → Faktor 1 + MAX_ADJUSTMENT
    Accuracy 0%   → Faktor 1 - MAX_ADJUSTMENT
    Gewichte werden danach re-normalisiert auf Summe 1.0.
    """
    adjusted = dict(base_weights)

    for agent, s in agent_stats.items():
        if agent not in adjusted or adjusted[agent] == 0.0:
            continue
        if s["total"] < MIN_TRADES:
            continue

        accuracy = s["accuracy"]
        # Lineare Anpassung: 0.5 Accuracy → 0, 1.0 → +MAX, 0.0 → -MAX
        delta = (accuracy - 0.5) * 2 * MAX_ADJUSTMENT
        adjusted[agent] = max(0.01, base_weights[agent] * (1 + delta))

    # Re-normalisieren
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: round(v / total, 4) for k, v in adjusted.items()}

    return adjusted


def build_performance_summary(agent_stats: dict[str, dict]) -> str:
    """Erzeugt einen Kurztext für Logs und Agent-Kontext."""
    eligible = {k: v for k, v in agent_stats.items() if v["total"] >= MIN_TRADES}
    if not eligible:
        return ""

    lines = ["Historische Trefferquoten:"]
    for agent, s in sorted(eligible.items(), key=lambda x: -x[1]["accuracy"]):
        lines.append(
            f"  {agent}: {s['accuracy']:.0%} ({s['correct']}/{s['total']} Trades, "
            f"P&L-Summe CHF {s['pnl_sum']:+.0f})"
        )
    return "\n".join(lines)


def load_learning_context() -> dict:
    """
    Hauptfunktion: lädt Trade-History, berechnet Agent-Stats und gibt
    angepasste Gewichts-Korrekturen zurück.
    Wird einmal pro Tagesanalyse aufgerufen.
    """
    try:
        with get_conn() as conn:
            trades = get_trades(conn, limit=1000)

        completed = [t for t in trades if t.get("pnl_chf") is not None]
        logger.info(f"Learning: {len(completed)} abgeschlossene Trades geladen")

        if len(completed) < MIN_TRADES:
            logger.info(
                f"Learning: zu wenige Trades ({len(completed)} < {MIN_TRADES}) "
                f"— Basisgewichte aktiv"
            )
            return {"agent_stats": {}, "summary": "", "ready": False}

        agent_stats = compute_agent_stats(completed)
        summary = build_performance_summary(agent_stats)

        if summary:
            logger.info(f"Learning:\n{summary}")

        return {
            "agent_stats": agent_stats,
            "summary": summary,
            "ready": True,
            "num_trades": len(completed),
        }

    except Exception as exc:
        logger.error(f"Learning Fehler: {exc}", exc_info=True)
        return {"agent_stats": {}, "summary": "", "ready": False}
