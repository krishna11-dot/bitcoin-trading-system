"""Yahoo Finance API client for Bitcoin market data.

This module provides a wrapper around Yahoo Finance (via yfinance library) with
rate limiting and error handling. Useful as a backup data source.

Example:
    >>> from tools.yfinance_client import YFinanceClient
    >>> client = YFinanceClient()
    >>> data = client.get_btc_data()
    >>> print(f"BTC Price: ${data.price:,.2f}")
"""

import logging
import time
from typing import Any, Dict, List, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance library not installed. YFinanceClient will not be functional.")

from data_models import MarketData
from tools.rate_limiter import yfinance_rate_limit


# Configure logger
logger = logging.getLogger(__name__)


class YFinanceClientError(Exception):
    """Base exception for YFinance client errors."""

    pass


class YFinanceClient:
    """Client for interacting with Yahoo Finance API.

    This client provides methods for fetching Bitcoin market data from Yahoo
    Finance. All API calls are rate limited to 1 call per 3 seconds.

    Example:
        >>> client = YFinanceClient()
        >>> data = client.get_btc_data(period="1d")
        >>> print(f"Price: ${data.price:,.2f}")
    """

    BTC_TICKER = "BTC-USD"

    def __init__(self):
        """Initialize YFinance client."""
        if not YFINANCE_AVAILABLE:
            logger.error(
                "yfinance library not installed. "
                "Install with: pip install yfinance"
            )
            raise YFinanceClientError("yfinance library not available")

        logger.info("Initialized YFinanceClient")

    @yfinance_rate_limit
    def get_btc_data(self, period: str = "1d") -> MarketData:
        """Get current Bitcoin market data.

        Args:
            period: Data period (1d, 5d, 1mo, 3mo, 1y, etc.)

        Returns:
            MarketData: Current market data with 24h stats

        Raises:
            YFinanceClientError: If data fetch fails

        Example:
            >>> client = YFinanceClient()
            >>> data = client.get_btc_data(period="1d")
            >>> print(f"Price: ${data.price:,.2f}")
        """
        logger.info(f"Fetching BTC data from Yahoo Finance (period={period})")

        try:
            # Fetch ticker data
            ticker = yf.Ticker(self.BTC_TICKER)

            # Get current info
            info = ticker.info

            # Get historical data for 24h change
            hist = ticker.history(period=period)

            if hist.empty:
                raise YFinanceClientError("No historical data available")

            # Get latest data point
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

            # Calculate 24h change
            current_price = latest["Close"]
            previous_price = previous["Close"]
            change_24h = ((current_price - previous_price) / previous_price) * 100

            # Create timestamp
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Create MarketData model
            market_data = MarketData(
                price=float(current_price),
                volume=float(latest["Volume"]) * current_price,  # Convert to USD volume
                timestamp=timestamp,
                change_24h=float(change_24h),
                high_24h=float(latest["High"]),
                low_24h=float(latest["Low"]),
            )

            logger.info(f"Fetched BTC data: ${market_data.price:,.2f}")

            # Add 3-second delay to respect rate limits
            time.sleep(3)

            return market_data

        except Exception as e:
            logger.error(f"Failed to fetch BTC data from Yahoo Finance: {e}")
            raise YFinanceClientError(f"Failed to fetch data: {e}")

    @yfinance_rate_limit
    def get_historical_data(
        self, period: str = "1mo", interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Get historical Bitcoin data.

        Args:
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h,
                                   1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            List of dictionaries with OHLCV data

        Raises:
            YFinanceClientError: If data fetch fails

        Example:
            >>> client = YFinanceClient()
            >>> hist = client.get_historical_data(period="1mo", interval="1d")
            >>> print(f"Fetched {len(hist)} data points")
        """
        logger.info(
            f"Fetching historical BTC data (period={period}, interval={interval})"
        )

        try:
            ticker = yf.Ticker(self.BTC_TICKER)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                raise YFinanceClientError("No historical data available")

            # Convert DataFrame to list of dictionaries
            historical_data = []
            for index, row in hist.iterrows():
                historical_data.append(
                    {
                        "timestamp": index.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]),
                    }
                )

            logger.info(f"Fetched {len(historical_data)} historical data points")

            # Add 3-second delay to respect rate limits
            time.sleep(3)

            return historical_data

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            raise YFinanceClientError(f"Failed to fetch historical data: {e}")

    @yfinance_rate_limit
    def get_info(self) -> Dict[str, Any]:
        """Get Bitcoin ticker information.

        Returns:
            Dict containing ticker information

        Raises:
            YFinanceClientError: If data fetch fails

        Example:
            >>> client = YFinanceClient()
            >>> info = client.get_info()
            >>> print(f"Market Cap: ${info.get('marketCap', 0):,.0f}")
        """
        logger.info("Fetching BTC ticker info")

        try:
            ticker = yf.Ticker(self.BTC_TICKER)
            info = ticker.info

            logger.info("Fetched BTC ticker info")

            # Add 3-second delay to respect rate limits
            time.sleep(3)

            return info

        except Exception as e:
            logger.error(f"Failed to fetch ticker info: {e}")
            raise YFinanceClientError(f"Failed to fetch info: {e}")

    def __repr__(self) -> str:
        """Return string representation of client.

        Returns:
            str: Client representation
        """
        return "YFinanceClient(ticker=BTC-USD)"
