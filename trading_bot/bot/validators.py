"""
validators.py
Input validation helpers for the trading bot CLI.
All public functions raise ValueError with a descriptive message on failure.
"""

from __future__ import annotations

from typing import Optional


VALID_SIDES       = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}  # STOP_MARKET = bonus


def validate_symbol(symbol: str) -> str:
    """
    Normalise and validate a trading symbol.

    Rules:
    - Must be a non-empty string.
    - Converted to uppercase.
    - Must end with USDT (Futures USDT-M pairs).

    Args:
        symbol: Raw symbol string from user input.

    Returns:
        Normalised uppercase symbol string.

    Raises:
        ValueError: If the symbol fails validation.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")

    symbol = symbol.strip().upper()

    if not symbol.isalpha():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Only letters are allowed (e.g. BTCUSDT)."
        )

    if not symbol.endswith("USDT"):
        raise ValueError(
            f"Symbol '{symbol}' does not end with 'USDT'. "
            "Only USDT-M futures pairs are supported (e.g. BTCUSDT, ETHUSDT)."
        )

    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Uppercase side string.

    Raises:
        ValueError: If side is not BUY or SELL.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET' (case-insensitive).

    Returns:
        Uppercase order type string.

    Raises:
        ValueError: If order type is not supported.
    """
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: float | str) -> float:
    """
    Validate order quantity.

    Args:
        quantity: Order quantity (positive number).

    Returns:
        Validated float quantity.

    Raises:
        ValueError: If quantity is not a positive number.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")

    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0. Got: {qty}")

    # Binance minimum quantity guard (generic; symbol-specific filters
    # are enforced server-side but we catch obvious mistakes early).
    if qty > 10_000:
        raise ValueError(
            f"Quantity {qty} seems unusually large. Please double-check."
        )

    return qty


def validate_price(price: Optional[float | str], order_type: str) -> Optional[float]:
    """
    Validate order price.

    Price is required for LIMIT and STOP_MARKET orders, forbidden for MARKET.

    Args:
        price:      Limit price (may be None for MARKET orders).
        order_type: The (already-validated) order type string.

    Returns:
        Validated float price, or None for MARKET orders.

    Raises:
        ValueError: If price rules are violated.
    """
    if order_type == "MARKET":
        if price is not None:
            raise ValueError(
                "Price must not be provided for MARKET orders "
                "(Binance ignores it and it can be confusing)."
            )
        return None

    # LIMIT / STOP_MARKET require a price
    if price is None:
        raise ValueError(
            f"Price is required for {order_type} orders. "
            "Please supply --price."
        )

    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValueError(f"Price '{price}' is not a valid number.")

    if p <= 0:
        raise ValueError(f"Price must be greater than 0. Got: {p}")

    return p


def validate_stop_price(
    stop_price: Optional[float | str], order_type: str
) -> Optional[float]:
    """
    Validate stop price (required for STOP_MARKET orders).

    Args:
        stop_price: Stop trigger price.
        order_type: The (already-validated) order type string.

    Returns:
        Validated float stop price, or None.

    Raises:
        ValueError: On invalid stop price.
    """
    if order_type != "STOP_MARKET":
        return None  # stop_price is irrelevant for other types

    if stop_price is None:
        raise ValueError(
            "stop_price is required for STOP_MARKET orders. "
            "Please supply --stop-price."
        )

    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValueError(f"stop_price '{stop_price}' is not a valid number.")

    if sp <= 0:
        raise ValueError(f"stop_price must be greater than 0. Got: {sp}")

    return sp
