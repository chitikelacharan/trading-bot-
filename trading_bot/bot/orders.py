"""
orders.py
High-level order placement logic.

This module sits between the CLI and the raw API client:
  - Builds the correct parameter set for each order type.
  - Calls the client to submit the order.
  - Formats and returns a structured result dict for display.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client import BinanceFuturesClient
from .logging_config import get_logger
from .validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger("orders")


# ── Internal helpers ──────────────────────────────────────────────────────

def _build_order_params(
    symbol:     str,
    side:       str,
    order_type: str,
    quantity:   float,
    price:      Optional[float] = None,
    stop_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Construct the Binance-compatible parameter dict for an order.

    Args:
        symbol:     Validated trading symbol.
        side:       'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:   Order quantity.
        price:      Limit price (required for LIMIT; ignored for MARKET).
        stop_price: Stop trigger price (required for STOP_MARKET).

    Returns:
        Dict of parameters ready to pass to client.place_order().
    """
    params: Dict[str, Any] = {
        "symbol":   symbol,
        "side":     side,
        "type":     order_type,
        "quantity": quantity,
    }

    if order_type == "LIMIT":
        params["price"]       = price
        params["timeInForce"] = "GTC"   # Good-Till-Cancelled

    elif order_type == "STOP_MARKET":
        params["stopPrice"]   = stop_price
        params["closePosition"] = "false"

    return params


def _format_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key fields from the raw Binance order response.

    Args:
        raw: Full Binance order response dict.

    Returns:
        Simplified result dict with the most useful fields.
    """
    return {
        "orderId":     raw.get("orderId"),
        "symbol":      raw.get("symbol"),
        "side":        raw.get("side"),
        "type":        raw.get("type"),
        "status":      raw.get("status"),
        "origQty":     raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "avgPrice":    raw.get("avgPrice"),
        "price":       raw.get("price"),
        "stopPrice":   raw.get("stopPrice"),
        "timeInForce": raw.get("timeInForce"),
        "clientOrderId": raw.get("clientOrderId"),
        "updateTime":  raw.get("updateTime"),
    }


# ── Public API ─────────────────────────────────────────────────────────────

def place_order(
    client:     BinanceFuturesClient,
    symbol:     str,
    side:       str,
    order_type: str,
    quantity:   float | str,
    price:      Optional[float | str] = None,
    stop_price: Optional[float | str] = None,
) -> Dict[str, Any]:
    """
    Validate inputs and place an order via the Binance Futures API.

    This is the single entry point for all order types used by the CLI.

    Args:
        client:     Authenticated BinanceFuturesClient instance.
        symbol:     Trading pair (e.g. 'BTCUSDT').
        side:       'BUY' or 'SELL'.
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:   Number of contracts.
        price:      Limit price for LIMIT orders.
        stop_price: Trigger price for STOP_MARKET orders.

    Returns:
        Formatted order result dict.

    Raises:
        ValueError:                  On invalid input parameters.
        bot.client.BinanceClientError: On API rejections.
        bot.client.NetworkError:       On connectivity failures.
    """
    # ── Validate all inputs first ──────────────────────────────────────────
    symbol     = validate_symbol(symbol)
    side       = validate_side(side)
    order_type = validate_order_type(order_type)
    qty        = validate_quantity(quantity)
    prc        = validate_price(price, order_type)
    stp        = validate_stop_price(stop_price, order_type)

    logger.info(
        "Order validated | symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
        symbol,
        side,
        order_type,
        qty,
        prc if prc is not None else "N/A",
        stp if stp is not None else "N/A",
    )

    # ── Build parameter set ────────────────────────────────────────────────
    params = _build_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=qty,
        price=prc,
        stop_price=stp,
    )

    # ── Submit order ───────────────────────────────────────────────────────
    raw_response = client.place_order(**params)
    result       = _format_result(raw_response)

    logger.info(
        "Order accepted | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result["orderId"],
        result["status"],
        result["executedQty"],
        result["avgPrice"],
    )

    return result


def place_market_order(
    client:   BinanceFuturesClient,
    symbol:   str,
    side:     str,
    quantity: float | str,
) -> Dict[str, Any]:
    """Convenience wrapper for MARKET orders."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="MARKET",
        quantity=quantity,
    )


def place_limit_order(
    client:   BinanceFuturesClient,
    symbol:   str,
    side:     str,
    quantity: float | str,
    price:    float | str,
) -> Dict[str, Any]:
    """Convenience wrapper for LIMIT orders (GTC)."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=quantity,
        price=price,
    )


def place_stop_market_order(
    client:     BinanceFuturesClient,
    symbol:     str,
    side:       str,
    quantity:   float | str,
    stop_price: float | str,
) -> Dict[str, Any]:
    """Convenience wrapper for STOP_MARKET orders (bonus order type)."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="STOP_MARKET",
        quantity=quantity,
        stop_price=stop_price,
    )
