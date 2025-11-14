"""Risk Manager Agent.

This agent evaluates trade proposals, calculates position sizes, sets stop losses,
and ensures risk parameters are within acceptable limits.

Example:
    >>> from agents.risk_manager import RiskManagerAgent
    >>> from data_models import PortfolioState, TradeDecision
    >>>
    >>> agent = RiskManagerAgent()
    >>> risk_assessment = agent.execute(portfolio, proposed_trade, market_analysis)
    >>> if risk_assessment["approved"]:
    ...     print(f"Position size: {risk_assessment['recommended_position_size']}%")
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentError
from data_models import PortfolioState, MarketData
from config import Settings


logger = logging.getLogger(__name__)


class RiskManagerAgent(BaseAgent):
    """Agent responsible for risk assessment and position sizing.

    This agent:
    - Evaluates proposed trades against risk parameters
    - Calculates appropriate position sizes based on volatility
    - Sets stop loss and take profit levels
    - Validates portfolio exposure limits
    - Calculates risk-reward ratios

    Attributes:
        agent_name: "RiskManager"
        settings: System settings with risk parameters
    """

    def __init__(self):
        """Initialize Risk Manager Agent."""
        super().__init__(agent_name="RiskManager")
        self.settings = Settings.get_instance()

    def execute(
        self,
        portfolio: PortfolioState,
        proposed_action: str,
        proposed_entry_price: float,
        suggested_position_size: float,
        market_data: MarketData,
        market_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess risk and validate trade proposal.

        Args:
            portfolio: Current portfolio state
            proposed_action: "BUY" or "SELL"
            proposed_entry_price: Proposed entry price
            suggested_position_size: Suggested position size (% of portfolio)
            market_data: Current market data
            market_analysis: Analysis from MarketAnalyst agent

        Returns:
            Dict containing:
                - approved: bool
                - recommended_position_size: 0.0-100.0
                - stop_loss_price: float
                - take_profit_price: float
                - risk_reward_ratio: float
                - max_loss_usd: float
                - risk_score: 1-10
                - warnings: List[str]
                - reasoning: str

        Raises:
            AgentError: If risk assessment fails
        """
        logger.info(
            f" RiskManager: Assessing {proposed_action} at "
            f"${proposed_entry_price:,.2f} ({suggested_position_size}%)"
        )

        try:
            # Calculate current exposure
            btc_value = portfolio.btc_balance * market_data.price
            total_value = portfolio.cash_balance + btc_value
            current_exposure = (btc_value / total_value * 100) if total_value > 0 else 0

            # Calculate exposure after trade
            exposure_after = self._calculate_exposure_after_trade(
                portfolio=portfolio,
                action=proposed_action,
                entry_price=proposed_entry_price,
                position_size_pct=suggested_position_size,
            )

            # Prepare prompt variables
            prompt_vars = {
                # Portfolio
                "total_balance": f"{total_value:,.2f}",
                "btc_balance": f"{portfolio.btc_balance:.8f}",
                "btc_value_usd": f"{btc_value:,.2f}",
                "cash_balance": f"{portfolio.cash_balance:,.2f}",
                "open_positions": len(portfolio.open_positions),
                "exposure_percentage": f"{current_exposure:.2f}",
                # Market
                "current_price": f"{market_data.price:,.2f}",
                "atr_14": f"{market_analysis.get('atr_14', 0):.2f}",
                "market_trend": market_analysis.get("trend", "unknown"),
                "market_risk_level": market_analysis.get("risk_level", "medium"),
                # Proposed trade
                "proposed_action": proposed_action,
                "proposed_entry_price": f"{proposed_entry_price:,.2f}",
                "suggested_position_size": f"{suggested_position_size:.2f}",
                # System parameters
                "max_position_size": f"{self.settings.MAX_POSITION_SIZE * 100:.2f}",
                "emergency_stop_loss": f"{self.settings.EMERGENCY_STOP_LOSS * 100:.2f}",
                "dca_threshold": f"{self.settings.DCA_THRESHOLD:.2f}",
            }

            # Load and format prompt
            prompt = self.load_prompt("risk_assessment.txt", **prompt_vars)

            # Generate risk assessment
            assessment = self.generate_json(prompt, max_tokens=600)

            # Validate response structure
            required_keys = [
                "approved",
                "recommended_position_size",
                "stop_loss_price",
                "take_profit_price",
                "risk_reward_ratio",
                "max_loss_usd",
                "risk_score",
                "reasoning",
            ]

            for key in required_keys:
                if key not in assessment:
                    logger.warning(f"Missing key in assessment: {key}")
                    assessment[key] = self._get_default_value(key)

            # Apply safety constraints
            assessment = self._apply_safety_constraints(assessment, portfolio, market_data)

            # Log result
            if assessment["approved"]:
                logger.info(
                    f"[OK] RiskManager: APPROVED {proposed_action} at "
                    f"{assessment['recommended_position_size']:.2f}% "
                    f"(risk score: {assessment.get('risk_score', 0)}/10)"
                )
            else:
                logger.warning(
                    f" RiskManager: REJECTED {proposed_action} - "
                    f"{assessment.get('reasoning', 'Unknown reason')}"
                )

            return assessment

        except Exception as e:
            logger.error(f"[FAIL] RiskManager execution failed: {e}")
            raise AgentError(f"Risk assessment failed: {e}")

    def _calculate_exposure_after_trade(
        self,
        portfolio: PortfolioState,
        action: str,
        entry_price: float,
        position_size_pct: float,
    ) -> float:
        """Calculate portfolio exposure after proposed trade.

        Args:
            portfolio: Current portfolio state
            action: "BUY" or "SELL"
            entry_price: Trade entry price
            position_size_pct: Position size as % of portfolio

        Returns:
            float: Exposure percentage after trade
        """
        btc_value = portfolio.btc_balance * entry_price
        total_value = portfolio.cash_balance + btc_value

        if action == "BUY":
            trade_amount = total_value * (position_size_pct / 100)
            new_btc_value = btc_value + trade_amount
        elif action == "SELL":
            trade_amount = btc_value * (position_size_pct / 100)
            new_btc_value = btc_value - trade_amount
        else:
            return 0.0

        exposure = (new_btc_value / total_value * 100) if total_value > 0 else 0
        return exposure

    def _apply_safety_constraints(
        self, assessment: Dict[str, Any], portfolio: PortfolioState, market_data: MarketData
    ) -> Dict[str, Any]:
        """Apply hard safety constraints to risk assessment.

        Args:
            assessment: Original risk assessment
            portfolio: Current portfolio
            market_data: Current market data

        Returns:
            Dict: Constrained risk assessment
        """
        # Ensure position size doesn't exceed maximum
        max_position_pct = self.settings.MAX_POSITION_SIZE * 100
        if assessment["recommended_position_size"] > max_position_pct:
            logger.warning(
                f"Constraining position size from {assessment['recommended_position_size']:.2f}% "
                f"to {max_position_pct:.2f}%"
            )
            assessment["recommended_position_size"] = max_position_pct
            if "warnings" not in assessment:
                assessment["warnings"] = []
            assessment["warnings"].append(
                f"Position size reduced to maximum allowed: {max_position_pct}%"
            )

        # Ensure sufficient cash for BUY orders
        btc_value = portfolio.btc_balance * market_data.price
        total_value = portfolio.cash_balance + btc_value
        required_cash = total_value * (assessment["recommended_position_size"] / 100)

        if required_cash > portfolio.cash_balance:
            logger.warning(f"Insufficient cash: ${portfolio.cash_balance:,.2f} < ${required_cash:,.2f}")
            assessment["approved"] = False
            assessment["recommended_position_size"] = 0.0
            if "warnings" not in assessment:
                assessment["warnings"] = []
            assessment["warnings"].append("Insufficient cash balance for this trade")

        # Validate stop loss is set
        if assessment["approved"] and assessment["stop_loss_price"] <= 0:
            logger.warning("Stop loss not set, rejecting trade")
            assessment["approved"] = False
            assessment["recommended_position_size"] = 0.0
            if "warnings" not in assessment:
                assessment["warnings"] = []
            assessment["warnings"].append("Stop loss must be set for all trades")

        return assessment

    def _get_default_value(self, key: str) -> Any:
        """Get default value for missing assessment keys.

        Args:
            key: Missing key name

        Returns:
            Default value appropriate for the key type
        """
        defaults = {
            "approved": False,
            "recommended_position_size": 0.0,
            "stop_loss_price": 0.0,
            "take_profit_price": 0.0,
            "risk_reward_ratio": 0.0,
            "max_loss_usd": 0.0,
            "risk_score": 10,
            "warnings": [],
            "reasoning": "Assessment incomplete due to missing data",
        }

        return defaults.get(key, None)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: Agent representation
        """
        return "RiskManagerAgent()"
