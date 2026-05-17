import asyncio
from typing import Optional
from agents.macro_agent import MacroAgent
from agents.technical_agent import TechnicalAgent
from agents.fundamental_agent import FundamentalAgent
from agents.crypto_agent import CryptoAgent
from agents.risk_agent import RiskAgent
from data_fetchers.yfinance_fetcher import get_asset_type
from config import MAX_POSITION_PCT

WEIGHTS_STOCK = {"macro": 0.20, "technical": 0.35, "fundamental": 0.30, "crypto": 0.00, "risk": 0.15}
WEIGHTS_ETF   = {"macro": 0.20, "technical": 0.35, "fundamental": 0.30, "crypto": 0.00, "risk": 0.15}
WEIGHTS_CRYPTO = {"macro": 0.15, "technical": 0.30, "fundamental": 0.00, "crypto": 0.40, "risk": 0.15}

BUY_THRESHOLD  =  0.25
SELL_THRESHOLD = -0.25
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
) -> dict:
    asset_type = get_asset_type(symbol)
    weights = {
        "stock": WEIGHTS_STOCK,
        "etf":   WEIGHTS_ETF,
        "crypto": WEIGHTS_CRYPTO,
    }.get(asset_type, WEIGHTS_STOCK)

    macro_agent = MacroAgent()
    tech_agent  = TechnicalAgent()
    fund_agent  = FundamentalAgent()
    crypto_agent = CryptoAgent()

    # Phase 1: Alle nicht-risk Agenten parallel
    macro_task  = macro_agent.analyze(symbol, asset_type)
    tech_task   = tech_agent.analyze(symbol, asset_type)
    fund_task   = fund_agent.analyze(symbol, asset_type)
    crypto_task = crypto_agent.analyze(symbol, asset_type)

    macro_sig, tech_sig, fund_sig, crypto_sig = await asyncio.gather(
        macro_task, tech_task, fund_task, crypto_task,
        return_exceptions=False,
    )

    phase1_signals = {
        "macro":       macro_sig,
        "technical":   tech_sig,
        "fundamental": fund_sig,
        "crypto":      crypto_sig,
    }

    # Vorläufiger Score ohne Risk
    prelim_score = sum(
        _score(phase1_signals[k].get("action", "HOLD"), phase1_signals[k].get("confidence", 0.0))
        * weights[k]
        for k in ("macro", "technical", "fundamental", "crypto")
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
        for k in ("macro", "technical", "fundamental", "crypto")
    )

    if weighted_score > BUY_THRESHOLD:
        final_action = "BUY"
        final_conf = min(weighted_score, 1.0)
    elif weighted_score < SELL_THRESHOLD:
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
