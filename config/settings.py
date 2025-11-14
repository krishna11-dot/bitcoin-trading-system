"""Configuration settings management for the Bitcoin trading system.

This module provides a singleton Settings class that loads and validates
all configuration parameters from environment variables. It includes API keys,
rate limits, trading parameters, and system configuration.

Example:
    >>> from config.settings import Settings
    >>> settings = Settings.get_instance()
    >>> print(settings.BINANCE_API_KEY)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Load environment variables from .env file
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


@dataclass
class Settings:
    """Application settings loaded from environment variables.

    This class uses the singleton pattern to ensure only one instance exists.
    All configuration values are loaded from environment variables and validated
    during initialization.

    Attributes:
        # API Keys
        HUGGINGFACE_API_KEY: HuggingFace API key for LLM inference
        OPENROUTER_API_KEY: OpenRouter API key for backup LLM access
        BINANCE_API_KEY: Binance exchange API key
        BINANCE_API_SECRET: Binance exchange API secret
        COINMARKETCAP_API_KEY: CoinMarketCap API key for market data
        TELEGRAM_BOT_TOKEN: Telegram bot token for alerts
        TELEGRAM_CHAT_ID: Telegram chat ID for notifications
        GOOGLE_SHEET_URL: Google Sheets URL for dynamic configuration

        # Rate Limits (calls per time window)
        BINANCE_RATE_LIMIT: Max API calls per 60 seconds (default: 100)
        COINMARKETCAP_RATE_LIMIT: Max API calls per 300 seconds (default: 1)
        YFINANCE_RATE_LIMIT: Max API calls per 3 seconds (default: 1)
        HUGGINGFACE_RATE_LIMIT: Max API calls per 60 seconds (default: 150)
        OPENROUTER_RATE_LIMIT: Max API calls per 60 seconds (default: 15)

        # Trading Parameters
        DCA_THRESHOLD: Price drop percentage to trigger DCA buy (default: 3.0%)
        ATR_MULTIPLIER: ATR multiplier for stop-loss calculation (default: 1.5)
        MAX_POSITION_SIZE: Maximum single position size as portfolio fraction (default: 0.20)
        MAX_TOTAL_EXPOSURE: Maximum total exposure as portfolio fraction (default: 0.80)
        EMERGENCY_STOP_LOSS: Emergency stop-loss percentage (default: 0.25 = 25%)
        MAX_TRADES_PER_HOUR: Maximum number of trades per hour (default: 5)

        # System Configuration
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        TESTNET_MODE: Use testnet/paper trading if True (default: True)
        TRADING_MODE: Trading mode (LIVE, PAPER, BACKTEST) (default: PAPER)
        MARKET_DATA_REFRESH_INTERVAL: Market data refresh interval in seconds (default: 60)
        PORTFOLIO_REFRESH_INTERVAL: Portfolio refresh interval in seconds (default: 300)
    """

    # ========================================================================
    # API Keys - Required for system operation
    # ========================================================================

    HUGGINGFACE_API_KEY: str = field(default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY", ""))
    OPENROUTER_API_KEY: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    BINANCE_API_KEY: str = field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    BINANCE_API_SECRET: str = field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    COINMARKETCAP_API_KEY: str = field(default_factory=lambda: os.getenv("COINMARKETCAP_API_KEY", ""))
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    TELEGRAM_CHAT_ID: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    GOOGLE_SHEET_URL: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEET_URL", ""))

    # ========================================================================
    # Rate Limits - Critical for avoiding API bans
    # ========================================================================

    # Binance: 100 calls per 60 seconds (generous limit for spot trading)
    BINANCE_RATE_LIMIT: int = 100
    BINANCE_RATE_WINDOW: int = 60  # seconds

    # CoinMarketCap: 1 call per 300 seconds (CRITICAL BOTTLENECK - Free tier)
    # This is the most restrictive rate limit in the system
    COINMARKETCAP_RATE_LIMIT: int = 1
    COINMARKETCAP_RATE_WINDOW: int = 300  # 5 minutes

    # Yahoo Finance: 1 call per 3 seconds (conservative estimate for free tier)
    YFINANCE_RATE_LIMIT: int = 1
    YFINANCE_RATE_WINDOW: int = 3  # seconds

    # HuggingFace: 150 calls per 60 seconds (inference API free tier)
    HUGGINGFACE_RATE_LIMIT: int = 150
    HUGGINGFACE_RATE_WINDOW: int = 60  # seconds

    # OpenRouter: 15 calls per 60 seconds (free tier for Mistral-7B)
    OPENROUTER_RATE_LIMIT: int = 15
    OPENROUTER_RATE_WINDOW: int = 60  # seconds

    # Google Sheets: 1 call per 60 seconds (conservative, API limit is 60/min)
    # We fetch config once per hour = 24 calls/day (0.03% of daily quota!)
    GOOGLE_SHEETS_RATE_LIMIT: int = 1
    GOOGLE_SHEETS_RATE_WINDOW: int = 60  # seconds

    # ========================================================================
    # Trading Parameters - Core trading logic configuration
    # ========================================================================

    # DCA_THRESHOLD: Trigger DCA buy when price drops 3% from last purchase
    DCA_THRESHOLD: float = 3.0  # percentage

    # ATR_MULTIPLIER: Stop-loss distance as multiple of Average True Range
    # Higher values = wider stops (less likely to trigger, more risk)
    ATR_MULTIPLIER: float = 1.5

    # MAX_POSITION_SIZE: Maximum 20% of portfolio in a single position
    # Prevents over-concentration in one trade
    MAX_POSITION_SIZE: float = 0.20  # 20% of portfolio

    # MAX_TOTAL_EXPOSURE: Maximum 80% of portfolio actively invested
    # Keeps 20% cash reserve for opportunities and safety
    MAX_TOTAL_EXPOSURE: float = 0.80  # 80% of portfolio

    # EMERGENCY_STOP_LOSS: Kill switch at 25% portfolio drawdown
    # Triggers emergency shutdown to prevent catastrophic losses
    EMERGENCY_STOP_LOSS: float = 0.25  # 25% drawdown

    # MAX_TRADES_PER_HOUR: Limit to 5 trades per hour
    # Prevents over-trading and excessive fee accumulation
    MAX_TRADES_PER_HOUR: int = 5

    # ========================================================================
    # System Configuration
    # ========================================================================

    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    TESTNET_MODE: bool = field(default_factory=lambda: os.getenv("TESTNET_MODE", "true").lower() == "true")
    MOCK_MODE: bool = field(default_factory=lambda: os.getenv("MOCK_MODE", "false").lower() == "true")
    TRADING_MODE: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "PAPER"))
    MARKET_DATA_REFRESH_INTERVAL: int = field(
        default_factory=lambda: int(os.getenv("MARKET_DATA_REFRESH_INTERVAL", "60"))
    )
    PORTFOLIO_REFRESH_INTERVAL: int = field(
        default_factory=lambda: int(os.getenv("PORTFOLIO_REFRESH_INTERVAL", "300"))
    )

    # ========================================================================
    # Optional Configuration
    # ========================================================================

    LANGCHAIN_TRACING_V2: bool = field(
        default_factory=lambda: os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    )
    LANGCHAIN_API_KEY: str = field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY", ""))
    LANGCHAIN_PROJECT: str = field(
        default_factory=lambda: os.getenv("LANGCHAIN_PROJECT", "bitcoin-trading-system")
    )

    # ========================================================================
    # Singleton instance
    # ========================================================================

    _instance: Optional["Settings"] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If required configuration values are missing or invalid
        """
        self._validate_api_keys()
        self._validate_trading_parameters()
        self._validate_system_configuration()

    def _validate_api_keys(self) -> None:
        """Validate that required API keys are present.

        Raises:
            ValueError: If required API keys are missing
        """
        required_keys = {
            "HUGGINGFACE_API_KEY": self.HUGGINGFACE_API_KEY,
            "BINANCE_API_KEY": self.BINANCE_API_KEY,
            "BINANCE_API_SECRET": self.BINANCE_API_SECRET,
        }

        missing_keys = [key for key, value in required_keys.items() if not value]

        if missing_keys:
            raise ValueError(
                f"Missing required API keys: {', '.join(missing_keys)}. "
                f"Please set these in your .env file. "
                f"See config/.env.example for template."
            )

        # Warn about optional but recommended keys
        optional_keys = {
            "COINMARKETCAP_API_KEY": self.COINMARKETCAP_API_KEY,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "GOOGLE_SHEET_URL": self.GOOGLE_SHEET_URL,
        }

        missing_optional = [key for key, value in optional_keys.items() if not value]

        if missing_optional:
            print(
                f"WARNING: Optional API keys not set: {', '.join(missing_optional)}. "
                f"Some features may be unavailable."
            )

    def _validate_trading_parameters(self) -> None:
        """Validate trading parameters are within safe ranges.

        Raises:
            ValueError: If trading parameters are invalid or unsafe
        """
        # Validate DCA threshold
        if not 0.1 <= self.DCA_THRESHOLD <= 20.0:
            raise ValueError(
                f"DCA_THRESHOLD must be between 0.1 and 20.0 (got {self.DCA_THRESHOLD})"
            )

        # Validate ATR multiplier
        if not 0.5 <= self.ATR_MULTIPLIER <= 5.0:
            raise ValueError(
                f"ATR_MULTIPLIER must be between 0.5 and 5.0 (got {self.ATR_MULTIPLIER})"
            )

        # Validate position sizes
        if not 0.01 <= self.MAX_POSITION_SIZE <= 1.0:
            raise ValueError(
                f"MAX_POSITION_SIZE must be between 0.01 and 1.0 (got {self.MAX_POSITION_SIZE})"
            )

        if not 0.01 <= self.MAX_TOTAL_EXPOSURE <= 1.0:
            raise ValueError(
                f"MAX_TOTAL_EXPOSURE must be between 0.01 and 1.0 (got {self.MAX_TOTAL_EXPOSURE})"
            )

        # Ensure position size doesn't exceed total exposure
        if self.MAX_POSITION_SIZE > self.MAX_TOTAL_EXPOSURE:
            raise ValueError(
                f"MAX_POSITION_SIZE ({self.MAX_POSITION_SIZE}) cannot exceed "
                f"MAX_TOTAL_EXPOSURE ({self.MAX_TOTAL_EXPOSURE})"
            )

        # Validate emergency stop loss
        if not 0.05 <= self.EMERGENCY_STOP_LOSS <= 0.50:
            raise ValueError(
                f"EMERGENCY_STOP_LOSS must be between 0.05 and 0.50 (got {self.EMERGENCY_STOP_LOSS})"
            )

        # Validate trade frequency
        if not 1 <= self.MAX_TRADES_PER_HOUR <= 100:
            raise ValueError(
                f"MAX_TRADES_PER_HOUR must be between 1 and 100 (got {self.MAX_TRADES_PER_HOUR})"
            )

    def _validate_system_configuration(self) -> None:
        """Validate system configuration parameters.

        Raises:
            ValueError: If system configuration is invalid
        """
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_log_levels} (got {self.LOG_LEVEL})"
            )

        # Validate trading mode
        valid_trading_modes = ["LIVE", "PAPER", "BACKTEST"]
        if self.TRADING_MODE.upper() not in valid_trading_modes:
            raise ValueError(
                f"TRADING_MODE must be one of {valid_trading_modes} (got {self.TRADING_MODE})"
            )

        # Validate refresh intervals
        if self.MARKET_DATA_REFRESH_INTERVAL < 1:
            raise ValueError(
                f"MARKET_DATA_REFRESH_INTERVAL must be at least 1 second "
                f"(got {self.MARKET_DATA_REFRESH_INTERVAL})"
            )

        if self.PORTFOLIO_REFRESH_INTERVAL < 10:
            raise ValueError(
                f"PORTFOLIO_REFRESH_INTERVAL must be at least 10 seconds "
                f"(got {self.PORTFOLIO_REFRESH_INTERVAL})"
            )

        # Warn if in live trading mode
        if self.TRADING_MODE.upper() == "LIVE" and not self.TESTNET_MODE:
            print(
                "\n" + "=" * 70 + "\n"
                "WARNING: LIVE TRADING MODE ENABLED\n"
                "This system will execute real trades with real money.\n"
                "Ensure you have tested thoroughly in PAPER mode first.\n"
                "=" * 70 + "\n"
            )

    @classmethod
    def get_instance(cls) -> "Settings":
        """Get the singleton Settings instance.

        Creates a new instance on first call, then returns the same instance
        on subsequent calls.

        Returns:
            Settings: The singleton Settings instance

        Example:
            >>> settings = Settings.get_instance()
            >>> settings2 = Settings.get_instance()
            >>> assert settings is settings2  # Same instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        Useful for testing when you need to reload configuration.
        Should not be used in production code.
        """
        cls._instance = None

    def __repr__(self) -> str:
        """Return string representation with sensitive data masked.

        Returns:
            str: String representation with API keys masked
        """
        return (
            f"Settings("
            f"TRADING_MODE={self.TRADING_MODE}, "
            f"TESTNET_MODE={self.TESTNET_MODE}, "
            f"MAX_POSITION_SIZE={self.MAX_POSITION_SIZE}, "
            f"EMERGENCY_STOP_LOSS={self.EMERGENCY_STOP_LOSS})"
        )


# Convenience function for quick access
def get_settings() -> Settings:
    """Convenience function to get Settings instance.

    Returns:
        Settings: The singleton Settings instance

    Example:
        >>> from config.settings import get_settings
        >>> settings = get_settings()
    """
    return Settings.get_instance()


# Module-level validation on import
if __name__ != "__main__":
    # Validate configuration on module import
    try:
        _settings = get_settings()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your .env file and ensure all required values are set.")
