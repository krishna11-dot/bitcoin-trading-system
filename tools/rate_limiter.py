"""Smart rate limiting with circuit breakers and caching for API calls.

This module provides intelligent rate limiting for various external APIs used by
the trading system. It includes circuit breakers to prevent cascading failures,
exponential backoff, usage statistics, and a caching layer to minimize API calls.

CRITICAL: CoinMarketCap has extremely restrictive rate limits (1 call per 5 minutes).
Always use caching when possible to avoid hitting rate limits.

Example:
    >>> from tools.rate_limiter import coinmarketcap_rate_limit, cache_result
    >>>
    >>> @coinmarketcap_rate_limit
    >>> @cache_result(ttl=300)  # Cache for 5 minutes
    >>> def fetch_bitcoin_price():
    ...     return api.get_price("BTC")
"""

import functools
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, Optional, TypeVar

from config.settings import get_settings


# Configure logger
logger = logging.getLogger(__name__)

# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Custom Exceptions
# ============================================================================


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded.

    This exception is raised when a function call would exceed the configured
    rate limit. The caller should wait before retrying.

    Attributes:
        wait_time: Seconds to wait before the next call is allowed
        limiter_name: Name of the rate limiter that triggered
    """

    def __init__(self, wait_time: float, limiter_name: str):
        """Initialize rate limit exception.

        Args:
            wait_time: Seconds to wait before retry
            limiter_name: Name of the rate limiter
        """
        self.wait_time = wait_time
        self.limiter_name = limiter_name
        super().__init__(
            f"Rate limit exceeded for {limiter_name}. "
            f"Wait {wait_time:.1f}s before retrying."
        )


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open due to repeated failures.

    This exception is raised when the circuit breaker opens after multiple
    consecutive failures. The circuit will automatically reset after a cooldown.

    Attributes:
        limiter_name: Name of the rate limiter with open circuit
        failures: Number of consecutive failures
        cooldown_until: Timestamp when circuit will reset
    """

    def __init__(self, limiter_name: str, failures: int, cooldown_until: float):
        """Initialize circuit breaker exception.

        Args:
            limiter_name: Name of the rate limiter
            failures: Number of consecutive failures
            cooldown_until: Unix timestamp when circuit resets
        """
        self.limiter_name = limiter_name
        self.failures = failures
        self.cooldown_until = cooldown_until
        wait_time = cooldown_until - time.time()
        super().__init__(
            f"Circuit breaker open for {limiter_name} after {failures} failures. "
            f"Retry in {wait_time:.1f}s."
        )


# ============================================================================
# Circuit Breaker State
# ============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


# ============================================================================
# Rate Limiter Statistics
# ============================================================================


@dataclass
class RateLimiterStats:
    """Statistics for a rate limiter.

    Attributes:
        name: Rate limiter name
        max_calls: Maximum calls allowed per period
        period: Time period in seconds
        current_calls: Current number of calls in window
        usage_pct: Usage as percentage (0-100)
        circuit_state: Current circuit breaker state
        consecutive_failures: Number of consecutive failures
        total_calls: Total calls made since initialization
        total_waits: Total number of times caller had to wait
        average_wait_time: Average wait time in seconds
    """

    name: str
    max_calls: int
    period: int
    current_calls: int
    usage_pct: float
    circuit_state: CircuitState
    consecutive_failures: int
    total_calls: int
    total_waits: int
    average_wait_time: float


# ============================================================================
# Smart Rate Limiter
# ============================================================================


class SmartRateLimiter:
    """Smart rate limiter with circuit breaker and usage tracking.

    This class implements a sliding window rate limiter with:
    - Circuit breaker pattern to prevent cascading failures
    - Exponential backoff on repeated failures
    - Usage statistics and warnings
    - Automatic cleanup of old call records

    Example:
        >>> limiter = SmartRateLimiter(max_calls=100, period=60, name="binance")
        >>>
        >>> @limiter
        >>> def call_binance_api():
        ...     return binance.get_price()
    """

    def __init__(
        self,
        max_calls: int,
        period: int,
        name: str,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_timeout: int = 60,
    ):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed per period
            period: Time period in seconds
            name: Human-readable name for this rate limiter
            circuit_breaker_threshold: Number of failures before opening circuit
            circuit_breaker_timeout: Seconds to wait before closing circuit
        """
        self.max_calls = max_calls
        self.period = period
        self.name = name
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Sliding window of call timestamps
        self._call_times: Deque[float] = deque()

        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._circuit_opened_at: Optional[float] = None

        # Statistics
        self._total_calls = 0
        self._total_waits = 0
        self._total_wait_time = 0.0

        # Warning threshold (80% usage)
        self._warning_threshold = 0.80

        logger.info(
            f"Initialized rate limiter '{name}': "
            f"{max_calls} calls per {period}s "
            f"(circuit breaker: {circuit_breaker_threshold} failures)"
        )

    def _clean_old_calls(self) -> None:
        """Remove call timestamps outside the current window.

        This method maintains the sliding window by removing timestamps
        that are older than the rate limit period.
        """
        current_time = time.time()
        cutoff_time = current_time - self.period

        # Remove timestamps older than the window
        while self._call_times and self._call_times[0] < cutoff_time:
            self._call_times.popleft()

    def _check_circuit_breaker(self) -> None:
        """Check circuit breaker state and update if needed.

        Raises:
            CircuitBreakerOpen: If circuit is open and cooldown not expired
        """
        if self._circuit_state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if self._circuit_opened_at is not None:
                cooldown_expires = self._circuit_opened_at + self.circuit_breaker_timeout

                if time.time() >= cooldown_expires:
                    # Try half-open state (allow one test call)
                    self._circuit_state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker for '{self.name}' entering HALF_OPEN state")
                else:
                    # Still in cooldown
                    raise CircuitBreakerOpen(
                        self.name, self._consecutive_failures, cooldown_expires
                    )

    def _open_circuit_breaker(self) -> None:
        """Open circuit breaker after repeated failures."""
        self._circuit_state = CircuitState.OPEN
        self._circuit_opened_at = time.time()
        logger.error(
            f"Circuit breaker OPENED for '{self.name}' after "
            f"{self._consecutive_failures} consecutive failures"
        )

    def _close_circuit_breaker(self) -> None:
        """Close circuit breaker after successful call."""
        if self._circuit_state != CircuitState.CLOSED:
            self._circuit_state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._circuit_opened_at = None
            logger.info(f"Circuit breaker CLOSED for '{self.name}' (service recovered)")

    def record_failure(self) -> None:
        """Record a failed API call.

        Increments failure counter and opens circuit breaker if threshold reached.
        """
        self._consecutive_failures += 1

        if self._consecutive_failures >= self.circuit_breaker_threshold:
            self._open_circuit_breaker()
        else:
            logger.warning(
                f"API call failed for '{self.name}' "
                f"({self._consecutive_failures}/{self.circuit_breaker_threshold} failures)"
            )

    def record_success(self) -> None:
        """Record a successful API call.

        Resets failure counter and closes circuit breaker if open.
        """
        if self._consecutive_failures > 0:
            logger.info(
                f"API call succeeded for '{self.name}' after "
                f"{self._consecutive_failures} failures"
            )
        self._close_circuit_breaker()

    def can_make_call(self) -> bool:
        """Check if a call can be made without exceeding rate limit.

        Returns:
            bool: True if call can be made, False if rate limit would be exceeded
        """
        self._clean_old_calls()
        return len(self._call_times) < self.max_calls

    def calculate_wait_time(self) -> float:
        """Calculate seconds to wait before next call is allowed.

        Returns:
            float: Seconds to wait (0.0 if call can be made immediately)
        """
        self._clean_old_calls()

        if self.can_make_call():
            return 0.0

        # Calculate when the oldest call will expire
        oldest_call_time = self._call_times[0]
        wait_time = (oldest_call_time + self.period) - time.time()

        return max(0.0, wait_time)

    def wait_if_needed(self) -> None:
        """Block until a call can be made within rate limit.

        This method will sleep if necessary to respect the rate limit.
        """
        wait_time = self.calculate_wait_time()

        if wait_time > 0:
            self._total_waits += 1
            self._total_wait_time += wait_time

            logger.warning(
                f"Rate limit reached for '{self.name}'. Waiting {wait_time:.1f}s..."
            )
            time.sleep(wait_time)

    def _check_usage_warning(self) -> None:
        """Log warning if usage exceeds threshold (80%)."""
        self._clean_old_calls()
        current_usage = len(self._call_times) / self.max_calls

        if current_usage >= self._warning_threshold:
            logger.warning(
                f"Rate limiter '{self.name}' at {current_usage:.0%} capacity "
                f"({len(self._call_times)}/{self.max_calls} calls)"
            )

    def _record_call(self) -> None:
        """Record that a call was made."""
        current_time = time.time()
        self._call_times.append(current_time)
        self._total_calls += 1
        self._check_usage_warning()

    def get_usage_stats(self) -> RateLimiterStats:
        """Get current usage statistics for this rate limiter.

        Returns:
            RateLimiterStats: Current statistics

        Example:
            >>> stats = limiter.get_usage_stats()
            >>> print(f"Usage: {stats.usage_pct:.1f}%")
        """
        self._clean_old_calls()
        current_calls = len(self._call_times)
        usage_pct = (current_calls / self.max_calls) * 100

        avg_wait = (
            self._total_wait_time / self._total_waits if self._total_waits > 0 else 0.0
        )

        return RateLimiterStats(
            name=self.name,
            max_calls=self.max_calls,
            period=self.period,
            current_calls=current_calls,
            usage_pct=usage_pct,
            circuit_state=self._circuit_state,
            consecutive_failures=self._consecutive_failures,
            total_calls=self._total_calls,
            total_waits=self._total_waits,
            average_wait_time=avg_wait,
        )

    def __call__(self, func: F) -> F:
        """Decorator to apply rate limiting to a function.

        Args:
            func: Function to rate limit

        Returns:
            Wrapped function with rate limiting

        Example:
            >>> @binance_rate_limit
            >>> def get_btc_price():
            ...     return api.get_price()
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check circuit breaker
            self._check_circuit_breaker()

            # Wait if needed to respect rate limit
            self.wait_if_needed()

            # Record the call
            self._record_call()

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Record success (for circuit breaker)
                self.record_success()

                return result

            except Exception as e:
                # Record failure (for circuit breaker)
                self.record_failure()
                raise

        return wrapper  # type: ignore


# ============================================================================
# Preconfigured Rate Limiters
# ============================================================================

# Load settings to get rate limits
settings = get_settings()

# Binance Exchange API: 100 calls per 60 seconds
# Generous limit for spot trading
binance_rate_limit = SmartRateLimiter(
    max_calls=settings.BINANCE_RATE_LIMIT,
    period=settings.BINANCE_RATE_WINDOW,
    name="Binance",
    circuit_breaker_threshold=5,  # More tolerant for high-volume API
    circuit_breaker_timeout=30,
)

# CoinMarketCap API: 1 call per 300 seconds (5 minutes)
# CRITICAL BOTTLENECK - Free tier is extremely restrictive
# ALWAYS use caching to minimize calls
coinmarketcap_rate_limit = SmartRateLimiter(
    max_calls=settings.COINMARKETCAP_RATE_LIMIT,
    period=settings.COINMARKETCAP_RATE_WINDOW,
    name="CoinMarketCap",
    circuit_breaker_threshold=2,  # Very strict - fail fast
    circuit_breaker_timeout=600,  # 10 minute cooldown
)

# Yahoo Finance API: 1 call per 3 seconds
# Conservative estimate for free tier
yfinance_rate_limit = SmartRateLimiter(
    max_calls=settings.YFINANCE_RATE_LIMIT,
    period=settings.YFINANCE_RATE_WINDOW,
    name="YFinance",
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=60,
)

# NOTE: On-chain analytics now uses FREE Blockchain.com API (no rate limiter needed)
# See tools/bitcoin_onchain_analyzer.py

# HuggingFace Inference API: 150 calls per 60 seconds
# Primary LLM inference API
huggingface_rate_limit = SmartRateLimiter(
    max_calls=settings.HUGGINGFACE_RATE_LIMIT,
    period=settings.HUGGINGFACE_RATE_WINDOW,
    name="HuggingFace",
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60,
)

# OpenRouter API: 15 calls per 60 seconds
# Free tier for Mistral-7B
openrouter_rate_limit = SmartRateLimiter(
    max_calls=settings.OPENROUTER_RATE_LIMIT,
    period=settings.OPENROUTER_RATE_WINDOW,
    name="OpenRouter",
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=120,
)

# Google Sheets API: 1 call per 60 seconds
# Conservative limit (actual API limit is 60 reads/min per user)
# Fetching once per hour = 24 calls/day (0.03% of quota)
google_sheets_rate_limit = SmartRateLimiter(
    max_calls=settings.GOOGLE_SHEETS_RATE_LIMIT,
    period=settings.GOOGLE_SHEETS_RATE_WINDOW,
    name="GoogleSheets",
    circuit_breaker_threshold=3,  # Tolerate a few failures
    circuit_breaker_timeout=300,  # 5 minute cooldown
)


# ============================================================================
# Caching Decorator
# ============================================================================


# Simple in-memory cache (no external dependencies)
_cache: Dict[str, Dict[str, Any]] = {}


def cache_result(ttl: int = 3600) -> Callable[[F], F]:
    """Decorator to cache function results for a specified time-to-live.

    This is critical for APIs with extremely restrictive rate limits like
    CoinMarketCap. Always cache when possible to minimize API calls.

    Args:
        ttl: Time-to-live in seconds (default: 3600 = 1 hour)

    Returns:
        Decorator function

    Example:
        >>> @coinmarketcap_rate_limit
        >>> @cache_result(ttl=300)  # Cache for 5 minutes
        >>> def get_bitcoin_price():
        ...     return api.get_price("BTC")
    """

    def decorator(func: F) -> F:
        cache_key = f"{func.__module__}.{func.__qualname__}"

        # Initialize cache entry for this function
        if cache_key not in _cache:
            _cache[cache_key] = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a hashable key from args and kwargs
            # Note: This is a simple implementation. For complex objects,
            # consider using pickle or json serialization
            args_key = str(args) + str(sorted(kwargs.items()))

            cache_entry = _cache[cache_key]
            current_time = time.time()

            # Check if result is cached and not expired
            if args_key in cache_entry:
                cached_result, cached_time = cache_entry[args_key]
                age = current_time - cached_time

                if age < ttl:
                    logger.debug(
                        f"Cache HIT for {func.__name__} (age: {age:.1f}s, TTL: {ttl}s)"
                    )
                    return cached_result
                else:
                    logger.debug(
                        f"Cache EXPIRED for {func.__name__} (age: {age:.1f}s, TTL: {ttl}s)"
                    )

            # Cache miss or expired - call function
            logger.debug(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)

            # Store result in cache
            cache_entry[args_key] = (result, current_time)

            return result

        return wrapper  # type: ignore

    return decorator


def clear_cache(func: Optional[Callable] = None) -> None:
    """Clear cached results for a function or all functions.

    Args:
        func: Function to clear cache for (None = clear all)

    Example:
        >>> clear_cache(get_bitcoin_price)  # Clear specific function
        >>> clear_cache()  # Clear all caches
    """
    if func is None:
        _cache.clear()
        logger.info("Cleared all function caches")
    else:
        cache_key = f"{func.__module__}.{func.__qualname__}"
        if cache_key in _cache:
            _cache[cache_key].clear()
            logger.info(f"Cleared cache for {func.__name__}")


# ============================================================================
# Global Statistics
# ============================================================================


def get_all_rate_limit_stats() -> Dict[str, RateLimiterStats]:
    """Get usage statistics for all rate limiters.

    Returns:
        Dict mapping rate limiter name to statistics

    Example:
        >>> stats = get_all_rate_limit_stats()
        >>> for name, stat in stats.items():
        ...     print(f"{name}: {stat.usage_pct:.1f}% usage")
    """
    all_limiters = [
        binance_rate_limit,
        coinmarketcap_rate_limit,
        yfinance_rate_limit,
        huggingface_rate_limit,
        openrouter_rate_limit,
        google_sheets_rate_limit,
    ]

    return {limiter.name: limiter.get_usage_stats() for limiter in all_limiters}


def print_rate_limit_dashboard() -> None:
    """Print a formatted dashboard of all rate limiter statistics.

    Useful for monitoring and debugging rate limit usage.

    Example:
        >>> print_rate_limit_dashboard()
        Rate Limiter Dashboard
        =====================
        Binance:         5/100 calls (5.0%)  [CLOSED] Total: 1234
        CoinMarketCap:   1/1 calls (100.0%)  [CLOSED] Total: 45  ⚠️ CRITICAL
        ...
    """
    stats = get_all_rate_limit_stats()

    print("\n" + "=" * 80)
    print("Rate Limiter Dashboard")
    print("=" * 80)

    for name, stat in stats.items():
        circuit_emoji = {
            CircuitState.CLOSED: "✓",
            CircuitState.OPEN: "✗",
            CircuitState.HALF_OPEN: "~",
        }[stat.circuit_state]

        warning = ""
        if stat.usage_pct >= 80:
            warning = "  ⚠️ HIGH USAGE"
        if stat.circuit_state == CircuitState.OPEN:
            warning = "  🚨 CIRCUIT OPEN"

        print(
            f"{name:20} {stat.current_calls:3}/{stat.max_calls:3} calls "
            f"({stat.usage_pct:5.1f}%)  [{circuit_emoji}] "
            f"Total: {stat.total_calls:6}{warning}"
        )

    print("=" * 80 + "\n")


# ============================================================================
# Example Usage
# ============================================================================


if __name__ == "__main__":
    # Example: Using rate limiter with caching
    @coinmarketcap_rate_limit
    @cache_result(ttl=300)  # Cache for 5 minutes
    def fetch_bitcoin_data() -> Dict[str, Any]:
        """Fetch Bitcoin data from CoinMarketCap (rate limited and cached)."""
        print("Making actual API call to CoinMarketCap...")
        # Simulate API call
        time.sleep(0.1)
        return {"price": 45000.0, "volume": 1000000.0}

    # First call - will hit API and cache result
    result1 = fetch_bitcoin_data()
    print(f"Result 1: {result1}")

    # Second call - will use cached result
    result2 = fetch_bitcoin_data()
    print(f"Result 2: {result2}")

    # Print dashboard
    print_rate_limit_dashboard()
