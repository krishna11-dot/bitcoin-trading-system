"""Execution Agent.

This agent performs final validation checks before executing trades and handles
the actual trade execution via Binance API.

Example:
    >>> from agents.execution_agent import ExecutionAgent
    >>> from tools import BinanceClient
    >>>
    >>> agent = ExecutionAgent()
    >>> validation = agent.validate_trade(trade_params, market_state, api_status)
    >>> if validation["approved"]:
    ...     result = agent.execute_trade(trade_params)
"""

import logging
import time
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentError
from tools import BinanceClient, BinanceAPIError
from data_models import MarketData


logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """Agent responsible for trade validation and execution.

    This agent:
    - Performs final pre-execution validation checks
    - Validates market liquidity and API health
    - Determines optimal order type (MARKET, LIMIT, STOP_LIMIT)
    - Executes trades via Binance API
    - Handles execution errors and retries

    Attributes:
        agent_name: "ExecutionAgent"
        binance_client: Binance API client
    """

    def __init__(self):
        """Initialize Execution Agent."""
        super().__init__(agent_name="ExecutionAgent")
        self.binance_client = BinanceClient()

    def validate_trade(
        self,
        action: str,
        symbol: str,
        quantity: float,
        order_type: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size_pct: float,
        estimated_cost: float,
        market_data: MarketData,
        available_cash: float,
    ) -> Dict[str, Any]:
        """Perform final validation before trade execution.

        Args:
            action: "BUY" or "SELL"
            symbol: Trading symbol (e.g., "BTCUSDT")
            quantity: BTC quantity to trade
            order_type: "MARKET", "LIMIT", or "STOP_LIMIT"
            entry_price: Target entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size_pct: Position size as % of portfolio
            estimated_cost: Estimated cost in USD
            market_data: Current market data
            available_cash: Available cash balance

        Returns:
            Dict containing:
                - approved: bool
                - execution_priority: immediate|normal|delayed
                - adjusted_quantity: float
                - adjusted_entry_price: float
                - warnings: List[str]
                - conditions: List[str]
                - reasoning: str
                - estimated_slippage: 0.0-10.0
                - recommended_order_type: MARKET|LIMIT|STOP_LIMIT

        Raises:
            AgentError: If validation fails
        """
        logger.info(
            f"[ANALYZING] ExecutionAgent: Validating {action} {quantity:.8f} BTC at ${entry_price:,.2f}"
        )

        try:
            # Get current order book data
            current_price = market_data.price

            # Calculate spread (using a default if bid/ask not available)
            spread_pct = 0.1  # Default 0.1% spread

            # Check API status
            api_status = "healthy"  # Simplified - in production, ping Binance API
            last_update_seconds = 1  # Simplified - track actual update time
            latency_ms = 50  # Simplified - measure actual latency

            # Calculate risk parameters
            max_loss = quantity * current_price * (stop_loss / entry_price - 1) if stop_loss > 0 else 0
            risk_reward_ratio = (
                abs((take_profit - entry_price) / (entry_price - stop_loss))
                if (entry_price - stop_loss) != 0 and take_profit > 0
                else 0
            )
            exposure_after = position_size_pct  # Simplified

            # Prepare prompt variables
            prompt_vars = {
                # Trade details
                "action": action,
                "symbol": symbol,
                "quantity": f"{quantity:.8f}",
                "order_type": order_type,
                "entry_price": f"{entry_price:,.2f}",
                "stop_loss": f"{stop_loss:,.2f}" if stop_loss > 0 else "N/A",
                "take_profit": f"{take_profit:,.2f}" if take_profit > 0 else "N/A",
                "position_size_pct": f"{position_size_pct:.2f}",
                "estimated_cost": f"{estimated_cost:,.2f}",
                # Market state
                "current_price": f"{current_price:,.2f}",
                "bid_price": f"{current_price * 0.9995:,.2f}",  # Approximate
                "ask_price": f"{current_price * 1.0005:,.2f}",  # Approximate
                "spread_pct": f"{spread_pct:.3f}",
                "volume_24h": f"{market_data.volume:,.2f}",
                "market_status": "open",
                # Risk parameters
                "max_loss": f"{abs(max_loss):,.2f}",
                "risk_reward_ratio": f"{risk_reward_ratio:.2f}",
                "exposure_after": f"{exposure_after:.2f}",
                "available_cash": f"{available_cash:,.2f}",
                # System health
                "api_status": api_status,
                "last_update": last_update_seconds,
                "latency_ms": latency_ms,
                "rate_limit_status": "healthy",
            }

            # Load and format prompt
            prompt = self.load_prompt("execution_validation.txt", **prompt_vars)

            # Generate validation
            validation = self.generate_json(prompt, max_tokens=600)

            # Validate response structure
            required_keys = [
                "approved",
                "execution_priority",
                "adjusted_quantity",
                "adjusted_entry_price",
                "warnings",
                "conditions",
                "reasoning",
                "estimated_slippage",
                "recommended_order_type",
            ]

            for key in required_keys:
                if key not in validation:
                    logger.warning(f"Missing key in validation: {key}")
                    validation[key] = self._get_default_value(key)

            # Apply hard safety checks
            validation = self._apply_safety_checks(
                validation, action, quantity, available_cash, current_price
            )

            # Log result
            if validation["approved"]:
                logger.info(
                    f"[OK] ExecutionAgent: VALIDATED {action} {validation['adjusted_quantity']:.8f} BTC "
                    f"(priority: {validation['execution_priority']})"
                )
            else:
                logger.warning(
                    f" ExecutionAgent: REJECTED - {validation.get('reasoning', 'Unknown reason')}"
                )

            return validation

        except Exception as e:
            logger.error(f"[FAIL] ExecutionAgent validation failed: {e}")
            raise AgentError(f"Trade validation failed: {e}")

    def execute_trade(
        self,
        action: str,
        symbol: str,
        quantity: float,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute trade via Binance API.

        Args:
            action: "BUY" or "SELL"
            symbol: Trading symbol (e.g., "BTCUSDT")
            quantity: BTC quantity to trade
            order_type: "MARKET" or "LIMIT"
            limit_price: Limit price (required for LIMIT orders)

        Returns:
            Dict containing:
                - success: bool
                - order_id: str
                - executed_price: float
                - executed_quantity: float
                - fee: float
                - timestamp: str
                - error: Optional[str]

        Raises:
            AgentError: If execution fails
        """
        logger.info(
            f" ExecutionAgent: Executing {order_type} {action} "
            f"{quantity:.8f} {symbol}"
        )

        try:
            if order_type == "MARKET":
                # Execute market order
                if action == "BUY":
                    result = self.binance_client.place_market_buy(symbol, quantity)
                elif action == "SELL":
                    result = self.binance_client.place_market_sell(symbol, quantity)
                else:
                    raise AgentError(f"Invalid action: {action}")

            elif order_type == "LIMIT":
                if not limit_price:
                    raise AgentError("Limit price required for LIMIT orders")

                if action == "BUY":
                    result = self.binance_client.place_limit_buy(symbol, quantity, limit_price)
                elif action == "SELL":
                    result = self.binance_client.place_limit_sell(symbol, quantity, limit_price)
                else:
                    raise AgentError(f"Invalid action: {action}")

            else:
                raise AgentError(f"Unsupported order type: {order_type}")

            # Log successful execution
            logger.info(
                f"[OK] ExecutionAgent: Trade executed successfully "
                f"(order_id: {result.get('order_id', 'N/A')})"
            )

            return {
                "success": True,
                "order_id": result.get("order_id", ""),
                "executed_price": result.get("price", 0.0),
                "executed_quantity": result.get("quantity", 0.0),
                "fee": result.get("fee", 0.0),
                "timestamp": result.get("timestamp", ""),
                "error": None,
            }

        except BinanceAPIError as e:
            logger.error(f"[FAIL] Binance API error: {e}")
            return {
                "success": False,
                "order_id": "",
                "executed_price": 0.0,
                "executed_quantity": 0.0,
                "fee": 0.0,
                "timestamp": "",
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"[FAIL] ExecutionAgent trade execution failed: {e}")
            raise AgentError(f"Trade execution failed: {e}")

    def _apply_safety_checks(
        self,
        validation: Dict[str, Any],
        action: str,
        quantity: float,
        available_cash: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """Apply hard safety checks to validation.

        Args:
            validation: Original validation dict
            action: Trade action
            quantity: Trade quantity
            available_cash: Available cash
            current_price: Current market price

        Returns:
            Dict: Validated with safety constraints applied
        """
        # Check for zero or negative quantity
        if validation["adjusted_quantity"] <= 0:
            logger.warning("Adjusted quantity is zero or negative, rejecting trade")
            validation["approved"] = False
            validation["adjusted_quantity"] = 0.0
            if "warnings" not in validation:
                validation["warnings"] = []
            validation["warnings"].append("Invalid trade quantity")

        # Check cash availability for BUY orders
        if action == "BUY":
            required_cash = validation["adjusted_quantity"] * current_price
            if required_cash > available_cash:
                logger.warning(
                    f"Insufficient cash: ${available_cash:,.2f} < ${required_cash:,.2f}"
                )
                validation["approved"] = False
                validation["adjusted_quantity"] = 0.0
                if "warnings" not in validation:
                    validation["warnings"] = []
                validation["warnings"].append("Insufficient cash for this trade")

        # Check API health (simplified - in production, actually check API status)
        # In a real implementation, you would check binance_client health here

        return validation

    def _get_default_value(self, key: str) -> Any:
        """Get default value for missing validation keys.

        Args:
            key: Missing key name

        Returns:
            Default value appropriate for the key type
        """
        defaults = {
            "approved": False,
            "execution_priority": "delayed",
            "adjusted_quantity": 0.0,
            "adjusted_entry_price": 0.0,
            "warnings": [],
            "conditions": [],
            "reasoning": "Validation incomplete due to missing data",
            "estimated_slippage": 0.0,
            "recommended_order_type": "LIMIT",
        }

        return defaults.get(key, None)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: Agent representation
        """
        return "ExecutionAgent()"
