"""Market data models for Bitcoin trading system.

This module defines Pydantic models for market data including price, volume,
and 24-hour statistics. All data is validated to ensure consistency and
prevent invalid market data from propagating through the system.

Example:
    >>> from data_models.market_data import MarketData
    >>> data = MarketData(
    ...     price=45000.50,
    ...     volume=1234567.89,
    ...     timestamp="2025-01-15T10:30:00Z",
    ...     change_24h=-2.5,
    ...     high_24h=46000.0,
    ...     low_24h=44500.0
    ... )
    >>> print(f"BTC Price: ${data.price:,.2f}")
    BTC Price: $45,000.50
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketData(BaseModel):
    """Real-time market data for Bitcoin.

    This model represents current market conditions including price, volume,
    and 24-hour change statistics. All numeric values are validated to ensure
    they fall within expected ranges.

    Attributes:
        price: Current Bitcoin price in USD (must be positive)
        volume: 24-hour trading volume in USD (must be non-negative)
        timestamp: ISO 8601 timestamp of the data point
        change_24h: 24-hour price change percentage (can be negative)
        high_24h: 24-hour high price in USD (optional)
        low_24h: 24-hour low price in USD (optional)

    Example:
        >>> data = MarketData(
        ...     price=45000.50,
        ...     volume=1234567.89,
        ...     timestamp="2025-01-15T10:30:00Z",
        ...     change_24h=-2.5
        ... )
    """

    # Core market data fields
    price: float = Field(
        ...,
        description="Current Bitcoin price in USD",
        gt=0,
        examples=[45000.50, 67890.12],
    )

    volume: float = Field(
        ...,
        description="24-hour trading volume in USD",
        ge=0,
        examples=[1234567.89, 9876543.21],
    )

    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of the data point",
        examples=["2025-01-15T10:30:00Z", "2025-01-15T14:45:30Z"],
    )

    change_24h: float = Field(
        ...,
        description="24-hour price change percentage (can be negative)",
        examples=[-2.5, 5.3, 0.0],
    )

    # Optional 24-hour statistics
    high_24h: Optional[float] = Field(
        default=None,
        description="24-hour high price in USD",
        gt=0,
        examples=[46000.0, 68500.0],
    )

    low_24h: Optional[float] = Field(
        default=None,
        description="24-hour low price in USD",
        gt=0,
        examples=[44500.0, 66000.0],
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "price": 45000.50,
                    "volume": 1234567.89,
                    "timestamp": "2025-01-15T10:30:00Z",
                    "change_24h": -2.5,
                    "high_24h": 46000.0,
                    "low_24h": 44500.0,
                },
                {
                    "price": 67890.12,
                    "volume": 9876543.21,
                    "timestamp": "2025-01-15T14:45:30Z",
                    "change_24h": 5.3,
                    "high_24h": 68500.0,
                    "low_24h": 66000.0,
                },
            ]
        },
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is within reasonable bounds.

        Args:
            v: Price value to validate

        Returns:
            float: Validated price

        Raises:
            ValueError: If price is outside reasonable bounds
        """
        # Bitcoin price should be between $100 and $1,000,000
        # These are sanity checks to catch obvious data errors
        if not 100 <= v <= 1_000_000:
            raise ValueError(
                f"Price {v:,.2f} USD is outside reasonable bounds ($100 - $1,000,000). "
                f"This may indicate a data error."
            )
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: float) -> float:
        """Validate that volume is reasonable.

        Args:
            v: Volume value to validate

        Returns:
            float: Validated volume

        Raises:
            ValueError: If volume is suspiciously high
        """
        # Daily volume over $100B would be extremely unusual and likely a data error
        if v > 100_000_000_000:
            raise ValueError(
                f"Volume {v:,.2f} USD is suspiciously high (>$100B). "
                f"This may indicate a data error."
            )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamp is in ISO 8601 format.

        Args:
            v: Timestamp string to validate

        Returns:
            str: Validated timestamp

        Raises:
            ValueError: If timestamp is not valid ISO 8601
        """
        try:
            # Attempt to parse as ISO 8601
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(
                f"Timestamp '{v}' is not valid ISO 8601 format. "
                f"Expected format: 'YYYY-MM-DDTHH:MM:SSZ'. Error: {e}"
            )
        return v

    @field_validator("high_24h", "low_24h")
    @classmethod
    def validate_24h_prices(cls, v: Optional[float]) -> Optional[float]:
        """Validate 24-hour high/low prices are within bounds.

        Args:
            v: Price value to validate

        Returns:
            Optional[float]: Validated price or None

        Raises:
            ValueError: If price is outside reasonable bounds
        """
        if v is not None:
            if not 100 <= v <= 1_000_000:
                raise ValueError(
                    f"24h price {v:,.2f} USD is outside reasonable bounds ($100 - $1,000,000)"
                )
        return v

    def is_price_near_high(self, threshold: float = 0.02) -> bool:
        """Check if current price is near 24h high.

        Args:
            threshold: Percentage threshold (default: 2% = 0.02)

        Returns:
            bool: True if price is within threshold of 24h high

        Example:
            >>> data = MarketData(price=45900, high_24h=46000, ...)
            >>> data.is_price_near_high(threshold=0.02)  # Within 2%
            True
        """
        if self.high_24h is None:
            return False

        price_diff = (self.high_24h - self.price) / self.high_24h
        return price_diff <= threshold

    def is_price_near_low(self, threshold: float = 0.02) -> bool:
        """Check if current price is near 24h low.

        Args:
            threshold: Percentage threshold (default: 2% = 0.02)

        Returns:
            bool: True if price is within threshold of 24h low

        Example:
            >>> data = MarketData(price=44600, low_24h=44500, ...)
            >>> data.is_price_near_low(threshold=0.02)  # Within 2%
            True
        """
        if self.low_24h is None:
            return False

        price_diff = (self.price - self.low_24h) / self.low_24h
        return price_diff <= threshold

    def get_price_position_in_range(self) -> Optional[float]:
        """Calculate where current price sits in 24h range (0.0 to 1.0).

        Returns:
            Optional[float]: Position in range (0.0 = at low, 1.0 = at high)
                           None if high_24h or low_24h is missing

        Example:
            >>> data = MarketData(price=45250, high_24h=46000, low_24h=44500, ...)
            >>> position = data.get_price_position_in_range()
            >>> print(f"Price is {position:.1%} up in 24h range")
            Price is 50.0% up in 24h range
        """
        if self.high_24h is None or self.low_24h is None:
            return None

        if self.high_24h == self.low_24h:
            return 0.5  # If no range, return middle

        return (self.price - self.low_24h) / (self.high_24h - self.low_24h)

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            str: Formatted market data string
        """
        return (
            f"MarketData(price=${self.price:,.2f}, "
            f"volume=${self.volume:,.0f}, "
            f"change_24h={self.change_24h:+.2f}%)"
        )
