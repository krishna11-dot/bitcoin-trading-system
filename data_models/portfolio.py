"""Portfolio state models for Bitcoin trading system.

This module defines Pydantic models for portfolio state tracking including
BTC and USD balances, active positions, and profit/loss calculations.

Example:
    >>> from data_models.portfolio import PortfolioState
    >>> portfolio = PortfolioState(
    ...     btc_balance=0.5,
    ...     usd_balance=10000.0,
    ...     active_positions=[],
    ...     last_updated="2025-01-15T10:30:00Z"
    ... )
    >>> total_value = portfolio.calculate_total_value(current_btc_price=45000.0)
    >>> print(f"Total Portfolio Value: ${total_value:,.2f}")
    Total Portfolio Value: $32,500.00
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class PortfolioState(BaseModel):
    """Current portfolio state with balances and positions.

    This model tracks the complete portfolio state including cryptocurrency
    and fiat balances, active trading positions, and performance metrics.

    Attributes:
        btc_balance: Current Bitcoin balance (must be non-negative)
        usd_balance: Current USD balance (must be non-negative)
        active_positions: List of active trading positions
        last_updated: ISO 8601 timestamp of last portfolio update
        profit_loss_pct: Overall profit/loss percentage (optional)

    Computed:
        total_value_usd: Total portfolio value in USD (requires current BTC price)

    Example:
        >>> portfolio = PortfolioState(
        ...     btc_balance=0.5,
        ...     usd_balance=10000.0,
        ...     active_positions=[],
        ...     last_updated="2025-01-15T10:30:00Z"
        ... )
        >>> value = portfolio.calculate_total_value(45000.0)
        >>> print(f"Total Value: ${value:,.2f}")
        Total Value: $32,500.00
    """

    # Balance fields
    btc_balance: float = Field(
        ...,
        description="Current Bitcoin balance",
        ge=0.0,
        examples=[0.5, 1.25, 0.0, 2.5],
    )

    usd_balance: float = Field(
        ...,
        description="Current USD balance",
        ge=0.0,
        examples=[10000.0, 25000.50, 0.0, 50000.0],
    )

    # Active positions (list of dictionaries with position details)
    active_positions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of active trading positions",
        examples=[
            [],
            [
                {
                    "entry_price": 45000.0,
                    "amount": 0.1,
                    "stop_loss": 43500.0,
                    "take_profit": 47000.0,
                    "entry_time": "2025-01-15T10:00:00Z",
                }
            ],
        ],
    )

    # Metadata
    last_updated: str = Field(
        ...,
        description="ISO 8601 timestamp of last portfolio update",
        examples=["2025-01-15T10:30:00Z", "2025-01-15T14:45:30Z"],
    )

    # Performance metrics
    profit_loss_pct: Optional[float] = Field(
        default=None,
        description="Overall profit/loss percentage (optional)",
        examples=[-5.2, 10.5, 0.0, 25.3],
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "btc_balance": 0.5,
                    "usd_balance": 10000.0,
                    "active_positions": [],
                    "last_updated": "2025-01-15T10:30:00Z",
                    "profit_loss_pct": 5.2,
                },
                {
                    "btc_balance": 1.25,
                    "usd_balance": 25000.50,
                    "active_positions": [
                        {
                            "entry_price": 45000.0,
                            "amount": 0.1,
                            "stop_loss": 43500.0,
                            "take_profit": 47000.0,
                            "entry_time": "2025-01-15T10:00:00Z",
                        }
                    ],
                    "last_updated": "2025-01-15T14:45:30Z",
                    "profit_loss_pct": 10.5,
                },
            ]
        },
    )

    @field_validator("btc_balance")
    @classmethod
    def validate_btc_balance(cls, v: float) -> float:
        """Validate BTC balance is non-negative and reasonable.

        Args:
            v: BTC balance to validate

        Returns:
            float: Validated BTC balance

        Raises:
            ValueError: If BTC balance is invalid
        """
        if v < 0:
            raise ValueError(f"BTC balance cannot be negative (got {v:.8f})")

        # Warn if balance exceeds 100 BTC (unusual for retail trader)
        if v > 100.0:
            print(
                f"WARNING: BTC balance {v:.4f} exceeds 100 BTC. "
                f"Ensure this is intentional."
            )

        return v

    @field_validator("usd_balance")
    @classmethod
    def validate_usd_balance(cls, v: float) -> float:
        """Validate USD balance is non-negative and reasonable.

        Args:
            v: USD balance to validate

        Returns:
            float: Validated USD balance

        Raises:
            ValueError: If USD balance is invalid
        """
        if v < 0:
            raise ValueError(f"USD balance cannot be negative (got ${v:,.2f})")

        # Warn if balance exceeds $10M (unusual for retail trader)
        if v > 10_000_000:
            print(
                f"WARNING: USD balance ${v:,.2f} exceeds $10M. "
                f"Ensure this is intentional."
            )

        return v

    @field_validator("profit_loss_pct")
    @classmethod
    def validate_profit_loss(cls, v: Optional[float]) -> Optional[float]:
        """Validate profit/loss percentage is reasonable.

        Args:
            v: Profit/loss percentage to validate

        Returns:
            Optional[float]: Validated profit/loss or None

        Raises:
            ValueError: If profit/loss is outside reasonable bounds
        """
        if v is not None:
            # Warn if P/L exceeds ±200% (extremely unusual)
            if abs(v) > 200.0:
                print(
                    f"WARNING: Profit/loss {v:+.1f}% exceeds ±200%. "
                    f"This is highly unusual. Verify calculation."
                )

        return v

    def calculate_total_value(self, current_btc_price: float) -> float:
        """Calculate total portfolio value in USD.

        Args:
            current_btc_price: Current Bitcoin price in USD

        Returns:
            float: Total portfolio value in USD

        Raises:
            ValueError: If current_btc_price is invalid

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
            >>> portfolio.calculate_total_value(45000.0)
            32500.0
        """
        if current_btc_price <= 0:
            raise ValueError(
                f"Current BTC price must be positive (got ${current_btc_price:,.2f})"
            )

        btc_value_usd = self.btc_balance * current_btc_price
        return btc_value_usd + self.usd_balance

    def get_btc_allocation_pct(self, current_btc_price: float) -> float:
        """Calculate percentage of portfolio allocated to BTC.

        Args:
            current_btc_price: Current Bitcoin price in USD

        Returns:
            float: BTC allocation as percentage (0-100)

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
            >>> allocation = portfolio.get_btc_allocation_pct(45000.0)
            >>> print(f"BTC allocation: {allocation:.1f}%")
            BTC allocation: 69.2%
        """
        total_value = self.calculate_total_value(current_btc_price)

        if total_value == 0:
            return 0.0

        btc_value = self.btc_balance * current_btc_price
        return (btc_value / total_value) * 100

    def get_usd_allocation_pct(self, current_btc_price: float) -> float:
        """Calculate percentage of portfolio allocated to USD.

        Args:
            current_btc_price: Current Bitcoin price in USD

        Returns:
            float: USD allocation as percentage (0-100)

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
            >>> allocation = portfolio.get_usd_allocation_pct(45000.0)
            >>> print(f"USD allocation: {allocation:.1f}%")
            USD allocation: 30.8%
        """
        return 100.0 - self.get_btc_allocation_pct(current_btc_price)

    def can_buy(self, amount_usd: float) -> bool:
        """Check if portfolio has sufficient USD balance to buy.

        Args:
            amount_usd: Amount in USD to check

        Returns:
            bool: True if sufficient USD balance available

        Example:
            >>> portfolio = PortfolioState(usd_balance=10000.0, ...)
            >>> portfolio.can_buy(5000.0)
            True
            >>> portfolio.can_buy(15000.0)
            False
        """
        return self.usd_balance >= amount_usd

    def can_sell(self, amount_btc: float) -> bool:
        """Check if portfolio has sufficient BTC balance to sell.

        Args:
            amount_btc: Amount in BTC to check

        Returns:
            bool: True if sufficient BTC balance available

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.5, ...)
            >>> portfolio.can_sell(0.3)
            True
            >>> portfolio.can_sell(0.8)
            False
        """
        return self.btc_balance >= amount_btc

    def get_active_positions_count(self) -> int:
        """Get number of active trading positions.

        Returns:
            int: Number of active positions

        Example:
            >>> portfolio = PortfolioState(active_positions=[{...}, {...}], ...)
            >>> portfolio.get_active_positions_count()
            2
        """
        return len(self.active_positions)

    def has_active_positions(self) -> bool:
        """Check if portfolio has any active positions.

        Returns:
            bool: True if there are active positions

        Example:
            >>> portfolio = PortfolioState(active_positions=[], ...)
            >>> portfolio.has_active_positions()
            False
        """
        return len(self.active_positions) > 0

    def get_total_position_value(self) -> float:
        """Calculate total value of all active positions.

        Returns:
            float: Total position value in USD

        Example:
            >>> portfolio = PortfolioState(
            ...     active_positions=[
            ...         {"entry_price": 45000.0, "amount": 0.1},
            ...         {"entry_price": 46000.0, "amount": 0.05}
            ...     ],
            ...     ...
            ... )
            >>> portfolio.get_total_position_value()
            6800.0
        """
        total = 0.0
        for position in self.active_positions:
            if "entry_price" in position and "amount" in position:
                total += position["entry_price"] * position["amount"]
        return total

    def get_exposure_pct(self, current_btc_price: float) -> float:
        """Calculate current market exposure as percentage of portfolio.

        Args:
            current_btc_price: Current Bitcoin price in USD

        Returns:
            float: Exposure as percentage (0-100)

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
            >>> exposure = portfolio.get_exposure_pct(45000.0)
            >>> print(f"Market exposure: {exposure:.1f}%")
            Market exposure: 69.2%
        """
        return self.get_btc_allocation_pct(current_btc_price)

    def is_below_max_exposure(
        self, current_btc_price: float, max_exposure: float = 0.80
    ) -> bool:
        """Check if portfolio is below maximum exposure limit.

        Args:
            current_btc_price: Current Bitcoin price in USD
            max_exposure: Maximum exposure limit (default: 0.80 = 80%)

        Returns:
            bool: True if below max exposure limit

        Example:
            >>> portfolio = PortfolioState(btc_balance=0.3, usd_balance=20000.0, ...)
            >>> portfolio.is_below_max_exposure(45000.0, max_exposure=0.80)
            True
        """
        current_exposure = self.get_exposure_pct(current_btc_price) / 100.0
        return current_exposure < max_exposure

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            str: Formatted portfolio string
        """
        return (
            f"PortfolioState("
            f"BTC={self.btc_balance:.4f}, "
            f"USD=${self.usd_balance:,.2f}, "
            f"positions={len(self.active_positions)}, "
            f"P/L={self.profit_loss_pct:+.1f}%)" if self.profit_loss_pct is not None
            else f"PortfolioState("
            f"BTC={self.btc_balance:.4f}, "
            f"USD=${self.usd_balance:,.2f}, "
            f"positions={len(self.active_positions)})"
        )
