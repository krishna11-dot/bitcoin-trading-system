"""Enhanced Position Manager for autonomous Bitcoin trading system.

This module provides comprehensive position tracking, budget management, ATR-based
stop-loss calculations, and emergency safeguards for 24/7 autonomous trading.

Features:
    - Multi-strategy support (DCA, Swing, Day trading)
    - ATR-based dynamic stop-losses
    - Per-strategy budget allocation limits
    - Emergency portfolio safeguards (-25% trigger)
    - Time-based DCA intervals
    - Real-time position monitoring
    - RAG prediction tracking (optional)
    - Binance order execution
    - Thread-safe singleton pattern
    - Persistent JSON storage

Example:
    >>> from tools.position_manager import PositionManager
    >>>
    >>> # Initialize (singleton)
    >>> manager = PositionManager(initial_budget=10000.0)
    >>>
    >>> # Open DCA position
    >>> can_open, reason = manager.can_open_dca_position(500)
    >>> if can_open:
    >>>     pos = manager.open_dca_position(
    >>>         btc_price=62000,
    >>>         amount_usd=500,
    >>>         atr=850,
    >>>         drop_pct=0.032
    >>>     )
    >>>
    >>> # Monitor positions (in main loop every 30 mins)
    >>> result = manager.update_all_positions(current_price=61500)
    >>> if result["emergency_triggered"]:
    >>>     manager.close_all_positions(current_price=61500)
    >>>
    >>> # Check stop-losses
    >>> triggered = manager.check_stop_losses(current_price=61500)
    >>> for pos in triggered:
    >>>     manager.execute_stop_loss(pos, current_price=61500)
"""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

from data_models.positions import Position
from data_models.portfolio import PortfolioState

# Configure logger
logger = logging.getLogger(__name__)


class PositionManager:
    """
    Enhanced position manager for autonomous Bitcoin trading.

    This manager handles all aspects of position lifecycle management including:
    - Opening positions with strategy-specific risk parameters
    - Calculating ATR-based stop-losses
    - Monitoring positions in real-time
    - Executing stop-losses automatically
    - Managing budget allocation across strategies
    - Triggering emergency safeguards
    - Tracking RAG prediction accuracy (optional)
    - Persisting state to JSON storage

    Architecture:
        - Singleton pattern (one instance per application)
        - Thread-safe with threading.Lock
        - Atomic file writes for data integrity
        - Comprehensive logging for all operations

    Strategy Configurations:
        DCA: k=2.0, max 50% allocation, 1 hour between buys
        Swing: k=1.5, max 30% allocation, 1 hour min hold
        Day: k=1.0, max 20% allocation, 15 min min hold (disabled by default)

    Emergency Safeguards:
        - Triggers at -25% portfolio loss
        - Blocks all new positions
        - Sends critical alerts
        - Optionally auto-closes all positions
    """

    _instance = None
    _lock = threading.Lock()

    # Strategy configurations
    STRATEGY_DEFAULTS = {
        "dca": {
            "atr_multiplier": 2.0,  # Wider stops for long-term
            "allocation_limit": 0.5,  # Max 50% of budget
            "min_hold_time": 86400,  # 24 hours
            "time_between_buys": 3600,  # 1 hour between DCA
            "enabled": True,
        },
        "swing": {
            "atr_multiplier": 1.5,  # Moderate stops
            "allocation_limit": 0.3,  # Max 30% of budget
            "min_hold_time": 3600,  # 1 hour
            "enabled": True,
        },
        "day": {
            "atr_multiplier": 1.0,  # Tight stops
            "allocation_limit": 0.2,  # Max 20% of budget
            "min_hold_time": 900,  # 15 minutes
            "enabled": False,  # Disabled by default (risky)
        },
    }

    # Global safeguards
    EMERGENCY_STOP_THRESHOLD = -0.25  # -25% portfolio loss
    MAX_TOTAL_ALLOCATION = 0.95  # Keep 5% cash buffer

    def __new__(cls, *args, **kwargs):
        """Singleton pattern - ensure only one instance exists."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, initial_budget: float = 10000.0, positions_file: str = "data/positions.json"
    ):
        """
        Initialize position manager.

        Args:
            initial_budget: Starting capital in USD (default: 10000.0)
            positions_file: Path to positions JSON file
        """
        # Prevent re-initialization
        if hasattr(self, "_initialized"):
            return

        self.initial_budget = initial_budget
        self.positions_file = Path(positions_file)
        self.positions: List[Position] = []
        self._operation_lock = threading.Lock()
        self.emergency_mode = False
        self.last_dca_time: Optional[datetime] = None

        # Ensure data directory exists
        self.positions_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing positions
        self._load_positions()

        self._initialized = True

        # Log initialization
        stats = self.get_budget_stats()
        logger.info(
            f"Position Manager initialized:\n"
            f"   Budget: ${self.initial_budget:,.2f}\n"
            f"   Allocated: ${stats['allocated_capital']:,.2f} "
            f"({stats['allocation_pct']:.1%})\n"
            f"   Available: ${stats['available_capital']:,.2f}\n"
            f"   Open positions: {len(self.get_open_positions())}\n"
            f"   Emergency mode: {self.emergency_mode}"
        )

    @classmethod
    def get_instance(cls, initial_budget: float = 10000.0) -> "PositionManager":
        """
        Get singleton instance of PositionManager.

        Args:
            initial_budget: Only used on first initialization

        Returns:
            PositionManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls(initial_budget=initial_budget)
        return cls._instance

    # =========================================================================
    # POSITION OPENING METHODS
    # =========================================================================

    def open_position(
        self,
        strategy: str,
        btc_price: float,
        amount_usd: float,
        atr: float,
        reason: str = "",
        metadata: Optional[Dict] = None,
        rag_context: Optional[Dict] = None,
    ) -> Position:
        """
        Open new position with strategy-specific stop-loss.

        Steps:
        1. Validate strategy enabled
        2. Check emergency mode
        3. Check budget availability and limits
        4. Calculate ATR-based stop-loss
        5. Execute market buy on Binance (if configured)
        6. Create Position object
        7. Add RAG insights (if provided)
        8. Add to tracking
        9. Save to file
        10. Log and return

        Args:
            strategy: "dca", "swing", or "day"
            btc_price: Current BTC price
            amount_usd: Amount to invest in USD
            atr: Current ATR(14) value
            reason: Human-readable reason for position
            metadata: Additional metadata dict
            rag_context: Optional RAG insights

        Returns:
            Position: The opened position

        Raises:
            ValueError: If validation fails

        Example:
            >>> pos = manager.open_position(
            >>>     strategy="swing",
            >>>     btc_price=62000,
            >>>     amount_usd=1000,
            >>>     atr=850,
            >>>     reason="RSI oversold + volume spike",
            >>>     rag_context={"success_rate": 0.72}
            >>> )
        """
        with self._operation_lock:
            # 1. Check strategy enabled
            if not self.STRATEGY_DEFAULTS[strategy]["enabled"]:
                raise ValueError(f"{strategy.upper()} strategy is disabled")

            # 2. Check emergency mode
            if self.emergency_mode:
                raise ValueError("Cannot open position: Emergency mode active")

            # 3. Check budget
            can_allocate, check_reason = self.can_allocate(strategy, amount_usd)
            if not can_allocate:
                raise ValueError(f"Cannot allocate: {check_reason}")

            # 4. Calculate stop-loss
            stop_loss = self.calculate_stop_loss(strategy, btc_price, atr)

            # 5. Execute market buy on Binance (if available)
            executed_price = btc_price
            amount_btc = amount_usd / btc_price
            order_id = None

            try:
                from tools.binance_client import BinanceClient

                client = BinanceClient()

                # Place market buy order
                order = client.place_market_order(side="BUY", quantity=amount_btc)

                # Get actual execution details
                if order and "fills" in order:
                    executed_price = float(order["fills"][0].get("price", btc_price))
                    executed_qty = float(order.get("executedQty", amount_btc))
                    amount_btc = executed_qty
                    order_id = order.get("orderId")

                    logger.info(f"Binance order executed: {order_id}")

            except ImportError:
                logger.warning(
                    "Binance client not available, simulating order execution"
                )
            except Exception as e:
                logger.error(f"Binance order failed: {e}, using simulation")

            # 6. Create position
            position = Position(
                position_id=f"{strategy.upper()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                strategy=strategy,
                amount_btc=amount_btc,
                amount_usd=amount_usd,
                entry_price=executed_price,
                entry_time=datetime.now().isoformat(),
                stop_loss=stop_loss,
                status="open",
                metadata=metadata or {},
            )

            # 7. Add RAG insights
            if rag_context:
                self.add_rag_insights(position, rag_context)

            # 8. Add metadata
            position.metadata.update(
                {
                    "reason": reason,
                    "atr_used": atr,
                    "atr_multiplier": self.STRATEGY_DEFAULTS[strategy]["atr_multiplier"],
                }
            )

            if order_id:
                position.metadata["binance_order_id"] = order_id

            # 9. Track position
            self.positions.append(position)

            # 10. Update DCA timing if applicable
            if strategy == "dca":
                self.last_dca_time = datetime.now()

            self._save_positions()

            # Log
            log_msg = (
                f"{strategy.upper()} position opened: {position.position_id}\n"
                f"   Amount: {amount_btc:.6f} BTC (${amount_usd:,.2f})\n"
                f"   Entry: ${executed_price:,.2f}\n"
                f"   Stop: ${stop_loss:,.2f} "
                f"(ATR: ${atr:,.0f} x {self.STRATEGY_DEFAULTS[strategy]['atr_multiplier']})\n"
                f"   Reason: {reason}"
            )

            if rag_context:
                log_msg += (
                    f"\n   RAG: {rag_context.get('success_rate', 0):.0%} success rate, "
                    f"expected {rag_context.get('expected_outcome', 0):+.2%}"
                )

            logger.info(log_msg)

            return position

    def open_dca_position(
        self,
        btc_price: float,
        amount_usd: float,
        atr: float,
        drop_pct: Optional[float] = None,
        time_based: bool = False,
        rag_context: Optional[Dict] = None,
    ) -> Position:
        """
        Convenience method for DCA positions.

        Supports both price-based and time-based triggers.

        Args:
            btc_price: Current BTC price
            amount_usd: Amount to invest
            atr: Current ATR value
            drop_pct: Price drop % that triggered (if price-based)
            time_based: True if triggered by time interval
            rag_context: Optional RAG insights

        Returns:
            Position: DCA position

        Example:
            >>> # Price-based DCA
            >>> pos = manager.open_dca_position(
            >>>     btc_price=60000,
            >>>     amount_usd=500,
            >>>     atr=850,
            >>>     drop_pct=0.032  # 3.2% drop
            >>> )
            >>>
            >>> # Time-based DCA
            >>> pos = manager.open_dca_position(
            >>>     btc_price=60000,
            >>>     amount_usd=500,
            >>>     atr=850,
            >>>     time_based=True
            >>> )
        """
        # Build reason
        if time_based:
            reason = "DCA: Time-based interval"
        elif drop_pct:
            reason = f"DCA: BTC dropped {drop_pct:.1%}"
        else:
            reason = "DCA: Manual trigger"

        # Build metadata
        metadata = {"trigger_type": "time" if time_based else "price", "drop_pct": drop_pct}

        return self.open_position(
            strategy="dca",
            btc_price=btc_price,
            amount_usd=amount_usd,
            atr=atr,
            reason=reason,
            metadata=metadata,
            rag_context=rag_context,
        )

    def open_swing_position(
        self,
        btc_price: float,
        amount_usd: float,
        atr: float,
        signal: str = "technical",
        rag_context: Optional[Dict] = None,
    ) -> Position:
        """
        Convenience method for swing trading positions.

        Example:
            >>> pos = manager.open_swing_position(
            >>>     btc_price=62500,
            >>>     amount_usd=1000,
            >>>     atr=850,
            >>>     signal="RSI_oversold + MACD_crossover"
            >>> )
        """
        return self.open_position(
            strategy="swing",
            btc_price=btc_price,
            amount_usd=amount_usd,
            atr=atr,
            reason=f"Swing: {signal}",
            metadata={"signal": signal},
            rag_context=rag_context,
        )

    def open_day_position(
        self,
        btc_price: float,
        amount_usd: float,
        atr: float,
        pattern: str = "breakout",
        rag_context: Optional[Dict] = None,
    ) -> Position:
        """Convenience method for day trading positions."""
        return self.open_position(
            strategy="day",
            btc_price=btc_price,
            amount_usd=amount_usd,
            atr=atr,
            reason=f"Day: {pattern}",
            metadata={"pattern": pattern},
            rag_context=rag_context,
        )

    # =========================================================================
    # MONITORING METHODS
    # =========================================================================

    def update_all_positions(self, current_price: float) -> Dict:
        """
        Update all open positions with current market price.

        Calculates:
        - Unrealized P&L for each position
        - Total portfolio value
        - Portfolio P&L percentage
        - Large moves (>2% change)

        Triggers:
        - Emergency mode check if portfolio down 25%

        Args:
            current_price: Current BTC market price

        Returns:
            {
                "positions_updated": 5,
                "total_unrealized_pnl": 325.50,
                "portfolio_value": 10325.50,
                "portfolio_pnl_pct": 0.0326,
                "emergency_triggered": False,
                "positions_with_large_moves": [...]
            }
        """
        with self._operation_lock:
            updated = 0
            large_moves = []

            # Get open positions directly (avoid nested lock acquisition)
            open_positions = [p for p in self.positions if p.status == "open"]

            for position in open_positions:
                old_pnl_pct = position.unrealized_pnl_pct or 0

                # Update price and P&L
                position.update_current_price(current_price)

                # Track significant moves (>2% change)
                if position.unrealized_pnl_pct:
                    pnl_change = abs(position.unrealized_pnl_pct - old_pnl_pct)
                    if pnl_change > 0.02:
                        large_moves.append(
                            {
                                "position_id": position.position_id,
                                "old_pnl_pct": old_pnl_pct,
                                "new_pnl_pct": position.unrealized_pnl_pct,
                                "change": position.unrealized_pnl_pct - old_pnl_pct,
                                "unrealized_pnl": position.unrealized_pnl,
                            }
                        )

                        logger.info(
                            f"Large move detected: {position.position_id} "
                            f"{old_pnl_pct:+.2%} -> {position.unrealized_pnl_pct:+.2%}"
                        )

                updated += 1

            if updated > 0:
                self._save_positions()

        # Calculate portfolio stats OUTSIDE lock to avoid deadlock
        stats = self.get_budget_stats()
        total_pnl = stats["unrealized_pnl"]
        portfolio_value = stats["portfolio_value"]
        portfolio_pnl_pct = (
            (portfolio_value - self.initial_budget) / self.initial_budget
        )

        # Check emergency condition OUTSIDE lock to avoid deadlock
        emergency_triggered, emergency_details = self.check_emergency_condition(
            current_price
        )

        return {
            "positions_updated": updated,
            "total_unrealized_pnl": total_pnl,
            "portfolio_value": portfolio_value,
            "portfolio_pnl_pct": portfolio_pnl_pct,
            "emergency_triggered": emergency_triggered,
            "positions_with_large_moves": large_moves,
        }

    def check_stop_losses(self, current_price: float) -> List[Position]:
        """
        Check if any open positions hit their stop-loss price.

        Does NOT execute orders - just identifies positions.
        Actual execution happens in execute_stop_loss().

        Args:
            current_price: Current BTC market price

        Returns:
            List of positions that triggered stop-loss
        """
        triggered = []

        with self._operation_lock:
            # Get open positions directly (avoid nested lock acquisition)
            open_positions = [p for p in self.positions if p.status == "open"]

            for position in open_positions:
                if position.is_stop_loss_triggered(current_price):
                    loss_pct = (current_price - position.entry_price) / position.entry_price

                    logger.warning(
                        f"STOP-LOSS TRIGGERED: {position.position_id}\n"
                        f"   Strategy: {position.strategy.upper()}\n"
                        f"   Entry: ${position.entry_price:,.2f}\n"
                        f"   Stop: ${position.stop_loss:,.2f}\n"
                        f"   Current: ${current_price:,.2f}\n"
                        f"   Loss: {loss_pct:.2%}"
                    )

                    triggered.append(position)

        return triggered

    def execute_stop_loss(self, position: Position, current_price: float) -> Dict:
        """
        Execute stop-loss order on Binance.

        Steps:
        1. Place market sell order on Binance
        2. Update position status to "stopped"
        3. Calculate realized P&L
        4. Free up allocated capital
        5. Compare with RAG prediction (if available)
        6. Save to file
        7. Log execution

        Args:
            position: Position to close
            current_price: Execution price

        Returns:
            {
                "position_id": "SWING-20250511-143022",
                "order_id": "12345678",
                "realized_pnl": -125.50,
                "realized_pnl_pct": -0.0256,
                "execution_price": 60900.0,
                "capital_freed": 1000.0,
                "rag_expected": 0.0294,
                "rag_accuracy": 0.0550
            }

        Raises:
            Exception: If Binance order fails critically
        """
        with self._operation_lock:
            executed_price = current_price
            order_id = None

            # Execute market sell on Binance (if available)
            try:
                from tools.binance_client import BinanceClient

                client = BinanceClient()
                order = client.place_market_order(side="SELL", quantity=position.amount_btc)

                # Get execution details
                if order and "fills" in order:
                    executed_price = float(order["fills"][0].get("price", current_price))
                    order_id = order.get("orderId")

                logger.info(f"Stop-loss order executed: {order_id}")

            except ImportError:
                logger.warning("Binance client not available, simulating execution")
            except Exception as e:
                logger.error(f"Binance sell failed: {e}, using simulation")

            # Update position
            position.status = "stopped"
            position.current_price = executed_price
            position.exit_price = executed_price
            position.exit_time = datetime.now().isoformat()

            # Calculate P&L
            realized_pnl = (executed_price - position.entry_price) * position.amount_btc
            realized_pnl_pct = (executed_price - position.entry_price) / position.entry_price

            position.realized_pnl = realized_pnl
            position.realized_pnl_pct = realized_pnl_pct

            if order_id:
                position.metadata["binance_stop_order_id"] = order_id

            # Free capital
            capital_freed = position.amount_usd

            self._save_positions()

            # Get RAG prediction if available
            rag_expected = None
            rag_accuracy = None
            if position.metadata and "rag_expected_outcome" in position.metadata:
                rag_expected = position.metadata["rag_expected_outcome"]
                rag_accuracy = abs(realized_pnl_pct - rag_expected)

            result = {
                "position_id": position.position_id,
                "order_id": order_id,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
                "execution_price": executed_price,
                "capital_freed": capital_freed,
            }

            # Add RAG comparison
            if rag_expected is not None:
                result["rag_expected"] = rag_expected
                result["rag_accuracy"] = rag_accuracy

                logger.info(
                    f"RAG Comparison:\n"
                    f"   Expected: {rag_expected:+.2%}\n"
                    f"   Actual: {realized_pnl_pct:+.2%}\n"
                    f"   Error: {rag_accuracy:.2%}"
                )

            logger.info(
                f"Stop-loss executed: {position.position_id}\n"
                f"   Realized P&L: ${realized_pnl:,.2f} ({realized_pnl_pct:+.2%})\n"
                f"   Capital freed: ${capital_freed:,.2f}"
            )

            return result

    def close_position(
        self, position_id: str, close_price: float, reason: str = "manual"
    ) -> Position:
        """
        Close position manually (not via stop-loss).

        Use cases:
        - Take profit hit
        - Manual user closure
        - Strategy signal reversal
        - Emergency closure

        Args:
            position_id: Position to close
            close_price: Exit price
            reason: Reason for closing

        Returns:
            Updated position

        Raises:
            ValueError: If position not found or not open
        """
        with self._operation_lock:
            position = self.get_position(position_id)

            if not position:
                raise ValueError(f"Position {position_id} not found")

            if position.status != "open":
                raise ValueError(
                    f"Position {position_id} is not open (status: {position.status})"
                )

            executed_price = close_price
            order_id = None

            # Execute on Binance
            try:
                from tools.binance_client import BinanceClient

                client = BinanceClient()
                order = client.place_market_order(side="SELL", quantity=position.amount_btc)

                if order and "fills" in order:
                    executed_price = float(order["fills"][0].get("price", close_price))
                    order_id = order.get("orderId")

            except ImportError:
                logger.warning("Binance client not available, simulating")
            except Exception as e:
                logger.error(f"Binance close failed: {e}")

            # Update position
            position.status = "closed"
            position.exit_price = executed_price
            position.current_price = executed_price
            position.exit_time = datetime.now().isoformat()

            # Calculate P&L
            position.realized_pnl = (
                executed_price - position.entry_price
            ) * position.amount_btc
            position.realized_pnl_pct = (
                executed_price - position.entry_price
            ) / position.entry_price

            # Add close reason
            if not position.metadata:
                position.metadata = {}
            position.metadata["close_reason"] = reason
            if order_id:
                position.metadata["binance_close_order_id"] = order_id

            self._save_positions()

            logger.info(
                f"Position closed: {position_id}\n"
                f"   Realized P&L: ${position.realized_pnl:,.2f} "
                f"({position.realized_pnl_pct:+.2%})\n"
                f"   Reason: {reason}"
            )

            return position

    def close_all_positions(self, current_price: float) -> List[Dict]:
        """
        Emergency: Close all open positions immediately.

        Used when:
        - Emergency threshold hit (-25%)
        - User manual stop
        - System shutdown

        Args:
            current_price: Current market price

        Returns:
            List of execution results
        """
        results = []

        for position in self.get_open_positions():
            try:
                result = self.close_position(
                    position_id=position.position_id,
                    close_price=current_price,
                    reason="emergency_close",
                )
                results.append(
                    {
                        "position_id": result.position_id,
                        "realized_pnl": result.realized_pnl,
                        "success": True,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to close {position.position_id}: {e}")
                results.append(
                    {"position_id": position.position_id, "error": str(e), "success": False}
                )

        logger.warning(
            f"Emergency close completed: "
            f"{sum(1 for r in results if r['success'])}/{len(results)} successful"
        )

        return results

    # =========================================================================
    # EMERGENCY & BUDGET METHODS
    # =========================================================================

    def check_emergency_condition(self, current_price: float) -> Tuple[bool, Dict]:
        """
        Check if portfolio hit emergency threshold (-25%).

        Calculation:
        1. Get budget stats (available cash + position values)
        2. Calculate portfolio P&L vs initial budget
        3. If P&L <= -25%, trigger emergency mode

        Actions when triggered:
        - Set self.emergency_mode = True
        - Log critical alert
        - Block all new positions
        - Return emergency details

        Args:
            current_price: Current BTC price

        Returns:
            (emergency_triggered: bool, details: Dict)
        """
        stats = self.get_budget_stats()
        portfolio_value = stats["portfolio_value"]
        portfolio_pnl_pct = (portfolio_value - self.initial_budget) / self.initial_budget

        details = {
            "portfolio_value": portfolio_value,
            "initial_budget": self.initial_budget,
            "portfolio_pnl": portfolio_value - self.initial_budget,
            "portfolio_pnl_pct": portfolio_pnl_pct,
            "threshold": self.EMERGENCY_STOP_THRESHOLD,
        }

        if portfolio_pnl_pct <= self.EMERGENCY_STOP_THRESHOLD and not self.emergency_mode:
            self.emergency_mode = True

            logger.critical(
                f"\n{'='*60}\n"
                f"EMERGENCY STOP TRIGGERED\n"
                f"{'='*60}\n"
                f"Portfolio Value: ${portfolio_value:,.2f}\n"
                f"Initial Budget: ${self.initial_budget:,.2f}\n"
                f"Total P&L: ${portfolio_value - self.initial_budget:,.2f} "
                f"({portfolio_pnl_pct:+.2%})\n"
                f"Threshold: {self.EMERGENCY_STOP_THRESHOLD:.2%}\n"
                f"{'='*60}\n"
                f"ALL NEW POSITIONS BLOCKED\n"
                f"Consider closing all positions immediately!\n"
                f"{'='*60}"
            )

            return True, details

        return False, details

    def can_allocate(self, strategy: str, amount_usd: float) -> Tuple[bool, str]:
        """
        Check if we can allocate capital for new position.

        Checks (in order):
        1. Emergency mode (block if True)
        2. Available capital >= amount
        3. Global allocation limit (95% max)
        4. Strategy-specific allocation limit

        Args:
            strategy: "dca", "swing", or "day"
            amount_usd: Amount to allocate

        Returns:
            (can_allocate: bool, reason: str)

        Example:
            >>> can, reason = manager.can_allocate("swing", 1000)
            >>> if not can:
            >>>     logger.warning(f"Cannot open position: {reason}")
        """
        # Check emergency
        if self.emergency_mode:
            return False, "Emergency mode active - all positions blocked"

        # Get budget stats
        stats = self.get_budget_stats()
        available = stats["available_capital"]
        allocated = stats["allocated_capital"]

        # Check available cash
        if amount_usd > available:
            return (
                False,
                f"Insufficient capital: ${available:,.2f} available, ${amount_usd:,.2f} required",
            )

        # Check global limit (95%)
        new_allocation_pct = (allocated + amount_usd) / self.initial_budget
        if new_allocation_pct > self.MAX_TOTAL_ALLOCATION:
            return (
                False,
                f"Global allocation limit: {new_allocation_pct:.1%} > {self.MAX_TOTAL_ALLOCATION:.1%}",
            )

        # Check strategy limit
        strategy_limit = self.STRATEGY_DEFAULTS[strategy]["allocation_limit"]
        strategy_allocated = stats["by_strategy"][strategy]["allocated"]
        new_strategy_alloc = strategy_allocated + amount_usd
        new_strategy_pct = new_strategy_alloc / self.initial_budget

        if new_strategy_pct > strategy_limit:
            return (
                False,
                f"{strategy.upper()} allocation limit: "
                f"{new_strategy_pct:.1%} > {strategy_limit:.1%}",
            )

        return True, "OK"

    def can_open_dca_position(self, amount_usd: float) -> Tuple[bool, str]:
        """
        Check if DCA position can be opened.

        Additional checks beyond can_allocate():
        - DCA strategy enabled?
        - Time since last DCA >= min interval?

        Args:
            amount_usd: Amount to invest

        Returns:
            (can_open: bool, reason: str)
        """
        # Check if DCA enabled
        if not self.STRATEGY_DEFAULTS["dca"]["enabled"]:
            return False, "DCA strategy is disabled"

        # Check timing (prevent too frequent DCA)
        if self.last_dca_time:
            time_since_last = (datetime.now() - self.last_dca_time).total_seconds()
            min_interval = self.STRATEGY_DEFAULTS["dca"]["time_between_buys"]

            if time_since_last < min_interval:
                return (
                    False,
                    f"Too soon since last DCA: {time_since_last:.0f}s elapsed, "
                    f"{min_interval}s required",
                )

        # Check budget allocation
        return self.can_allocate("dca", amount_usd)

    def get_budget_stats(self) -> Dict:
        """
        Calculate current budget allocation.

        Returns:
            {
                "initial_budget": 10000.0,
                "allocated_capital": 6500.0,
                "available_capital": 3500.0,
                "allocation_pct": 0.65,
                "portfolio_value": 10800.0,
                "unrealized_pnl": 800.0,
                "realized_pnl": 150.0,
                "total_pnl": 950.0,
                "by_strategy": {...}
            }
        """
        open_pos = self.get_open_positions()
        closed_pos = self.get_all_positions("closed")
        stopped_pos = self.get_all_positions("stopped")

        # Allocated capital (in open positions)
        allocated = sum(p.amount_usd for p in open_pos)

        # Available capital
        available = self.initial_budget - allocated

        # Unrealized P&L
        unrealized_pnl = sum(p.unrealized_pnl or 0 for p in open_pos)

        # Realized P&L
        realized_pnl = sum(p.realized_pnl or 0 for p in closed_pos + stopped_pos)

        # Portfolio value (cash + position values)
        portfolio_value = available + allocated + unrealized_pnl

        # By strategy
        by_strategy = {}
        for strategy in ["dca", "swing", "day"]:
            strategy_positions = [p for p in open_pos if p.strategy == strategy]
            strategy_allocated = sum(p.amount_usd for p in strategy_positions)

            by_strategy[strategy] = {
                "count": len(strategy_positions),
                "allocated": strategy_allocated,
                "allocation_pct": strategy_allocated / self.initial_budget,
            }

        return {
            "initial_budget": self.initial_budget,
            "allocated_capital": allocated,
            "available_capital": available,
            "allocation_pct": allocated / self.initial_budget,
            "portfolio_value": portfolio_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": unrealized_pnl + realized_pnl,
            "by_strategy": by_strategy,
        }

    def get_portfolio_state(self) -> PortfolioState:
        """
        Get current portfolio state for trading workflow.

        Calculates total BTC balance (from all open positions) and available USD balance.

        Returns:
            PortfolioState: Current portfolio with BTC/USD balances and positions

        Example:
            >>> state = manager.get_portfolio_state()
            >>> print(f"BTC: {state.btc_balance:.8f}, USD: ${state.usd_balance:.2f}")
            BTC: 0.00000000, USD: $10000.00
        """
        open_positions = self.get_open_positions()

        # Total BTC balance (sum of all open positions)
        btc_balance = sum(p.amount_btc for p in open_positions)

        # Available USD balance (initial budget minus allocated capital)
        budget_stats = self.get_budget_stats()
        usd_balance = budget_stats["available_capital"]

        return PortfolioState(
            btc_balance=btc_balance,
            usd_balance=usd_balance,
            active_positions=open_positions,
            last_updated=datetime.now().isoformat(),
        )

    # =========================================================================
    # HELPER & UTILITY METHODS
    # =========================================================================

    def calculate_stop_loss(self, strategy: str, entry_price: float, atr: float) -> float:
        """
        Calculate strategy-specific stop-loss using ATR.

        Formula: Stop = Entry Price - (ATR * k)

        Strategy multipliers:
        - DCA: k=2.0 (wider stops for long-term)
        - Swing: k=1.5 (moderate stops)
        - Day: k=1.0 (tight stops for quick exit)

        Args:
            strategy: "dca", "swing", or "day"
            entry_price: Position entry price
            atr: Current ATR(14) value

        Returns:
            float: Stop-loss price

        Example:
            >>> # DCA position
            >>> stop = manager.calculate_stop_loss("dca", 62000, 850)
            >>> # stop = 62000 - (850 * 2.0) = 60300
        """
        k = self.STRATEGY_DEFAULTS[strategy]["atr_multiplier"]
        stop_loss = entry_price - (atr * k)
        return round(stop_loss, 2)

    def add_rag_insights(
        self, position: Position, rag_context: Optional[Dict] = None
    ) -> None:
        """
        Add RAG insights to position metadata (optional).

        RAG context can include:
        - success_rate: Historical win rate (0.0-1.0)
        - expected_outcome: Expected P&L % (e.g., 0.0294)
        - similar_patterns: Number of matches found
        - confidence: RAG confidence score (0.0-1.0)

        Args:
            position: Position to update
            rag_context: RAG insights dict
        """
        if not rag_context:
            return

        if position.metadata is None:
            position.metadata = {}

        position.metadata.update(
            {
                "rag_success_rate": rag_context.get("success_rate"),
                "rag_expected_outcome": rag_context.get("expected_outcome"),
                "rag_similar_patterns": rag_context.get("similar_patterns"),
                "rag_confidence": rag_context.get("confidence"),
            }
        )

    def get_position(self, position_id: str) -> Optional[Position]:
        """Get specific position by ID."""
        with self._operation_lock:
            for position in self.positions:
                if position.position_id == position_id:
                    return position
            return None

    def get_all_positions(self, status: Optional[str] = None) -> List[Position]:
        """
        Get all positions, optionally filtered by status.

        Args:
            status: Filter by "open", "closed", or "stopped"

        Returns:
            List of positions sorted by entry time
        """
        with self._operation_lock:
            positions = self.positions.copy()

            if status:
                positions = [p for p in positions if p.status == status]

            return sorted(positions, key=lambda p: p.entry_time)

    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return self.get_all_positions("open")

    def get_statistics(self) -> Dict:
        """
        Calculate comprehensive portfolio statistics.

        Returns:
            {
                "total_positions": 15,
                "open_positions": 5,
                "closed_positions": 8,
                "stopped_positions": 2,
                "total_unrealized_pnl": 325.50,
                "total_realized_pnl": -125.00,
                "avg_realized_pnl_pct": -0.0125,
                "median_realized_pnl_pct": 0.005,
                "win_rate": 0.60,
                "best_trade_pct": 0.0842,
                "worst_trade_pct": -0.0256,
                "stdev_pnl_pct": 0.0325,
                "by_strategy": {...},
                "emergency_mode": False,
                "budget_stats": {...},
                "rag_accuracy": {...}
            }
        """
        all_pos = self.positions
        open_pos = self.get_open_positions()
        closed_pos = self.get_all_positions("closed")
        stopped_pos = self.get_all_positions("stopped")
        finished_pos = closed_pos + stopped_pos

        # Basic counts
        stats = {
            "total_positions": len(all_pos),
            "open_positions": len(open_pos),
            "closed_positions": len(closed_pos),
            "stopped_positions": len(stopped_pos),
        }

        # P&L totals
        stats["total_unrealized_pnl"] = sum(p.unrealized_pnl or 0 for p in open_pos)
        stats["total_realized_pnl"] = sum(p.realized_pnl or 0 for p in finished_pos)

        # Performance metrics (only for finished positions)
        if finished_pos:
            pnl_pcts = [p.realized_pnl_pct for p in finished_pos if p.realized_pnl_pct]

            if pnl_pcts:
                stats["avg_realized_pnl_pct"] = mean(pnl_pcts)
                stats["median_realized_pnl_pct"] = sorted(pnl_pcts)[len(pnl_pcts) // 2]
                stats["win_rate"] = sum(1 for pct in pnl_pcts if pct > 0) / len(pnl_pcts)
                stats["best_trade_pct"] = max(pnl_pcts)
                stats["worst_trade_pct"] = min(pnl_pcts)

                if len(pnl_pcts) > 1:
                    stats["stdev_pnl_pct"] = stdev(pnl_pcts)

        # By strategy
        by_strategy = {}
        for strategy in ["dca", "swing", "day"]:
            strategy_finished = [p for p in finished_pos if p.strategy == strategy]
            pnl_pcts = [
                p.realized_pnl_pct
                for p in strategy_finished
                if p.realized_pnl_pct is not None
            ]

            by_strategy[strategy] = {
                "count": len(strategy_finished),
                "win_rate": (
                    sum(1 for pct in pnl_pcts if pct > 0) / len(pnl_pcts)
                    if pnl_pcts
                    else 0
                ),
                "avg_pnl_pct": mean(pnl_pcts) if pnl_pcts else 0,
            }

        stats["by_strategy"] = by_strategy

        # Emergency & budget
        stats["emergency_mode"] = self.emergency_mode
        stats["budget_stats"] = self.get_budget_stats()

        # RAG accuracy (if used)
        rag_positions = [
            p
            for p in finished_pos
            if p.metadata and "rag_expected_outcome" in p.metadata
        ]

        if rag_positions:
            errors = [
                abs(p.realized_pnl_pct - p.metadata["rag_expected_outcome"])
                for p in rag_positions
                if p.realized_pnl_pct is not None
            ]

            stats["rag_accuracy"] = {
                "predictions_made": len(rag_positions),
                "avg_accuracy": 1 - mean(errors) if errors else 0,
                "avg_error": mean(errors) if errors else 0,
                "best_prediction": 1 - min(errors) if errors else 0,
                "worst_prediction": 1 - max(errors) if errors else 0,
            }

        return stats

    def get_rag_accuracy(self) -> Dict:
        """
        Calculate RAG prediction accuracy (if RAG used).

        Compares RAG expected_outcome vs actual realized_pnl_pct.

        Returns:
            {
                "predictions_made": 15,
                "avg_accuracy": 0.87,
                "avg_error": 0.023,
                "best_prediction": 0.98,
                "worst_prediction": 0.65
            }
        """
        finished = self.get_all_positions("closed") + self.get_all_positions("stopped")

        rag_positions = [
            p
            for p in finished
            if p.metadata
            and "rag_expected_outcome" in p.metadata
            and p.realized_pnl_pct is not None
        ]

        if not rag_positions:
            return {
                "predictions_made": 0,
                "avg_accuracy": 0,
                "avg_error": 0,
                "best_prediction": 0,
                "worst_prediction": 0,
            }

        errors = [
            abs(p.realized_pnl_pct - p.metadata["rag_expected_outcome"])
            for p in rag_positions
        ]

        return {
            "predictions_made": len(rag_positions),
            "avg_accuracy": 1 - mean(errors),
            "avg_error": mean(errors),
            "best_prediction": 1 - min(errors),
            "worst_prediction": 1 - max(errors),
        }

    # =========================================================================
    # PERSISTENCE METHODS
    # =========================================================================

    def _save_positions(self) -> None:
        """Save positions to JSON file atomically."""
        try:
            # Convert positions to dicts
            data = {
                "emergency_mode": self.emergency_mode,
                "last_dca_time": (
                    self.last_dca_time.isoformat() if self.last_dca_time else None
                ),
                "positions": [p.to_dict() for p in self.positions],
            }

            # Atomic write using temp file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.positions_file.parent, suffix=".tmp"
            )

            try:
                with os.fdopen(temp_fd, "w") as f:
                    json.dump(data, f, indent=2)

                # Atomic rename
                os.replace(temp_path, self.positions_file)

            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

        except Exception as e:
            logger.error(f"Failed to save positions: {e}")

    def _load_positions(self) -> None:
        """Load positions from JSON file."""
        if not self.positions_file.exists():
            logger.info("No existing positions file, starting fresh")
            return

        try:
            with open(self.positions_file, "r") as f:
                data = json.load(f)

            self.emergency_mode = data.get("emergency_mode", False)

            if data.get("last_dca_time"):
                self.last_dca_time = datetime.fromisoformat(data["last_dca_time"])

            self.positions = [
                Position.from_dict(p_dict) for p_dict in data.get("positions", [])
            ]

            logger.info(
                f"Loaded {len(self.positions)} positions "
                f"({len(self.get_open_positions())} open)"
            )

        except Exception as e:
            logger.error(f"Failed to load positions: {e}")
            logger.warning("Starting with empty position list")
            self.positions = []

    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_budget_stats()
        return (
            f"PositionManager(budget=${self.initial_budget:,.2f}, "
            f"allocated={stats['allocation_pct']:.1%}, "
            f"open_positions={len(self.get_open_positions())}, "
            f"emergency={self.emergency_mode})"
        )
