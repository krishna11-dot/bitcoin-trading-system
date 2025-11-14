"""Position data model for tracking Bitcoin trading positions.

This module defines the Position model used by the PositionManager to track
individual trading positions across different strategies (DCA, Swing, Day).

Example:
    >>> from data_models.positions import Position
    >>> pos = Position(
    ...     position_id="DCA-20250512-143022",
    ...     strategy="dca",
    ...     amount_btc=0.008,
    ...     amount_usd=500.0,
    ...     entry_price=62000.0,
    ...     stop_loss=60300.0,
    ...     status="open"
    ... )
"""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Position(BaseModel):
    """
    Trading position model for Bitcoin positions.

    Tracks all details of an open, closed, or stopped position including
    entry/exit prices, P&L calculations, stop-loss levels, and metadata.

    Attributes:
        position_id: Unique identifier (format: "{STRATEGY}-{TIMESTAMP}")
        strategy: Trading strategy ("dca", "swing", or "day")
        amount_btc: Bitcoin amount in position
        amount_usd: USD amount invested
        entry_price: BTC price at entry
        entry_time: ISO timestamp of entry
        stop_loss: Stop-loss price (optional)
        current_price: Current BTC price (updated by manager)
        exit_price: BTC price at exit (if closed)
        exit_time: ISO timestamp of exit (if closed)
        status: Position status ("open", "closed", "stopped")
        unrealized_pnl: Current unrealized profit/loss in USD
        unrealized_pnl_pct: Current unrealized P&L percentage
        realized_pnl: Final realized profit/loss in USD (after close)
        realized_pnl_pct: Final realized P&L percentage (after close)
        metadata: Additional custom data (RAG insights, triggers, etc.)

    Example:
        >>> position = Position(
        ...     position_id="SWING-20250512-143022",
        ...     strategy="swing",
        ...     amount_btc=0.016,
        ...     amount_usd=1000.0,
        ...     entry_price=62500.0,
        ...     stop_loss=60725.0,  # 1.5 ATR below entry
        ...     status="open",
        ...     metadata={"signal": "RSI_oversold", "rag_success_rate": 0.72}
        ... )
    """

    # Core identification
    position_id: str = Field(
        ...,
        description="Unique position identifier (e.g., 'DCA-20250512-143022')"
    )

    strategy: Literal["dca", "swing", "day"] = Field(
        ...,
        description="Trading strategy for this position"
    )

    # Position sizing
    amount_btc: float = Field(
        ...,
        gt=0,
        description="Amount of Bitcoin in position"
    )

    amount_usd: float = Field(
        ...,
        gt=0,
        description="USD amount invested at entry"
    )

    # Entry details
    entry_price: float = Field(
        ...,
        gt=0,
        description="BTC price at entry (USD)"
    )

    entry_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Entry timestamp (ISO format)"
    )

    # Risk management
    stop_loss: Optional[float] = Field(
        default=None,
        description="Stop-loss price (USD), calculated as Entry - (k * ATR)"
    )

    # Current state (updated by manager)
    current_price: Optional[float] = Field(
        default=None,
        description="Current BTC price (updated by manager)"
    )

    # Exit details
    exit_price: Optional[float] = Field(
        default=None,
        description="BTC price at exit (USD)"
    )

    exit_time: Optional[str] = Field(
        default=None,
        description="Exit timestamp (ISO format)"
    )

    # Status
    status: Literal["open", "closed", "stopped"] = Field(
        default="open",
        description="Position status: open, closed (manual), stopped (stop-loss)"
    )

    # P&L tracking
    unrealized_pnl: Optional[float] = Field(
        default=None,
        description="Current unrealized profit/loss (USD)"
    )

    unrealized_pnl_pct: Optional[float] = Field(
        default=None,
        description="Current unrealized P&L percentage"
    )

    realized_pnl: Optional[float] = Field(
        default=None,
        description="Final realized profit/loss (USD) after close"
    )

    realized_pnl_pct: Optional[float] = Field(
        default=None,
        description="Final realized P&L percentage after close"
    )

    # Additional data
    metadata: Optional[Dict] = Field(
        default_factory=dict,
        description="Additional metadata (RAG insights, triggers, Binance order IDs, etc.)"
    )

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v: Optional[float], info) -> Optional[float]:
        """Validate stop-loss is below entry price for long positions."""
        if v is not None and "entry_price" in info.data:
            entry_price = info.data["entry_price"]
            if v >= entry_price:
                raise ValueError(
                    f"Stop-loss ({v}) must be below entry price ({entry_price}) for long positions"
                )
        return v

    @field_validator("exit_price")
    @classmethod
    def validate_exit_price(cls, v: Optional[float]) -> Optional[float]:
        """Validate exit price is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError(f"Exit price must be positive (got {v})")
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        validate_assignment = True

    def update_current_price(self, price: float) -> None:
        """
        Update current price and recalculate unrealized P&L.

        Args:
            price: Current BTC market price
        """
        self.current_price = price

        if self.status == "open":
            self.unrealized_pnl = (price - self.entry_price) * self.amount_btc
            self.unrealized_pnl_pct = (price - self.entry_price) / self.entry_price

    def get_hold_time_seconds(self) -> float:
        """
        Calculate how long position has been held in seconds.

        Returns:
            float: Hold time in seconds
        """
        entry_dt = datetime.fromisoformat(self.entry_time)

        if self.exit_time:
            exit_dt = datetime.fromisoformat(self.exit_time)
            return (exit_dt - entry_dt).total_seconds()
        else:
            return (datetime.now() - entry_dt).total_seconds()

    def is_stop_loss_triggered(self, current_price: float) -> bool:
        """
        Check if stop-loss is triggered at current price.

        Args:
            current_price: Current BTC market price

        Returns:
            bool: True if stop-loss triggered
        """
        if self.stop_loss is None or self.status != "open":
            return False

        return current_price <= self.stop_loss

    def to_dict(self) -> Dict:
        """Convert position to dictionary for JSON serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict) -> "Position":
        """Create Position from dictionary."""
        return cls(**data)

    def __repr__(self) -> str:
        """String representation for logging."""
        if self.status == "open":
            return (
                f"Position({self.position_id}, {self.strategy.upper()}, "
                f"{self.amount_btc:.6f} BTC @ ${self.entry_price:,.2f}, "
                f"Stop: ${self.stop_loss:,.2f}, "
                f"UnrealizedP&L: {self.unrealized_pnl_pct:+.2%})"
            )
        else:
            return (
                f"Position({self.position_id}, {self.strategy.upper()}, "
                f"{self.status.upper()}, "
                f"RealizedP&L: ${self.realized_pnl:,.2f} ({self.realized_pnl_pct:+.2%}))"
            )
