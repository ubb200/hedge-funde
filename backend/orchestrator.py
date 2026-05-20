import asyncio
from typing import Optional
from agents.macro_agent import MacroAgent
from agents.technical_agent import TechnicalAgent
from agents.fundamental_agent import FundamentalAgent
from agents.crypto_agent import CryptoAgent
from agents.risk_agent import RiskAgent
from agents.sentiment_agent import SentimentAgent
from data_fetchers.yfinance_fetcher import get_asset_type
from config import MAX_POSITION_PCT
from learning import get_adjusted_weights

# Gewichte: Megatrends/Makro dominiert, Technical nur als Trend-Filter
WEIGHTS_STOCK  = {"macro": 0.35, "technical": 0.10, "fundamental": 0.20, "crypto": 0.00, "risk": 0.15, "sentiment": 0.20}
WEIGHTS_ETF    = {"macro": 0.35, "technical": 0.15, "fundamental": 0.15, "crypto": 0.00, "risk": 0.15, "sentiment": 0.20}
WEIGHTS_CRYPTO = {"macro": 0.25, "technical": 0.10, "fundamental": 0.00, "crypto": 0.40, "risk": 0.15, "sentiment": 0.10}

BUY_THRESHOLD  =  0.25
SELL_THRESHOLD = -0.25
SELL_THRESHOLD_WITH_POSITION = -0.15  # leichterer Exit wenn wir die Position schon halten
RISK_VETO_THRESHOLD = 0.60


def _score(action: str, confidence: float) -> float:
    direction = {"BUY": 1.0, "HOLD": 0.0, "SELL": -1.0}.get(action, 0.0)
    return direction * max(0.0, min(1.0, confidence))


def _build_reasoning(signals: dict, final_action: str, weighted_score: float) -> str:
    parts = []
    for name, sig in signals.items():
        if sig and sig.get("action"):
            parts.append(f"{name.capitalize()}: {sig['action']} ({round(sig.get('confidence', 0), 2)})")
    signal_str = " | ".join(parts)
    return f"Gewichteter Score: {weighted_score:+.3f} → {final_action}. Signale: {signal_str}"


async def run_analysis(
    symbol: str,
    portfolio: dict,
    positions: list[dict],
    learning_context: dict | None = None,
) -> dict:
    asset_type = get_asset_type(symbol)
    base_weights = {
        "stock": WEIGHTS_STOCK,
        "etf":   WEIGHTS_ETF,
        "crypto": WEIGHTS_CRYPTO,
    }.get(asset_type, WEIGHTS_STOCK)

    # Lernende Gewichte: wenn genug Trade-History vorhanden
    agent_stats = (learning_context or {}).get("agent_stats", {})
    weights = get_adjusted_weights(base_weights, agent_stats) if agent_stats else base_weights

    macro_agent     = MacroAgent()
    tech_agent      = TechnicalAgent()
    fund_agent      = FundamentalAgent()
    crypto_agent    = CryptoAgent()
    sentiment_agent = SentimentAgent()

    # Phase 1: Alle nicht-risk Agenten parallel
    macro_sig, tech_sig, fund_sig, crypto_sig, sentiment_sig = await asyncio.gather(
        macro_agent.analyze(symbol, asset_type),
        tech_agent.analyze(symbol, asset_type),
        fund_agent.analyze(symbol, asset_type),
        crypto_agent.analyze(symbol, asset_type),
        sentiment_agent.analyze(symbol, asset_type),
        return_exceptions=False,
    )

    phase1_signals = {
        "macro":       macro_sig,
        "technical":   tech_sig,
        "fundamental": fund_sig,
        "crypto":      crypto_sig,
        "sentiment":   sentiment_sig,
    }

    # Vorläufiger Score ohne Risk
    prelim_score = sum(
        _score(phase1_signals[k].get("action", "HOLD"), phase1_signals[k].get("confidence", 0.0))
        * weights[k]
        for k in ("macro", "technical", "fundamental", "crypto", "sentiment")
    )
    prelim_action = "BUY" if prelim_score > BUY_THRESHOLD else ("SELL" if prelim_score < SELL_THRESHOLD else "HOLD")

    # Positionsgrösse berechnen
    total_value = portfolio.get("total_value_chf", 100000.0)
    confidence_score = abs(prelim_score)
    raw_size_pct = confidence_score * MAX_POSITION_PCT * 1.5
    position_size_pct = min(raw_size_pct, MAX_POSITION_PCT)
    proposed_size_chf = total_value * position_size_pct

    # Phase 2: Risk Agent (braucht Phase-1-Ergebnisse)
    risk_agent = RiskAgent()
    risk_sig = await risk_agent.analyze(
        symbol=symbol,
        asset_type=asset_type,
        portfolio=portfolio,
        positions=positions,
        proposed_action=prelim_action,
        proposed_size_chf=proposed_size_chf,
        other_signals=phase1_signals,
    )

    all_signals = {**phase1_signals, "risk": risk_sig}

    # Finaler gewichteter Score (mit Risk)
    weighted_score = sum(
        _score(all_signals[k].get("action", "HOLD"), all_signals[k].get("confidence", 0.0))
        * weights[k]
        for k in ("macro", "technical", "fundamental", "crypto", "sentiment")
    )

    has_position = any(p["symbol"] == symbol for p in positions)
    effective_sell_threshold = SELL_THRESHOLD_WITH_POSITION if has_position else SELL_THRESHOLD

    if weighted_score > BUY_THRESHOLD:
        final_action = "BUY"
        final_conf = min(weighted_score, 1.0)
    elif weighted_score < effective_sell_threshold:
        final_action = "SELL"
        final_conf = min(abs(weighted_score), 1.0)
    else:
        final_action = "HOLD"
        final_conf = 1.0 - abs(weighted_score)

    # Risk-Veto: Risk sagt SELL mit hoher Confidence → BUY wird zu HOLD
    risk_action = risk_sig.get("action", "HOLD")
    risk_conf = risk_sig.get("confidence", 0.0)
    if risk_action == "SELL" and risk_conf >= RISK_VETO_THRESHOLD and final_action == "BUY":
        final_action = "HOLD"
        final_conf = risk_conf
        reasoning = f"Risk-Veto (Confidence {risk_conf:.0%}): {risk_sig.get('reasoning', '')}. " + _build_reasoning(all_signals, final_action, weighted_score)
    else:
        reasoning = _build_reasoning(all_signals, final_action, weighted_score)

    orchestrator = {
        "action": final_action,
        "confidence": round(final_conf, 3),
        "weighted_score": round(weighted_score, 4),
        "position_size_pct": round(position_size_pct, 4),
        "position_size_chf": round(proposed_size_chf, 2),
        "reasoning": reasoning,
        "asset_type": asset_type,
    }

    return {
        "symbol": symbol,
        "asset_type": asset_type,
        "orchestrator": orchestrator,
        "signals": all_signals,
    }
