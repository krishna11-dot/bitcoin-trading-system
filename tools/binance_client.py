"""Binance API client for cryptocurrency trading and market data.

This module provides a wrapper around the Binance exchange API with rate
limiting, error handling, and automatic retries. All methods return Pydantic
models for type safety.

Example:
    >>> from tools.binance_client import BinanceClient
    >>> client = BinanceClient(api_key="...", api_secret="...")
    >>> market_data = client.get_current_price("BTCUSDT")
    >>> print(f"BTC Price: ${market_data.price:,.2f}")
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from config import get_settings
from data_models import MarketData
from tools.rate_limiter import binance_rate_limit


# Configure logger
logger = logging.getLogger(__name__)


class BinanceClientError(Exception):
    """Base exception for Binance client errors."""

    pass


class BinanceAPIError(BinanceClientError):
    """Raised when Binance API returns an error response."""

    def __init__(self, code: int, message: str):
        """Initialize Binance API error.

        Args:
            code: Binance error code
            message: Error message from API
        """
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceClient:
    """Client for interacting with Binance exchange API.

    This client provides methods for fetching market data, account information,
    and placing orders. All API calls are rate limited and include automatic
    retry logic.

    Attributes:
        api_key: Binance API key
        api_secret: Binance API secret
        testnet: Whether to use testnet (default from settings)

    Example:
        >>> client = BinanceClient()
        >>> price_data = client.get_current_price("BTCUSDT")
        >>> print(f"Price: ${price_data.price:,.2f}")
    """

    BASE_URL = "https://api.binance.com"
    TESTNET_URL = "https://testnet.binance.vision"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: Optional[bool] = None,
    ):
        """Initialize Binance client.

        Args:
            api_key: Binance API key (defaults to config)
            api_secret: Binance API secret (defaults to config)
            testnet: Use testnet if True (defaults to config)
        """
        settings = get_settings()

        self.api_key = api_key or settings.BINANCE_API_KEY
        self.api_secret = api_secret or settings.BINANCE_API_SECRET
        self.testnet = testnet if testnet is not None else settings.TESTNET_MODE

        self.base_url = self.TESTNET_URL if self.testnet else self.BASE_URL

        # Validate credentials
        if not self.api_key or not self.api_secret:
            logger.warning(
                "Binance API credentials not configured. "
                "Some functionality will be unavailable."
            )

        logger.info(
            f"Initialized BinanceClient (testnet={self.testnet}, "
            f"base_url={self.base_url})"
        )

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for authenticated requests.

        Args:
            params: Request parameters to sign

        Returns:
            str: HMAC SHA256 signature
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make HTTP request to Binance API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v3/ticker/price")
            params: Request parameters
            signed: Whether request requires signature
            max_retries: Maximum number of retry attempts

        Returns:
            Dict containing API response

        Raises:
            BinanceAPIError: If API returns error response
            BinanceClientError: If request fails after retries
        """
        params = params or {}
        url = f"{self.base_url}{endpoint}"

        # Add timestamp and signature for signed requests
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

        # Set headers
        headers = {"X-MBX-APIKEY": self.api_key} if self.api_key else {}

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.debug(f"Binance API: {method} {endpoint} (attempt {attempt + 1})")

                if method.upper() == "GET":
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                elif method.upper() == "POST":
                    response = requests.post(url, params=params, headers=headers, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for HTTP errors
                if response.status_code != 200:
                    error_data = response.json()
                    raise BinanceAPIError(
                        code=error_data.get("code", response.status_code),
                        message=error_data.get("msg", "Unknown error"),
                    )

                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Binance API timeout (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise BinanceClientError("Request timed out after retries")
                time.sleep(2**attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                logger.error(f"Binance API request failed: {e}")
                if attempt == max_retries - 1:
                    raise BinanceClientError(f"Request failed: {e}")
                time.sleep(2**attempt)  # Exponential backoff

            except BinanceAPIError:
                # Don't retry API errors (invalid params, etc.)
                raise

        raise BinanceClientError("Unexpected error in request logic")

    @binance_rate_limit
    def get_current_price(self, symbol: str = "BTCUSDT") -> MarketData:
        """Get current price and 24-hour statistics for a symbol.

        Args:
            symbol: Trading pair symbol (default: BTCUSDT)

        Returns:
            MarketData: Current market data with 24h stats

        Raises:
            BinanceAPIError: If API returns error
            BinanceClientError: If request fails

        Example:
            >>> client = BinanceClient()
            >>> data = client.get_current_price("BTCUSDT")
            >>> print(f"Price: ${data.price:,.2f}")
        """
        logger.info(f"Fetching current price for {symbol}")

        try:
            # Get 24hr ticker statistics
            data = self._make_request("GET", "/api/v3/ticker/24hr", {"symbol": symbol})

            # Parse timestamp
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(data["closeTime"] / 1000))

            # Create MarketData model
            market_data = MarketData(
                price=float(data["lastPrice"]),
                volume=float(data["quoteVolume"]),  # Volume in quote asset (USD)
                timestamp=timestamp,
                change_24h=float(data["priceChangePercent"]),
                high_24h=float(data["highPrice"]),
                low_24h=float(data["lowPrice"]),
            )

            logger.info(f"Fetched {symbol}: ${market_data.price:,.2f}")
            return market_data

        except Exception as e:
            logger.error(f"Failed to fetch current price for {symbol}: {e}")
            raise

    @binance_rate_limit
    def get_24h_stats(self, symbol: str = "BTCUSDT") -> MarketData:
        """Get 24-hour statistics for a symbol.

        This is an alias for get_current_price() for clarity.

        Args:
            symbol: Trading pair symbol (default: BTCUSDT)

        Returns:
            MarketData: 24-hour market statistics
        """
        return self.get_current_price(symbol)

    @binance_rate_limit
    def get_historical_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1h",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get historical kline/candlestick data.

        Args:
            symbol: Trading pair symbol (default: BTCUSDT)
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to fetch (max 1000)

        Returns:
            List of kline dictionaries with OHLCV data

        Raises:
            BinanceAPIError: If API returns error
            BinanceClientError: If request fails

        Example:
            >>> client = BinanceClient()
            >>> klines = client.get_historical_klines("BTCUSDT", "1h", 24)
            >>> print(f"Fetched {len(klines)} hourly candles")
        """
        logger.info(f"Fetching historical klines for {symbol} ({interval}, limit={limit})")

        try:
            params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}

            data = self._make_request("GET", "/api/v3/klines", params)

            # Parse kline data
            klines = []
            for kline in data:
                klines.append(
                    {
                        "open_time": kline[0],
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                        "close_time": kline[6],
                        "quote_volume": float(kline[7]),
                        "trades": kline[8],
                    }
                )

            logger.info(f"Fetched {len(klines)} klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Failed to fetch historical klines for {symbol}: {e}")
            raise

    @binance_rate_limit
    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance for all assets.

        Returns:
            Dict mapping asset symbol to balance

        Raises:
            BinanceAPIError: If API returns error
            BinanceClientError: If request fails or credentials missing

        Example:
            >>> client = BinanceClient()
            >>> balances = client.get_account_balance()
            >>> print(f"BTC: {balances.get('BTC', 0):.8f}")
            >>> print(f"USDT: {balances.get('USDT', 0):.2f}")
        """
        if not self.api_key or not self.api_secret:
            raise BinanceClientError("API credentials required for account operations")

        logger.info("Fetching account balance")

        try:
            data = self._make_request("GET", "/api/v3/account", signed=True)

            # Parse balances (only include non-zero)
            balances = {}
            for balance in data["balances"]:
                asset = balance["asset"]
                free = float(balance["free"])
                locked = float(balance["locked"])
                total = free + locked

                if total > 0:
                    balances[asset] = total

            logger.info(f"Fetched balances for {len(balances)} assets")
            return balances

        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            raise

    @binance_rate_limit
    def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> Dict[str, Any]:
        """Place a market order.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            side: Order side ("BUY" or "SELL")
            quantity: Order quantity in base asset

        Returns:
            Dict containing order details

        Raises:
            BinanceAPIError: If API returns error
            BinanceClientError: If request fails or credentials missing

        Example:
            >>> client = BinanceClient()
            >>> order = client.place_market_order("BTCUSDT", "BUY", 0.001)
            >>> print(f"Order ID: {order['orderId']}")
        """
        if not self.api_key or not self.api_secret:
            raise BinanceClientError("API credentials required for trading operations")

        side = side.upper()
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid order side: {side}. Must be 'BUY' or 'SELL'")

        logger.info(f"Placing market order: {side} {quantity} {symbol}")

        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": quantity,
            }

            order_result = self._make_request("POST", "/api/v3/order", params, signed=True)

            logger.info(
                f"Order placed successfully: {side} {quantity} {symbol} "
                f"(orderId: {order_result['orderId']})"
            )

            return order_result

        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            raise

    def get_server_time(self) -> int:
        """Get Binance server time in milliseconds.

        Returns:
            int: Server timestamp in milliseconds

        Example:
            >>> client = BinanceClient()
            >>> server_time = client.get_server_time()
            >>> print(f"Server time: {server_time}")
        """
        try:
            data = self._make_request("GET", "/api/v3/time")
            return data["serverTime"]
        except Exception as e:
            logger.error(f"Failed to get server time: {e}")
            raise

    def __repr__(self) -> str:
        """Return string representation of client.

        Returns:
            str: Client representation
        """
        return f"BinanceClient(testnet={self.testnet})"
