import sqlite3
from typing import Optional
from database import (
    get_conn, get_portfolio, update_cash, get_positions, get_position,
    upsert_position, reduce_or_close_position, insert_trade,
)
from data_fetchers.yfinance_fetcher import get_current_price, get_fx_rate


class InsufficientCashError(Exception):
    pass


class NoPositionError(Exception):
    pass


def get_portfolio_with_value(conn: sqlite3.Connection) -> dict:
    portfolio = get_portfolio(conn)
    positions = get_positions(conn)

    total_positions_chf = 0.0
    enriched = []

    for pos in positions:
        price = get_current_price(pos["symbol"])
        fx = get_fx_rate(pos.get("currency", "USD"))
        current_price_chf = (price * fx) if price else None
        position_value_chf = (current_price_chf * pos["quantity"]) if current_price_chf else None
        cost_basis_chf = pos["avg_buy_price"] * pos["quantity"] * fx
        pnl_chf = (position_value_chf - cost_basis_chf) if position_value_chf else None
        pnl_pct = (pnl_chf / cost_basis_chf * 100) if (pnl_chf is not None and cost_basis_chf > 0) else None

        enriched.append({
            **pos,
            "current_price": price,
            "current_price_chf": round(current_price_chf, 4) if current_price_chf else None,
            "position_value_chf": round(position_value_chf, 2) if position_value_chf else None,
            "cost_basis_chf": round(cost_basis_chf, 2),
            "pnl_chf": round(pnl_chf, 2) if pnl_chf is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        })
        if position_value_chf:
            total_positions_chf += position_value_chf

    total_value = portfolio["cash_chf"] + total_positions_chf

    return {
        "cash_chf": round(portfolio["cash_chf"], 2),
        "positions_value_chf": round(total_positions_chf, 2),
        "total_value_chf": round(total_value, 2),
        "positions": enriched,
        "updated_at": portfolio["updated_at"],
    }


def execute_buy(
    symbol: str,
    asset_type: str,
    size_chf: float,
    agent_signals: Optional[dict] = None,
) -> dict:
    price_usd = get_current_price(symbol)
    if price_usd is None:
        raise ValueError(f"Kein aktueller Kurs für {symbol} verfügbar")

    fx = get_fx_rate("USD")
    price_chf = price_usd * fx
    quantity = size_chf / price_chf
    total_chf = quantity * price_chf

    with get_conn() as conn:
        portfolio = get_portfolio(conn)
        if portfolio["cash_chf"] < total_chf:
            raise InsufficientCashError(
                f"Nicht genug Cash: {portfolio['cash_chf']:.0f} CHF verfügbar, "
                f"{total_chf:.0f} CHF benötigt"
            )

        new_cash = portfolio["cash_chf"] - total_chf
        update_cash(conn, new_cash)
        upsert_position(conn, symbol, asset_type, quantity, price_usd)
        trade_id = insert_trade(
            conn, symbol, asset_type, "BUY",
            quantity, price_usd, price_chf, total_chf,
            None, agent_signals,
        )

    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "direction": "BUY",
        "quantity": round(quantity, 8),
        "price_usd": round(price_usd, 4),
        "price_chf": round(price_chf, 4),
        "total_chf": round(total_chf, 2),
        "remaining_cash_chf": round(new_cash, 2),
    }


def execute_sell(
    symbol: str,
    asset_type: str,
    quantity: Optional[float] = None,
    agent_signals: Optional[dict] = None,
) -> dict:
    with get_conn() as conn:
        position = get_position(conn, symbol)
        if not position:
            raise NoPositionError(f"Keine offene Position für {symbol}")

        sell_qty = quantity if quantity else position["quantity"]
        sell_qty = min(sell_qty, position["quantity"])

        price_usd = get_current_price(symbol)
        if price_usd is None:
            raise ValueError(f"Kein aktueller Kurs für {symbol}")

        fx = get_fx_rate("USD")
        price_chf = price_usd * fx
        total_chf = sell_qty * price_chf

        cost_basis_chf = position["avg_buy_price"] * sell_qty * fx
        pnl_chf = total_chf - cost_basis_chf

        portfolio = get_portfolio(conn)
        new_cash = portfolio["cash_chf"] + total_chf
        update_cash(conn, new_cash)
        reduce_or_close_position(conn, symbol, sell_qty)
        trade_id = insert_trade(
            conn, symbol, asset_type, "SELL",
            sell_qty, price_usd, price_chf, total_chf,
            pnl_chf, agent_signals,
        )

    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "direction": "SELL",
        "quantity": round(sell_qty, 8),
        "price_usd": round(price_usd, 4),
        "price_chf": round(price_chf, 4),
        "total_chf": round(total_chf, 2),
        "pnl_chf": round(pnl_chf, 2),
        "remaining_cash_chf": round(new_cash, 2),
    }


def execute_from_analysis(analysis_result: dict) -> Optional[dict]:
    orchestrator = analysis_result.get("orchestrator", {})
    action = orchestrator.get("action", "HOLD")
    symbol = analysis_result.get("symbol")
    asset_type = analysis_result.get("asset_type", "stock")
    signals = analysis_result.get("signals", {})

    if action == "HOLD" or not symbol:
        return None

    size_chf = orchestrator.get("position_size_chf", 5000.0)

    if action == "BUY":
        return execute_buy(symbol, asset_type, size_chf, signals)
    elif action == "SELL":
        with get_conn() as conn:
            pos = get_position(conn, symbol)
        if pos:
            return execute_sell(symbol, asset_type, agent_signals=signals)
    return None
