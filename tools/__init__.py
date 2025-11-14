"""Agent tools and external integrations.

This module contains tools that agents use to interact with external
services, perform calculations, and access data.

Files in this directory:
- rate_limiter.py: Smart rate limiting with circuit breakers and caching
- binance_client.py: Binance exchange API client
- coinmarketcap_client.py: CoinMarketCap market data client
- yfinance_client.py: Yahoo Finance data client
- bitcoin_onchain_analyzer.py: FREE on-chain analytics (Blockchain.com API)
- huggingface_client.py: HuggingFace LLM inference client
- openrouter_client.py: OpenRouter LLM inference client (backup)
- indicator_calculator.py: Technical indicator calculations (RSI, MACD, ATR, etc.)
- csv_rag_pipeline.py: CSV-based RAG for historical pattern matching
- google_sheets_sync.py: Dynamic configuration from Google Sheets

Example:
    >>> from tools import BinanceClient, cache_result
    >>> from tools import HuggingFaceClient
    >>>
    >>> binance = BinanceClient()
    >>> price_data = binance.get_current_price("BTCUSDT")
    >>>
    >>> llm = HuggingFaceClient()
    >>> analysis = llm.generate_text("Analyze market conditions")
"""

from typing import List

# Import rate limiting components
from tools.rate_limiter import (
    SmartRateLimiter,
    RateLimitExceeded,
    CircuitBreakerOpen,
    binance_rate_limit,
    coinmarketcap_rate_limit,
    yfinance_rate_limit,
    huggingface_rate_limit,
    openrouter_rate_limit,
    google_sheets_rate_limit,
    cache_result,
    clear_cache,
    get_all_rate_limit_stats,
    print_rate_limit_dashboard,
)

# Import API clients
from tools.binance_client import BinanceClient, BinanceClientError, BinanceAPIError
from tools.coinmarketcap_client import (
    CoinMarketCapClient,
    CoinMarketCapClientError,
    CoinMarketCapAPIError,
)
from tools.yfinance_client import YFinanceClient, YFinanceClientError
from tools.huggingface_client import (
    HuggingFaceClient,
    HuggingFaceAPIError,
)
from tools.openrouter_client import (
    OpenRouterClient,
    OpenRouterClientError,
    OpenRouterAPIError,
)

# Import indicator calculator
from tools.indicator_calculator import (
    calculate_rsi,
    calculate_macd,
    calculate_atr,
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_all_indicators,
    validate_price_data,
)

# Import RAG engine
from tools.csv_rag_pipeline import RAGRetriever

# Import Google Sheets sync
from tools.google_sheets_sync import GoogleSheetsSync, GoogleSheetsSyncError

__all__: List[str] = [
    # Rate limiter class
    "SmartRateLimiter",
    # Exceptions
    "RateLimitExceeded",
    "CircuitBreakerOpen",
    # Preconfigured rate limiters
    "binance_rate_limit",
    "coinmarketcap_rate_limit",
    "yfinance_rate_limit",
    "huggingface_rate_limit",
    "openrouter_rate_limit",
    "google_sheets_rate_limit",
    # Caching utilities
    "cache_result",
    "clear_cache",
    # Statistics and monitoring
    "get_all_rate_limit_stats",
    "print_rate_limit_dashboard",
    # API Clients
    "BinanceClient",
    "BinanceClientError",
    "BinanceAPIError",
    "CoinMarketCapClient",
    "CoinMarketCapClientError",
    "CoinMarketCapAPIError",
    "YFinanceClient",
    "YFinanceClientError",
    "HuggingFaceClient",
    "HuggingFaceClientError",
    "HuggingFaceAPIError",
    "OpenRouterClient",
    "OpenRouterClientError",
    "OpenRouterAPIError",
    # Indicator Calculator
    "calculate_rsi",
    "calculate_macd",
    "calculate_atr",
    "calculate_sma",
    "calculate_ema",
    "calculate_bollinger_bands",
    "calculate_all_indicators",
    "validate_price_data",
    # RAG Engine
    "RAGRetriever",
    # Google Sheets Sync
    "GoogleSheetsSync",
    "GoogleSheetsSyncError",
]
