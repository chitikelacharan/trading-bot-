"""
client.py
Low-level Binance Futures REST API client.

Uses the `requests` library for all HTTP interactions so that there is no
hidden abstraction on top of the exchange's API.  Every outgoing request and
incoming response is logged at DEBUG level; errors are logged at ERROR level
before being re-raised so the caller can decide how to handle them.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

# ── Constants ──────────────────────────────────────────────────────────────
BASE_URL    = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000          # milliseconds – Binance recommended default
TIMEOUT     = 10            # HTTP request timeout in seconds


class BinanceClientError(Exception):
    """Raised when the Binance API returns a non-2xx HTTP status."""

    def __init__(self, status_code: int, code: int, msg: str) -> None:
        self.status_code = status_code
        self.code        = code
        self.msg         = msg
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {msg}")


class NetworkError(Exception):
    """Raised on connection/timeout failures."""


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance Futures REST API.

    All signed endpoints include a HMAC-SHA256 signature appended as the
    last query-string parameter, as required by the exchange.

    Args:
        api_key:    Binance Futures Testnet API key.
        api_secret: Binance Futures Testnet API secret.
        base_url:   Override the default testnet base URL (useful for unit
                    tests that point to a local mock server).
    """

    def __init__(
        self,
        api_key:    str,
        api_secret: str,
        base_url:   str = BASE_URL,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key    = api_key
        self._api_secret = api_secret
        self._base_url   = base_url.rstrip("/")
        self._session    = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceFuturesClient initialised (base_url=%s)", self._base_url)

    # ── Private helpers ────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a timestamp and HMAC-SHA256 signature to a parameters dict."""
        params["timestamp"]  = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string         = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method:   str,
        endpoint: str,
        params:   Optional[Dict[str, Any]] = None,
        signed:   bool = False,
    ) -> Any:
        """
        Execute an HTTP request against the Binance REST API.

        Args:
            method:   HTTP verb ('GET', 'POST', 'DELETE', …).
            endpoint: API path, e.g. '/fapi/v1/order'.
            params:   Query / body parameters.
            signed:   Whether to append HMAC signature.

        Returns:
            Decoded JSON response body.

        Raises:
            BinanceClientError: On non-2xx API responses.
            NetworkError:       On connection / timeout issues.
        """
        params = dict(params or {})
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"
        logger.debug(
            "→ %s %s | params=%s",
            method.upper(),
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params   if method.upper() != "GET" else None,
                timeout=TIMEOUT,
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, url)
            raise NetworkError(f"Request timed out ({TIMEOUT}s): {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s – %s", method, url, exc)
            raise NetworkError(f"Connection failed: {exc}") from exc

        logger.debug(
            "← HTTP %s | body=%s",
            response.status_code,
            response.text[:500],   # truncate large bodies in logs
        )

        # Attempt to parse JSON regardless of status code so we can extract
        # the Binance error code and message.
        try:
            data = response.json()
        except ValueError:
            data = {"code": -1, "msg": response.text}

        if not response.ok:
            code = data.get("code", -1) if isinstance(data, dict) else -1
            msg  = data.get("msg",  response.reason) if isinstance(data, dict) else str(data)
            logger.error(
                "API error: HTTP %s, code=%s, msg=%s",
                response.status_code,
                code,
                msg,
            )
            raise BinanceClientError(response.status_code, code, msg)

        return data

    # ── Public API methods ─────────────────────────────────────────────────

    def ping(self) -> bool:
        """
        Test connectivity to the Binance REST API.

        Returns:
            True on success.

        Raises:
            NetworkError: If the server is unreachable.
        """
        self._request("GET", "/fapi/v1/ping")
        logger.info("Ping successful – testnet is reachable.")
        return True

    def get_server_time(self) -> int:
        """
        Return the current Binance server time in milliseconds.

        Returns:
            Server timestamp in ms.
        """
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_account_info(self) -> Dict[str, Any]:
        """
        Fetch futures account information (balances, positions, …).

        Returns:
            Account info dict from Binance.
        """
        logger.info("Fetching account information …")
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Place a new futures order.

        Keyword arguments map directly to Binance POST /fapi/v1/order params.
        Common keys: symbol, side, type, quantity, price, timeInForce,
                     stopPrice, reduceOnly.

        Returns:
            Order response dict from Binance.

        Raises:
            BinanceClientError: On API-level rejections.
            NetworkError:       On connectivity failures.
        """
        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
            kwargs.get("symbol"),
            kwargs.get("side"),
            kwargs.get("type"),
            kwargs.get("quantity"),
            kwargs.get("price", "N/A"),
        )
        return self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Query the status of an existing order.

        Args:
            symbol:   Trading pair (e.g. 'BTCUSDT').
            order_id: Binance order ID.

        Returns:
            Order detail dict.
        """
        logger.info("Querying order | symbol=%s orderId=%s", symbol, order_id)
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            symbol:   Trading pair.
            order_id: Binance order ID.

        Returns:
            Cancellation response dict.
        """
        logger.info("Cancelling order | symbol=%s orderId=%s", symbol, order_id)
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Retrieve exchange trading rules and symbol filters.

        Returns:
            Exchange info dict.
        """
        return self._request("GET", "/fapi/v1/exchangeInfo")
