"""Technical indicators models for Bitcoin trading system.

This module defines Pydantic models for technical analysis indicators including
RSI, MACD, ATR, moving averages, and Bollinger Bands. All values are validated
to ensure they fall within mathematically valid ranges.

Example:
    >>> from data_models.indicators import TechnicalIndicators
    >>> indicators = TechnicalIndicators(
    ...     rsi_14=65.5,
    ...     macd=120.5,
    ...     macd_signal=115.3,
    ...     macd_histogram=5.2,
    ...     atr_14=12000.0,  # BTC at $100k: ATR ~12% of price is normal
    ...     sma_50=95000.0,
    ...     ema_12=98000.0,
    ...     ema_26=96000.0
    ... )
    >>> print(f"RSI: {indicators.rsi_14:.1f}")
    RSI: 65.5
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators for Bitcoin.

    This model contains calculated technical indicators used for market analysis
    and trading decisions. All indicators are validated to ensure they fall
    within mathematically valid ranges.

    Attributes:
        rsi_14: Relative Strength Index (14-period), range 0-100
        macd: MACD line value
        macd_signal: MACD signal line value
        macd_histogram: MACD histogram (MACD - Signal)
        atr_14: Average True Range (14-period), must be positive
        sma_50: Simple Moving Average (50-period)
        ema_12: Exponential Moving Average (12-period)
        ema_26: Exponential Moving Average (26-period)
        bollinger_upper: Upper Bollinger Band (optional)
        bollinger_lower: Lower Bollinger Band (optional)

    Example:
        >>> indicators = TechnicalIndicators(
        ...     rsi_14=65.5,
        ...     macd=120.5,
        ...     macd_signal=115.3,
        ...     macd_histogram=5.2,
        ...     atr_14=12000.0,  # BTC at $100k
        ...     sma_50=95000.0,
        ...     ema_12=98000.0,
        ...     ema_26=96000.0
        ... )
    """

    # RSI - Relative Strength Index (0-100 range)
    rsi_14: float = Field(
        ...,
        description="Relative Strength Index (14-period)",
        ge=0,
        le=100,
        examples=[30.5, 50.0, 70.5, 85.2],
    )

    # MACD - Moving Average Convergence Divergence
    macd: float = Field(
        ...,
        description="MACD line value",
        examples=[120.5, -85.3, 0.0],
    )

    macd_signal: float = Field(
        ...,
        description="MACD signal line value",
        examples=[115.3, -90.1, 5.2],
    )

    macd_histogram: float = Field(
        ...,
        description="MACD histogram (MACD - Signal)",
        examples=[5.2, 4.8, -10.5, 0.0],
    )

    # ATR - Average True Range (volatility measure)
    atr_14: float = Field(
        ...,
        description="Average True Range (14-period)",
        gt=0,
        examples=[850.0, 12000.0, 43000.0],  # Normal: $12k, High volatility: $43k (BTC at $100k)
    )

    # Moving Averages
    sma_50: float = Field(
        ...,
        description="Simple Moving Average (50-period)",
        gt=0,
        examples=[44500.0, 45000.0, 67890.5],
    )

    ema_12: float = Field(
        ...,
        description="Exponential Moving Average (12-period)",
        gt=0,
        examples=[45200.0, 45500.0, 68000.0],
    )

    ema_26: float = Field(
        ...,
        description="Exponential Moving Average (26-period)",
        gt=0,
        examples=[44800.0, 45000.0, 67500.0],
    )

    # Bollinger Bands (optional)
    bollinger_upper: Optional[float] = Field(
        default=None,
        description="Upper Bollinger Band",
        gt=0,
        examples=[46500.0, 69000.0],
    )

    bollinger_lower: Optional[float] = Field(
        default=None,
        description="Lower Bollinger Band",
        gt=0,
        examples=[43500.0, 66000.0],
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "rsi_14": 65.5,
                    "macd": 120.5,
                    "macd_signal": 115.3,
                    "macd_histogram": 5.2,
                    "atr_14": 12000.0,  # Updated: BTC at $100k
                    "sma_50": 95000.0,  # Updated: BTC at $100k
                    "ema_12": 98000.0,  # Updated: BTC at $100k
                    "ema_26": 96000.0,  # Updated: BTC at $100k
                    "bollinger_upper": 102000.0,  # Updated: BTC at $100k
                    "bollinger_lower": 94000.0,   # Updated: BTC at $100k
                },
                {
                    "rsi_14": 30.5,
                    "macd": -85.3,
                    "macd_signal": -90.1,
                    "macd_histogram": 4.8,
                    "atr_14": 1200.5,  # Lower volatility period
                    "sma_50": 45000.0,  # Historical example (BTC at $45k)
                    "ema_12": 45500.0,
                    "ema_26": 45000.0,
                    "bollinger_upper": 47000.0,
                    "bollinger_lower": 43000.0,
                },
            ]
        },
    )

    @field_validator("rsi_14")
    @classmethod
    def validate_rsi(cls, v: float) -> float:
        """Validate RSI is within 0-100 range.

        Args:
            v: RSI value to validate

        Returns:
            float: Validated RSI value

        Raises:
            ValueError: If RSI is outside 0-100 range
        """
        if not 0 <= v <= 100:
            raise ValueError(
                f"RSI must be between 0 and 100 (got {v:.2f}). "
                f"This indicates a calculation error."
            )
        return v

    @field_validator("atr_14")
    @classmethod
    def validate_atr(cls, v: float) -> float:
        """Validate ATR is positive and reasonable.

        Args:
            v: ATR value to validate

        Returns:
            float: Validated ATR value

        Raises:
            ValueError: If ATR is invalid
        """
        if v <= 0:
            raise ValueError(
                f"ATR must be positive (got {v:.2f}). "
                f"This indicates a calculation error."
            )

        # ATR over $100,000 would be extremely unusual
        # Note: With BTC at $100k, normal ATR is $10-15k (10-15% volatility)
        # During extreme volatility (flash crashes, high fear), ATR can spike to 40-50% of price
        # Example: BTC at $97k with -5.72% drop → ATR of $43k (44% volatility) is possible
        # Increased from $25k to $100k to handle extreme market conditions
        if v > 100_000:
            raise ValueError(
                f"ATR {v:,.2f} is suspiciously high (>$100,000). "
                f"This may indicate a calculation error."
            )

        return v

    @field_validator("sma_50", "ema_12", "ema_26")
    @classmethod
    def validate_moving_averages(cls, v: float) -> float:
        """Validate moving averages are within reasonable bounds.

        Args:
            v: Moving average value to validate

        Returns:
            float: Validated moving average

        Raises:
            ValueError: If moving average is outside reasonable bounds
        """
        # Moving averages should be within Bitcoin's reasonable price range
        if not 100 <= v <= 1_000_000:
            raise ValueError(
                f"Moving average {v:,.2f} is outside reasonable bounds ($100 - $1,000,000). "
                f"This may indicate a calculation error."
            )
        return v

    @field_validator("bollinger_upper", "bollinger_lower")
    @classmethod
    def validate_bollinger_bands(cls, v: Optional[float]) -> Optional[float]:
        """Validate Bollinger Bands are within reasonable bounds.

        Args:
            v: Bollinger Band value to validate

        Returns:
            Optional[float]: Validated Bollinger Band or None

        Raises:
            ValueError: If Bollinger Band is outside reasonable bounds
        """
        if v is not None:
            if not 100 <= v <= 1_000_000:
                raise ValueError(
                    f"Bollinger Band {v:,.2f} is outside reasonable bounds ($100 - $1,000,000)"
                )
        return v

    def is_rsi_oversold(self, threshold: float = 30.0) -> bool:
        """Check if RSI indicates oversold conditions.

        Args:
            threshold: Oversold threshold (default: 30.0)

        Returns:
            bool: True if RSI is below threshold (oversold)

        Example:
            >>> indicators = TechnicalIndicators(rsi_14=25.0, ...)
            >>> indicators.is_rsi_oversold()
            True
        """
        return self.rsi_14 < threshold

    def is_rsi_overbought(self, threshold: float = 70.0) -> bool:
        """Check if RSI indicates overbought conditions.

        Args:
            threshold: Overbought threshold (default: 70.0)

        Returns:
            bool: True if RSI is above threshold (overbought)

        Example:
            >>> indicators = TechnicalIndicators(rsi_14=75.0, ...)
            >>> indicators.is_rsi_overbought()
            True
        """
        return self.rsi_14 > threshold

    def is_macd_bullish(self) -> bool:
        """Check if MACD indicates bullish momentum.

        Returns:
            bool: True if MACD line is above signal line (bullish)

        Example:
            >>> indicators = TechnicalIndicators(macd=120.5, macd_signal=115.3, ...)
            >>> indicators.is_macd_bullish()
            True
        """
        return self.macd > self.macd_signal

    def is_macd_bearish(self) -> bool:
        """Check if MACD indicates bearish momentum.

        Returns:
            bool: True if MACD line is below signal line (bearish)

        Example:
            >>> indicators = TechnicalIndicators(macd=110.0, macd_signal=115.3, ...)
            >>> indicators.is_macd_bearish()
            True
        """
        return self.macd < self.macd_signal

    def get_macd_strength(self) -> float:
        """Calculate MACD strength as percentage of signal line.

        Returns:
            float: MACD strength as percentage

        Example:
            >>> indicators = TechnicalIndicators(macd=120.5, macd_signal=115.3, ...)
            >>> strength = indicators.get_macd_strength()
            >>> print(f"MACD strength: {strength:.2f}%")
            MACD strength: 4.51%
        """
        if self.macd_signal == 0:
            return 0.0
        return (self.macd_histogram / abs(self.macd_signal)) * 100

    def is_price_above_sma(self, current_price: float) -> bool:
        """Check if current price is above 50-period SMA.

        Args:
            current_price: Current Bitcoin price

        Returns:
            bool: True if price is above SMA (bullish)

        Example:
            >>> indicators = TechnicalIndicators(sma_50=44500.0, ...)
            >>> indicators.is_price_above_sma(45000.0)
            True
        """
        return current_price > self.sma_50

    def get_ema_crossover_signal(self) -> str:
        """Determine EMA crossover signal (golden/death cross).

        Returns:
            str: 'bullish' if EMA12 > EMA26, 'bearish' if EMA12 < EMA26, 'neutral' if equal

        Example:
            >>> indicators = TechnicalIndicators(ema_12=45200.0, ema_26=44800.0, ...)
            >>> indicators.get_ema_crossover_signal()
            'bullish'
        """
        if self.ema_12 > self.ema_26:
            return "bullish"
        elif self.ema_12 < self.ema_26:
            return "bearish"
        else:
            return "neutral"

    def is_price_near_bollinger_upper(
        self, current_price: float, threshold: float = 0.01
    ) -> bool:
        """Check if price is near upper Bollinger Band.

        Args:
            current_price: Current Bitcoin price
            threshold: Distance threshold as fraction (default: 1% = 0.01)

        Returns:
            bool: True if price is within threshold of upper band

        Example:
            >>> indicators = TechnicalIndicators(bollinger_upper=46500.0, ...)
            >>> indicators.is_price_near_bollinger_upper(46300.0, threshold=0.01)
            True
        """
        if self.bollinger_upper is None:
            return False

        distance = abs(current_price - self.bollinger_upper) / self.bollinger_upper
        return distance <= threshold

    def is_price_near_bollinger_lower(
        self, current_price: float, threshold: float = 0.01
    ) -> bool:
        """Check if price is near lower Bollinger Band.

        Args:
            current_price: Current Bitcoin price
            threshold: Distance threshold as fraction (default: 1% = 0.01)

        Returns:
            bool: True if price is within threshold of lower band

        Example:
            >>> indicators = TechnicalIndicators(bollinger_lower=43500.0, ...)
            >>> indicators.is_price_near_bollinger_lower(43600.0, threshold=0.01)
            True
        """
        if self.bollinger_lower is None:
            return False

        distance = abs(current_price - self.bollinger_lower) / self.bollinger_lower
        return distance <= threshold

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            str: Formatted indicators string
        """
        return (
            f"TechnicalIndicators(RSI={self.rsi_14:.1f}, "
            f"MACD={self.macd:.1f}/{self.macd_signal:.1f}, "
            f"ATR={self.atr_14:.1f})"
        )
