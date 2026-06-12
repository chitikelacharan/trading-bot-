#!/usr/bin/env python3
"""
cli.py – Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples:
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
  python cli.py place --symbol ETHUSDT --side SELL --type LIMIT  --quantity 0.1 --price 3000
  python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 50000

Sub-commands:
  place   – Place a new order (MARKET / LIMIT / STOP_MARKET)
  ping    – Test connectivity to the testnet
  account – Show account balance summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from typing import Optional

from dotenv import load_dotenv

from bot.client import BinanceClientError, BinanceFuturesClient, NetworkError
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_order
from bot.validators import (
    VALID_ORDER_TYPES,
    VALID_SIDES,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

# ── Bootstrap logging FIRST so all subsequent modules have handlers ────────
setup_logging()
logger = get_logger("cli")


# ── Helpers ────────────────────────────────────────────────────────────────

def _load_credentials() -> tuple[str, str]:
    """
    Load API credentials from environment variables or a .env file.

    Priority: environment variables > .env file in project root.

    Returns:
        (api_key, api_secret) tuple.

    Raises:
        SystemExit: If credentials are missing.
    """
    load_dotenv()  # no-op if .env is absent
    api_key    = os.getenv("BINANCE_API_KEY",    "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        _error(
            "API credentials not found.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET as environment "
            "variables or place them in a .env file:\n\n"
            "  BINANCE_API_KEY=<your_key>\n"
            "  BINANCE_API_SECRET=<your_secret>\n"
        )

    return api_key, api_secret


def _error(message: str, exit_code: int = 1) -> None:
    """Print an error to stderr and exit."""
    print(f"\n❌  ERROR: {message}\n", file=sys.stderr)
    logger.error("CLI error: %s", message)
    sys.exit(exit_code)


def _print_banner() -> None:
    banner = textwrap.dedent(
        """
        ╔══════════════════════════════════════════════════════════════╗
        ║        Binance Futures Testnet Trading Bot  v1.0             ║
        ║        Network: USDT-M Futures Testnet                       ║
        ╚══════════════════════════════════════════════════════════════╝
        """
    )
    print(banner)


def _print_order_summary(
    symbol:     str,
    side:       str,
    order_type: str,
    quantity:   float,
    price:      Optional[float],
    stop_price: Optional[float],
) -> None:
    """Print a formatted summary of the order being placed."""
    print("\n" + "─" * 60)
    print("  📋  ORDER REQUEST SUMMARY")
    print("─" * 60)
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price is not None:
        print(f"  Price      : {price}")
    if stop_price is not None:
        print(f"  Stop Price : {stop_price}")
    print("─" * 60)


def _print_order_result(result: dict) -> None:
    """Print a formatted summary of the order response."""
    print("\n" + "─" * 60)
    print("  ✅  ORDER RESPONSE")
    print("─" * 60)
    print(f"  Order ID      : {result.get('orderId')}")
    print(f"  Symbol        : {result.get('symbol')}")
    print(f"  Side          : {result.get('side')}")
    print(f"  Type          : {result.get('type')}")
    print(f"  Status        : {result.get('status')}")
    print(f"  Orig Qty      : {result.get('origQty')}")
    print(f"  Executed Qty  : {result.get('executedQty')}")

    avg = result.get("avgPrice")
    if avg and float(avg) > 0:
        print(f"  Avg Price     : {avg}")

    prc = result.get("price")
    if prc and float(prc) > 0:
        print(f"  Limit Price   : {prc}")

    sp = result.get("stopPrice")
    if sp and float(sp) > 0:
        print(f"  Stop Price    : {sp}")

    tif = result.get("timeInForce")
    if tif:
        print(f"  Time-In-Force : {tif}")

    print("─" * 60)
    status = result.get("status", "")
    if status in ("FILLED", "NEW", "PARTIALLY_FILLED"):
        print(f"\n  🎉  Order placed successfully! (status: {status})\n")
    else:
        print(f"\n  ⚠️   Order status: {status}\n")


# ── Sub-command handlers ───────────────────────────────────────────────────

def handle_place(args: argparse.Namespace) -> None:
    """Handle the 'place' sub-command."""
    _print_banner()

    # ── Validate CLI inputs ────────────────────────────────────────────────
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.type)
        qty        = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValueError as exc:
        _error(str(exc))

    _print_order_summary(symbol, side, order_type, qty, price, stop_price)

    # ── Confirm if not --yes ───────────────────────────────────────────────
    if not args.yes:
        try:
            ans = input("  Proceed with this order? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if ans not in ("y", "yes"):
            print("Order cancelled by user.")
            logger.info("Order cancelled by user at confirmation prompt.")
            sys.exit(0)

    # ── Load credentials & build client ───────────────────────────────────
    api_key, api_secret = _load_credentials()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)

    # ── Ping first to catch connectivity issues early ─────────────────────
    print("\n  🔗  Connecting to Binance Futures Testnet …")
    try:
        client.ping()
        print("  🟢  Connected successfully.\n")
    except NetworkError as exc:
        _error(f"Cannot reach testnet: {exc}")

    # ── Place the order ────────────────────────────────────────────────────
    print("  ⏳  Submitting order …")
    try:
        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        _error(f"Validation error: {exc}")
    except BinanceClientError as exc:
        _error(
            f"Binance API rejected the order.\n"
            f"  HTTP Status : {exc.status_code}\n"
            f"  Error Code  : {exc.code}\n"
            f"  Message     : {exc.msg}"
        )
    except NetworkError as exc:
        _error(f"Network failure while placing order: {exc}")

    _print_order_result(result)

    if args.json:
        print("\n  📄  Full JSON response:")
        print(json.dumps(result, indent=2))


def handle_ping(args: argparse.Namespace) -> None:
    """Handle the 'ping' sub-command."""
    _print_banner()
    api_key, api_secret = _load_credentials()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    print("  🔗  Pinging Binance Futures Testnet …")
    try:
        client.ping()
        server_time = client.get_server_time()
        print(f"  🟢  Testnet is reachable! Server time: {server_time} ms")
        logger.info("Ping OK – server time: %s ms", server_time)
    except NetworkError as exc:
        _error(str(exc))
    except BinanceClientError as exc:
        _error(str(exc))


def handle_account(args: argparse.Namespace) -> None:
    """Handle the 'account' sub-command (balance summary)."""
    _print_banner()
    api_key, api_secret = _load_credentials()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)

    print("  📊  Fetching account information …\n")
    try:
        info = client.get_account_info()
    except (BinanceClientError, NetworkError) as exc:
        _error(str(exc))

    assets = [a for a in info.get("assets", []) if float(a.get("walletBalance", 0)) > 0]

    if not assets:
        print("  No funded assets found on testnet.\n")
        return

    print("─" * 60)
    print(f"  {'Asset':<10} {'Wallet Balance':<22} {'Unrealised PnL'}")
    print("─" * 60)
    for asset in assets:
        print(
            f"  {asset['asset']:<10} "
            f"{float(asset['walletBalance']):<22.6f} "
            f"{float(asset.get('unrealizedProfit', 0)):.6f}"
        )
    print("─" * 60 + "\n")

    if args.json:
        print("\n  📄  Full JSON response:")
        print(json.dumps(info, indent=2))


# ── Argument parser ────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot (USDT-M)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              Place a MARKET BUY:
                python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

              Place a LIMIT SELL:
                python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3000

              Place a STOP_MARKET (bonus):
                python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 50000

              Ping the testnet:
                python cli.py ping

              Show account balances:
                python cli.py account
            """
        ),
    )

    sub = parser.add_subparsers(dest="command", required=True, title="sub-commands")

    # ── 'place' sub-command ────────────────────────────────────────────────
    place_p = sub.add_parser(
        "place",
        help="Place a MARKET, LIMIT, or STOP_MARKET order",
        description="Place a futures order on Binance Testnet.",
    )
    place_p.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    place_p.add_argument(
        "--side",
        required=True,
        choices=[s.lower() for s in VALID_SIDES] + list(VALID_SIDES),
        metavar="SIDE",
        help=f"Order side: {' | '.join(sorted(VALID_SIDES))}",
    )
    place_p.add_argument(
        "--type", "-t",
        required=True,
        choices=[o.lower() for o in VALID_ORDER_TYPES] + list(VALID_ORDER_TYPES),
        metavar="TYPE",
        help=f"Order type: {' | '.join(sorted(VALID_ORDER_TYPES))}",
    )
    place_p.add_argument(
        "--quantity", "-q",
        required=True,
        type=float,
        metavar="QTY",
        help="Order quantity (number of contracts)",
    )
    place_p.add_argument(
        "--price", "-p",
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders)",
    )
    place_p.add_argument(
        "--stop-price",
        type=float,
        default=None,
        dest="stop_price",
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_MARKET orders)",
    )
    place_p.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    place_p.add_argument(
        "--json",
        action="store_true",
        help="Also print the full raw JSON response",
    )
    place_p.set_defaults(func=handle_place)

    # ── 'ping' sub-command ─────────────────────────────────────────────────
    ping_p = sub.add_parser("ping", help="Test connectivity to the testnet")
    ping_p.set_defaults(func=handle_ping)

    # ── 'account' sub-command ──────────────────────────────────────────────
    acc_p = sub.add_parser("account", help="Show account balance summary")
    acc_p.add_argument(
        "--json",
        action="store_true",
        help="Print full raw JSON account info",
    )
    acc_p.set_defaults(func=handle_account)

    return parser


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    logger.debug("CLI invoked with args: %s", vars(args))

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
