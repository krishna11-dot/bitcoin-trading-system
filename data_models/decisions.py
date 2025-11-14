"""Trading decision models for Bitcoin trading system.

This module defines Pydantic models for trading decisions including buy, sell,
and hold actions. All decisions are validated to ensure they contain required
information and fall within safe trading parameters.

Example:
    >>> from data_models.decisions import TradeDecision
    >>> decision = TradeDecision(
    ...     action="buy",
    ...     amount=0.05,
    ...     entry_price=45000.0,
    ...     stop_loss=43500.0,
    ...     take_profit=47000.0,
    ...     confidence=0.75,
    ...     reasoning="RSI oversold at 28, MACD bullish crossover, price near support",
    ...     timestamp="2025-01-15T10:30:00Z",
    ...     strategy="swing"
    ... )
    >>> print(f"Action: {decision.action.upper()} {decision.amount} BTC")
    Action: BUY 0.05 BTC
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradeDecision(BaseModel):
    """Trading decision with full context and risk management.

    This model represents a complete trading decision including action, position
    sizing, entry/exit prices, and the reasoning behind the decision. All numeric
    values are validated to ensure safe trading parameters.

    Attributes:
        action: Trading action (buy, sell, hold)
        amount: Amount of BTC to trade (must be positive for buy/sell)
        entry_price: Expected entry price in USD (must be positive)
        stop_loss: Stop-loss price in USD (optional, must be positive if set)
        take_profit: Take-profit price in USD (optional)
        confidence: Decision confidence score (0.0 to 1.0)
        reasoning: Detailed explanation of decision (minimum 10 characters)
        timestamp: ISO 8601 timestamp of the decision
        strategy: Trading strategy used (dca, swing, day, hold)

    Example:
        >>> decision = TradeDecision(
        ...     action="buy",
        ...     amount=0.05,
        ...     entry_price=45000.0,
        ...     stop_loss=43500.0,
        ...     confidence=0.75,
        ...     reasoning="RSI oversold, bullish MACD crossover",
        ...     timestamp="2025-01-15T10:30:00Z",
        ...     strategy="swing"
        ... )
    """

    # Core decision fields
    action: Literal["buy", "sell", "hold"] = Field(
        ...,
        description="Trading action to execute",
        examples=["buy", "sell", "hold"],
    )

    amount: float = Field(
        ...,
        description="Amount of BTC to trade",
        gt=0,
        examples=[0.01, 0.05, 0.1, 1.0],
    )

    entry_price: float = Field(
        ...,
        description="Expected entry price in USD",
        gt=0,
        examples=[45000.0, 67890.5, 50000.0],
    )

    # Risk management
    stop_loss: Optional[float] = Field(
        default=None,
        description="Stop-loss price in USD (optional)",
        gt=0,
        examples=[43500.0, 66000.0, 48000.0],
    )

    take_profit: Optional[float] = Field(
        default=None,
        description="Take-profit price in USD (optional)",
        examples=[47000.0, 70000.0, 52000.0],
    )

    # Decision quality metrics
    confidence: float = Field(
        ...,
        description="Decision confidence score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
        examples=[0.5, 0.75, 0.85, 0.95],
    )

    reasoning: str = Field(
        ...,
        description="Detailed explanation of the decision",
        min_length=10,
        examples=[
            "RSI oversold at 28, MACD bullish crossover, price near support level",
            "Price broke below 50-day SMA with high volume, bearish momentum increasing",
            "Consolidating in tight range, waiting for clear directional breakout",
        ],
    )

    # Metadata
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of the decision",
        examples=["2025-01-15T10:30:00Z", "2025-01-15T14:45:30Z"],
    )

    strategy: Literal["dca", "swing", "day", "hold"] = Field(
        ...,
        description="Trading strategy employed",
        examples=["dca", "swing", "day", "hold"],
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "action": "buy",
                    "amount": 0.05,
                    "entry_price": 45000.0,
                    "stop_loss": 43500.0,
                    "take_profit": 47000.0,
                    "confidence": 0.75,
                    "reasoning": "RSI oversold at 28, MACD bullish crossover, price near support level",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "strategy": "swing",
                },
                {
                    "action": "sell",
                    "amount": 0.03,
                    "entry_price": 46500.0,
                    "stop_loss": 47500.0,
                    "take_profit": 44500.0,
                    "confidence": 0.65,
                    "reasoning": "Price broke below 50-day SMA with high volume, bearish momentum increasing",
                    "timestamp": "2025-01-15T12:00:00Z",
                    "strategy": "swing",
                },
                {
                    "action": "hold",
                    "amount": 0.0,
                    "entry_price": 45500.0,
                    "confidence": 0.50,
                    "reasoning": "Consolidating in tight range, waiting for clear directional breakout",
                    "timestamp": "2025-01-15T14:30:00Z",
                    "strategy": "hold",
                },
            ]
        },
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate trade amount is within reasonable bounds.

        Args:
            v: Amount value to validate

        Returns:
            float: Validated amount

        Raises:
            ValueError: If amount is outside reasonable bounds
        """
        # Amount should not exceed 10 BTC per trade (sanity check)
        if v > 10.0:
            raise ValueError(
                f"Trade amount {v:.4f} BTC exceeds reasonable limit (10 BTC). "
                f"This may indicate a calculation error."
            )

        # Amount should be at least 0.0001 BTC (typical exchange minimum)
        if v < 0.0001:
            raise ValueError(
                f"Trade amount {v:.8f} BTC is below typical exchange minimum (0.0001 BTC)."
            )

        return v

    @field_validator("entry_price")
    @classmethod
    def validate_entry_price(cls, v: float) -> float:
        """Validate entry price is within reasonable bounds.

        Args:
            v: Entry price to validate

        Returns:
            float: Validated entry price

        Raises:
            ValueError: If entry price is outside reasonable bounds
        """
        if not 100 <= v <= 1_000_000:
            raise ValueError(
                f"Entry price ${v:,.2f} is outside reasonable bounds ($100 - $1,000,000). "
                f"This may indicate a data error."
            )
        return v

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v: Optional[float]) -> Optional[float]:
        """Validate stop-loss price is positive and reasonable.

        Args:
            v: Stop-loss price to validate

        Returns:
            Optional[float]: Validated stop-loss or None

        Raises:
            ValueError: If stop-loss is invalid
        """
        if v is not None:
            if v <= 0:
                raise ValueError(f"Stop-loss must be positive (got ${v:,.2f})")

            if not 100 <= v <= 1_000_000:
                raise ValueError(
                    f"Stop-loss ${v:,.2f} is outside reasonable bounds ($100 - $1,000,000)"
                )

        return v

    @field_validator("take_profit")
    @classmethod
    def validate_take_profit(cls, v: Optional[float]) -> Optional[float]:
        """Validate take-profit price is reasonable.

        Args:
            v: Take-profit price to validate

        Returns:
            Optional[float]: Validated take-profit or None

        Raises:
            ValueError: If take-profit is invalid
        """
        if v is not None:
            if not 100 <= v <= 1_000_000:
                raise ValueError(
                    f"Take-profit ${v:,.2f} is outside reasonable bounds ($100 - $1,000,000)"
                )

        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0.0 and 1.0.

        Args:
            v: Confidence score to validate

        Returns:
            float: Validated confidence score

        Raises:
            ValueError: If confidence is outside 0.0-1.0 range
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0 (got {v:.2f}). "
                f"This indicates a calculation error."
            )
        return v

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """Validate reasoning has minimum length and content.

        Args:
            v: Reasoning text to validate

        Returns:
            str: Validated reasoning

        Raises:
            ValueError: If reasoning is too short or empty
        """
        if len(v.strip()) < 10:
            raise ValueError(
                f"Reasoning must be at least 10 characters (got {len(v.strip())}). "
                f"Provide detailed explanation for trading decisions."
            )
        return v.strip()

    def validate_risk_management(self) -> None:
        """Validate that stop-loss and take-profit make sense for the action.

        Raises:
            ValueError: If risk management parameters are inconsistent
        """
        if self.action == "buy":
            # For buys, stop-loss should be below entry, take-profit above
            if self.stop_loss is not None and self.stop_loss >= self.entry_price:
                raise ValueError(
                    f"Buy order: stop-loss (${self.stop_loss:,.2f}) must be below "
                    f"entry price (${self.entry_price:,.2f})"
                )

            if self.take_profit is not None and self.take_profit <= self.entry_price:
                raise ValueError(
                    f"Buy order: take-profit (${self.take_profit:,.2f}) must be above "
                    f"entry price (${self.entry_price:,.2f})"
                )

        elif self.action == "sell":
            # For sells, stop-loss should be above entry, take-profit below
            if self.stop_loss is not None and self.stop_loss <= self.entry_price:
                raise ValueError(
                    f"Sell order: stop-loss (${self.stop_loss:,.2f}) must be above "
                    f"entry price (${self.entry_price:,.2f})"
                )

            if self.take_profit is not None and self.take_profit >= self.entry_price:
                raise ValueError(
                    f"Sell order: take-profit (${self.take_profit:,.2f}) must be below "
                    f"entry price (${self.entry_price:,.2f})"
                )

    def get_risk_reward_ratio(self) -> Optional[float]:
        """Calculate risk-reward ratio for the trade.

        Returns:
            Optional[float]: Risk-reward ratio, or None if stop/take profit not set

        Example:
            >>> decision = TradeDecision(
            ...     action="buy",
            ...     entry_price=45000,
            ...     stop_loss=43500,
            ...     take_profit=48000,
            ...     ...
            ... )
            >>> decision.get_risk_reward_ratio()
            2.0  # Risk $1500 to make $3000 = 2:1 ratio
        """
        if self.stop_loss is None or self.take_profit is None:
            return None

        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)

        if risk == 0:
            return None

        return reward / risk

    def get_position_value_usd(self) -> float:
        """Calculate total position value in USD.

        Returns:
            float: Position value in USD

        Example:
            >>> decision = TradeDecision(amount=0.05, entry_price=45000, ...)
            >>> decision.get_position_value_usd()
            2250.0
        """
        return self.amount * self.entry_price

    def is_high_confidence(self, threshold: float = 0.70) -> bool:
        """Check if decision has high confidence.

        Args:
            threshold: Confidence threshold (default: 0.70 = 70%)

        Returns:
            bool: True if confidence exceeds threshold

        Example:
            >>> decision = TradeDecision(confidence=0.75, ...)
            >>> decision.is_high_confidence()
            True
        """
        return self.confidence >= threshold

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            str: Formatted decision string
        """
        if self.action == "hold":
            return (
                f"TradeDecision(action=HOLD, "
                f"confidence={self.confidence:.0%}, "
                f"strategy={self.strategy})"
            )

        return (
            f"TradeDecision(action={self.action.upper()}, "
            f"amount={self.amount:.4f} BTC, "
            f"entry=${self.entry_price:,.2f}, "
            f"confidence={self.confidence:.0%}, "
            f"strategy={self.strategy})"
        )
