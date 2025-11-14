"""CoinMarketCap API client for market data and sentiment.

[WARN] CRITICAL: CoinMarketCap free tier allows only 1 call per 5 minutes (288/day).
This is the primary bottleneck in the system. ALWAYS use aggressive caching.

This module provides a wrapper around the CoinMarketCap API with strict rate
limiting and aggressive caching to avoid exhausting the API quota.

Example:
    >>> from tools.coinmarketcap_client import CoinMarketCapClient
    >>> client = CoinMarketCapClient()
    >>> fg_index = client.get_fear_greed_index()  # Cached for 1 hour
    >>> print(f"Fear & Greed Index: {fg_index}")
"""

import logging
import time
from typing import Any, Dict, Optional

import requests

from config import get_settings
from data_models import SentimentData
from tools.rate_limiter import coinmarketcap_rate_limit, cache_result


# Configure logger
logger = logging.getLogger(__name__)


class CoinMarketCapClientError(Exception):
    """Base exception for CoinMarketCap client errors."""

    pass


class CoinMarketCapAPIError(CoinMarketCapClientError):
    """Raised when CoinMarketCap API returns an error response."""

    def __init__(self, status_code: int, message: str):
        """Initialize CoinMarketCap API error.

        Args:
            status_code: HTTP status code
            message: Error message from API
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"CoinMarketCap API Error {status_code}: {message}")


class CoinMarketCapClient:
    """Client for interacting with CoinMarketCap API.

    [WARN] WARNING: Free tier is EXTREMELY limited (1 call per 5 minutes).
    All methods use aggressive caching (1 hour default) to avoid exhausting quota.

    This client provides methods for fetching cryptocurrency market data and
    sentiment indicators. Every API call is logged and cached.

    Attributes:
        api_key: CoinMarketCap API key

    Example:
        >>> client = CoinMarketCapClient()
        >>> sentiment = client.get_latest_quotes("BTC")
        >>> print(f"Price: ${sentiment.price}")
    """

    BASE_URL = "https://pro-api.coinmarketcap.com"
    SANDBOX_URL = "https://sandbox-api.coinmarketcap.com"

    def __init__(self, api_key: Optional[str] = None, sandbox: bool = False):
        """Initialize CoinMarketCap client.

        Args:
            api_key: CoinMarketCap API key (defaults to config)
            sandbox: Use sandbox environment if True
        """
        settings = get_settings()

        self.api_key = api_key or settings.COINMARKETCAP_API_KEY
        self.sandbox = sandbox
        self.base_url = self.SANDBOX_URL if sandbox else self.BASE_URL

        if not self.api_key:
            logger.warning(
                "CoinMarketCap API key not configured. "
                "Client will not be functional."
            )

        logger.info(
            f"Initialized CoinMarketCapClient (sandbox={sandbox}, "
            f"[WARN] Rate limit: 1 call per 5 minutes)"
        )

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """Make HTTP request to CoinMarketCap API with retry logic.

        [WARN] Every call to this method is logged as it consumes precious API quota.

        Args:
            endpoint: API endpoint (e.g., "/v1/cryptocurrency/quotes/latest")
            params: Request parameters
            max_retries: Maximum number of retry attempts (default: 2)

        Returns:
            Dict containing API response

        Raises:
            CoinMarketCapAPIError: If API returns error response
            CoinMarketCapClientError: If request fails after retries
        """
        if not self.api_key:
            raise CoinMarketCapClientError("API key not configured")

        params = params or {}
        url = f"{self.base_url}{endpoint}"

        headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json",
        }

        # [WARN] LOG EVERY CALL - This is critical for monitoring quota usage
        logger.warning(
            f"[ALERT] CoinMarketCap API CALL: {endpoint} "
            f"([WARN] 1/288 daily calls used, params={params})"
        )

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"CoinMarketCap API: GET {endpoint} (attempt {attempt + 1}/{max_retries})"
                )

                response = requests.get(url, params=params, headers=headers, timeout=15)

                # Check for HTTP errors
                if response.status_code != 200:
                    error_msg = response.json().get("status", {}).get("error_message", "Unknown error")
                    raise CoinMarketCapAPIError(
                        status_code=response.status_code,
                        message=error_msg,
                    )

                data = response.json()

                # Check API status
                status = data.get("status", {})
                if status.get("error_code", 0) != 0:
                    raise CoinMarketCapAPIError(
                        status_code=status.get("error_code"),
                        message=status.get("error_message", "Unknown error"),
                    )

                logger.info(f"[OK] CoinMarketCap API call successful: {endpoint}")
                return data

            except requests.exceptions.Timeout:
                logger.warning(
                    f"CoinMarketCap API timeout (attempt {attempt + 1}/{max_retries})"
                )
                if attempt == max_retries - 1:
                    raise CoinMarketCapClientError("Request timed out after retries")
                time.sleep(3 * (attempt + 1))  # Exponential backoff

            except requests.exceptions.RequestException as e:
                logger.error(f"CoinMarketCap API request failed: {e}")
                if attempt == max_retries - 1:
                    raise CoinMarketCapClientError(f"Request failed: {e}")
                time.sleep(3 * (attempt + 1))  # Exponential backoff

            except CoinMarketCapAPIError:
                # Don't retry API errors (invalid params, quota exceeded, etc.)
                raise

        raise CoinMarketCapClientError("Unexpected error in request logic")

    @coinmarketcap_rate_limit
    @cache_result(ttl=3600)  # Cache for 1 hour - CRITICAL to avoid quota exhaustion
    def get_fear_greed_index(self) -> int:
        """Get Fear & Greed Index (0-100).

        [WARN] This method is cached for 1 hour to avoid exhausting API quota.

        Note: CoinMarketCap doesn't provide Fear & Greed Index directly.
        This is a placeholder that derives sentiment from market metrics.

        Returns:
            int: Fear & Greed Index (0-100)

        Raises:
            CoinMarketCapAPIError: If API returns error
            CoinMarketCapClientError: If request fails

        Example:
            >>> client = CoinMarketCapClient()
            >>> index = client.get_fear_greed_index()
            >>> print(f"Fear & Greed: {index}")
        """
        logger.info("Fetching Fear & Greed Index (derived from market metrics)")

        try:
            # Get global market metrics to derive sentiment
            data = self._make_request("/v1/global-metrics/quotes/latest")

            # Derive sentiment from market metrics
            # This is a simplified heuristic - adjust based on your needs
            btc_dominance = data["data"]["btc_dominance"]

            # Try to get 24h market cap change (field name varies across API versions)
            usd_quote = data["data"]["quote"]["USD"]
            total_market_cap_pct_change = (
                usd_quote.get("total_market_cap_change_24h") or
                usd_quote.get("total_market_cap_yesterday_percentage_change") or
                usd_quote.get("total_volume_24h_percentage_change") or
                0.0  # Default to neutral if field not found
            )

            # Simple heuristic:
            # - High BTC dominance (>50%) = Fear (money flowing to safety)
            # - Positive market cap change = Greed
            # - Negative market cap change = Fear

            base_index = 50  # Neutral
            if btc_dominance > 50:
                base_index -= (btc_dominance - 50)  # More fear
            else:
                base_index += (50 - btc_dominance)  # More greed

            # Adjust based on market cap change
            base_index += total_market_cap_pct_change * 2

            # Clamp to 0-100
            fear_greed_index = int(max(0, min(100, base_index)))

            logger.info(f"Derived Fear & Greed Index: {fear_greed_index} (BTC dominance: {btc_dominance:.2f}%)")
            return fear_greed_index

        except Exception as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            # Return neutral on error to avoid blocking system
            logger.warning("Returning neutral Fear & Greed Index (50) due to error")
            return 50

    @coinmarketcap_rate_limit
    @cache_result(ttl=3600)  # Cache for 1 hour - CRITICAL
    def get_latest_quotes(self, symbol: str = "BTC") -> SentimentData:
        """Get latest quotes and derive sentiment data for a cryptocurrency.

        [WARN] This method is cached for 1 hour to avoid exhausting API quota.

        Args:
            symbol: Cryptocurrency symbol (default: BTC)

        Returns:
            SentimentData: Market sentiment derived from price action

        Raises:
            CoinMarketCapAPIError: If API returns error
            CoinMarketCapClientError: If request fails

        Example:
            >>> client = CoinMarketCapClient()
            >>> sentiment = client.get_latest_quotes("BTC")
            >>> print(f"FG Index: {sentiment.fear_greed_index}")
        """
        logger.info(f"Fetching latest quotes for {symbol}")

        try:
            params = {"symbol": symbol, "convert": "USD"}

            data = self._make_request("/v1/cryptocurrency/quotes/latest", params)

            # Extract quote data
            quote_data = data["data"][symbol]["quote"]["USD"]

            # Derive sentiment from price metrics
            price_change_24h = quote_data["percent_change_24h"]
            price_change_7d = quote_data["percent_change_7d"]
            volume_change_24h = quote_data.get("volume_change_24h", 0)

            # Derive Fear & Greed Index from price action
            # Positive change = Greed, Negative change = Fear
            base_fg = 50  # Neutral
            base_fg += price_change_24h * 2  # 24h impact
            base_fg += price_change_7d * 0.5  # 7d impact (lower weight)
            fear_greed_index = int(max(0, min(100, base_fg)))

            # Derive social volume from trading volume change
            if volume_change_24h > 50:
                social_volume = "high"
            elif volume_change_24h < -20:
                social_volume = "low"
            else:
                social_volume = "medium"

            # Derive news sentiment from price momentum
            # Strong positive momentum = positive news sentiment
            news_sentiment = max(-1.0, min(1.0, price_change_24h / 10))

            # Create timestamp
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            sentiment_data = SentimentData(
                fear_greed_index=fear_greed_index,
                social_volume=social_volume,
                news_sentiment=news_sentiment,
                trending_score=None,  # Not available from CMC
                timestamp=timestamp,
            )

            logger.info(
                f"Derived sentiment for {symbol}: FG={fear_greed_index}, "
                f"news={news_sentiment:.2f}"
            )

            return sentiment_data

        except Exception as e:
            logger.error(f"Failed to fetch latest quotes for {symbol}: {e}")
            raise

    @coinmarketcap_rate_limit
    @cache_result(ttl=3600)  # Cache for 1 hour - CRITICAL
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global cryptocurrency market metrics.

        [WARN] This method is cached for 1 hour to avoid exhausting API quota.

        Returns:
            Dict containing global market metrics

        Raises:
            CoinMarketCapAPIError: If API returns error
            CoinMarketCapClientError: If request fails

        Example:
            >>> client = CoinMarketCapClient()
            >>> metrics = client.get_global_metrics()
            >>> print(f"Total Market Cap: ${metrics['total_market_cap']:,.0f}")
        """
        logger.info("Fetching global market metrics")

        try:
            data = self._make_request("/v1/global-metrics/quotes/latest")

            usd_quote = data["data"]["quote"]["USD"]

            # Try multiple field names for 24h change (API field names vary)
            total_market_cap_change = (
                usd_quote.get("total_market_cap_change_24h") or
                usd_quote.get("total_market_cap_yesterday_percentage_change") or
                usd_quote.get("total_volume_24h_percentage_change") or
                0.0
            )

            metrics = {
                "btc_dominance": data["data"]["btc_dominance"],
                "eth_dominance": data["data"]["eth_dominance"],
                "total_market_cap": usd_quote["total_market_cap"],
                "total_volume_24h": usd_quote["total_volume_24h"],
                "total_market_cap_change_24h": total_market_cap_change,
                "last_updated": data["data"]["last_updated"],
            }

            logger.info(
                f"Global metrics: BTC dominance={metrics['btc_dominance']:.1f}%, "
                f"Market cap=${metrics['total_market_cap']:,.0f}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to fetch global metrics: {e}")
            raise

    def get_api_usage_stats(self) -> str:
        """Get API usage statistics (reminder about quota).

        Returns:
            str: Usage statistics and warnings

        Example:
            >>> client = CoinMarketCapClient()
            >>> print(client.get_api_usage_stats())
        """
        return (
            "[WARN] CoinMarketCap Free Tier Limits:\n"
            "- 1 call per 5 minutes (333 calls per day)\n"
            "- ALWAYS use caching (1 hour recommended)\n"
            "- Monitor logs for [ALERT] API CALL warnings\n"
            "- Upgrade to paid tier if quota exhausted"
        )

    def __repr__(self) -> str:
        """Return string representation of client.

        Returns:
            str: Client representation
        """
        return f"CoinMarketCapClient(sandbox={self.sandbox}, [WARN] Rate limit: 1/5min)"
