"""Strategy Agent.

This agent determines the optimal trading strategy (DCA, Swing, Day Trading, or HOLD)
based on market conditions, technical signals, and portfolio state.

Example:
    >>> from agents.strategy_agent import StrategyAgent
    >>> from data_models import PortfolioState
    >>>
    >>> agent = StrategyAgent()
    >>> decision = agent.execute(market_analysis, portfolio, performance_stats)
    >>> print(f"Strategy: {decision['strategy']}, Action: {decision['action']}")
"""

import logging
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentError
from data_models import PortfolioState, TechnicalIndicators
from config import Settings


logger = logging.getLogger(__name__)


class StrategyAgent(BaseAgent):
    """Agent responsible for determining trading strategy and specific actions.

    This agent:
    - Evaluates market conditions and trend
    - Selects optimal strategy (DCA, Swing, Day, or HOLD)
    - Determines specific action (BUY, SELL, HOLD)
    - Sets position sizing and entry/exit targets
    - Considers historical performance and patterns

    Attributes:
        agent_name: "StrategyAgent"
        settings: System settings with trading parameters
    """

    def __init__(self):
        """Initialize Strategy Agent."""
        super().__init__(agent_name="StrategyAgent")
        self.settings = Settings.get_instance()

    def execute(
        self,
        market_analysis: Dict[str, Any],
        indicators: TechnicalIndicators,
        portfolio: PortfolioState,
        current_price: float,
        performance_stats: Optional[Dict[str, Any]] = None,
        historical_patterns: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Determine optimal trading strategy and action.

        Args:
            market_analysis: Analysis from MarketAnalyst agent
            indicators: Current technical indicators
            portfolio: Current portfolio state
            current_price: Current BTC price
            performance_stats: Optional recent performance metrics
            historical_patterns: Optional historical pattern context

        Returns:
            Dict containing:
                - strategy: DCA|SWING|DAY|HOLD
                - action: BUY|SELL|HOLD
                - confidence: 0-100
                - position_size_pct: 0.0-100.0
                - entry_price_target: float
                - exit_price_target: float
                - holding_period: hours|days|weeks
                - reasoning: str
                - key_factors: List[str]
                - invalidation_price: float

        Raises:
            AgentError: If strategy determination fails
        """
        logger.info(
            f" StrategyAgent: Determining strategy for "
            f"{market_analysis.get('trend', 'unknown')} market"
        )

        try:
            # Calculate portfolio metrics
            btc_value = portfolio.btc_balance * current_price
            total_value = portfolio.cash_balance + btc_value
            exposure_pct = (btc_value / total_value * 100) if total_value > 0 else 0
            avg_entry = portfolio.avg_entry_price if portfolio.avg_entry_price > 0 else current_price
            unrealized_pnl = ((current_price - avg_entry) / avg_entry * 100) if avg_entry > 0 else 0

            # Determine MACD signal status
            macd_histogram = indicators.macd_histogram
            if macd_histogram > 0:
                macd_signal = "bullish cross"
            elif macd_histogram < 0:
                macd_signal = "bearish cross"
            else:
                macd_signal = "neutral"

            # Calculate price vs SMA
            price_vs_sma = ((current_price - indicators.sma_50) / indicators.sma_50 * 100)

            # Determine Bollinger position
            if indicators.bollinger_upper and indicators.bollinger_lower:
                bb_range = indicators.bollinger_upper - indicators.bollinger_lower
                if bb_range > 0:
                    bb_position_pct = (
                        (current_price - indicators.bollinger_lower) / bb_range * 100
                    )
                    if bb_position_pct > 80:
                        bollinger_position = "near upper band (overbought)"
                    elif bb_position_pct < 20:
                        bollinger_position = "near lower band (oversold)"
                    else:
                        bollinger_position = f"mid-range ({bb_position_pct:.0f}%)"
                else:
                    bollinger_position = "range too narrow"
            else:
                bollinger_position = "N/A"

            # Get performance stats or use defaults
            perf = performance_stats or {}

            # Prepare prompt variables
            prompt_vars = {
                # Market analysis
                "market_trend": market_analysis.get("trend", "unknown"),
                "trend_strength": market_analysis.get("trend_strength", 5),
                "momentum": market_analysis.get("momentum", "neutral"),
                "risk_level": market_analysis.get("risk_level", "medium"),
                "market_phase": market_analysis.get("market_phase", "distribution"),
                # Portfolio
                "btc_balance": f"{portfolio.btc_balance:.8f}",
                "cash_balance": f"{portfolio.cash_balance:,.2f}",
                "exposure_percentage": f"{exposure_pct:.2f}",
                "avg_entry_price": f"{avg_entry:,.2f}",
                "current_price": f"{current_price:,.2f}",
                "unrealized_pnl": f"{unrealized_pnl:+.2f}",
                # Technical signals
                "rsi_14": f"{indicators.rsi_14:.2f}",
                "macd_histogram": f"{macd_histogram:.4f}",
                "macd_signal_status": macd_signal,
                "price_vs_sma": f"{price_vs_sma:+.2f}",
                "bollinger_position": bollinger_position,
                # Performance
                "performance_7d": f"{perf.get('performance_7d', 0.0):+.2f}",
                "performance_30d": f"{perf.get('performance_30d', 0.0):+.2f}",
                "win_rate": f"{perf.get('win_rate', 50.0):.1f}",
                # Historical patterns
                "historical_patterns": historical_patterns or "No historical data available",
                # System parameters
                "dca_threshold": f"{self.settings.DCA_THRESHOLD:.2f}",
            }

            # Load and format prompt
            prompt = self.load_prompt("strategy_decision.txt", **prompt_vars)

            # Generate strategy decision
            decision = self.generate_json(prompt, max_tokens=700)

            # Validate response structure
            required_keys = [
                "strategy",
                "action",
                "confidence",
                "position_size_pct",
                "entry_price_target",
                "exit_price_target",
                "holding_period",
                "reasoning",
                "key_factors",
                "invalidation_price",
            ]

            for key in required_keys:
                if key not in decision:
                    logger.warning(f"Missing key in decision: {key}")
                    decision[key] = self._get_default_value(key)

            # Validate strategy and action
            decision = self._validate_decision(decision)

            # Log result
            logger.info(
                f"[OK] StrategyAgent: {decision['strategy']} strategy, "
                f"action={decision['action']}, "
                f"confidence={decision.get('confidence', 0)}%"
            )

            return decision

        except Exception as e:
            logger.error(f"[FAIL] StrategyAgent execution failed: {e}")
            raise AgentError(f"Strategy determination failed: {e}")

    def _validate_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize strategy decision.

        Args:
            decision: Original decision dict

        Returns:
            Dict: Validated decision
        """
        # Validate strategy
        valid_strategies = ["DCA", "SWING", "DAY", "HOLD"]
        if decision.get("strategy", "").upper() not in valid_strategies:
            logger.warning(f"Invalid strategy: {decision.get('strategy')}, defaulting to HOLD")
            decision["strategy"] = "HOLD"

        # Validate action
        valid_actions = ["BUY", "SELL", "HOLD"]
        if decision.get("action", "").upper() not in valid_actions:
            logger.warning(f"Invalid action: {decision.get('action')}, defaulting to HOLD")
            decision["action"] = "HOLD"

        # If action is HOLD, ensure position size is 0
        if decision["action"].upper() == "HOLD":
            decision["position_size_pct"] = 0.0

        # Ensure position size is within bounds
        if decision["position_size_pct"] < 0:
            decision["position_size_pct"] = 0.0
        elif decision["position_size_pct"] > 100:
            decision["position_size_pct"] = 100.0

        # Ensure confidence is within bounds
        if decision.get("confidence", 0) < 0:
            decision["confidence"] = 0
        elif decision.get("confidence", 0) > 100:
            decision["confidence"] = 100

        # Ensure key_factors is a list
        if not isinstance(decision.get("key_factors"), list):
            decision["key_factors"] = []

        return decision

    def _get_default_value(self, key: str) -> Any:
        """Get default value for missing decision keys.

        Args:
            key: Missing key name

        Returns:
            Default value appropriate for the key type
        """
        defaults = {
            "strategy": "HOLD",
            "action": "HOLD",
            "confidence": 0,
            "position_size_pct": 0.0,
            "entry_price_target": 0.0,
            "exit_price_target": 0.0,
            "holding_period": "N/A",
            "reasoning": "Decision incomplete due to missing data",
            "key_factors": [],
            "invalidation_price": 0.0,
        }

        return defaults.get(key, "N/A")

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: Agent representation
        """
        return "StrategyAgent()"
