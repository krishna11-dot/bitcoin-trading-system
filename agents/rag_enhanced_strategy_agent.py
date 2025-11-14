"""RAG-Enhanced Strategy Agent.

This enhanced strategy agent uses RAG (Retrieval-Augmented Generation) to make
data-driven trading decisions based on historical pattern matching.

Key enhancements:
1. Historical success rate integration
2. Risk-adjusted position sizing based on RAG confidence
3. Entry/exit targets informed by historical outcomes
4. Strategy selection backed by statistical evidence
5. Invalidation levels based on historical worst cases

Example:
    >>> from agents.rag_enhanced_strategy_agent import RAGEnhancedStrategyAgent
    >>>
    >>> agent = RAGEnhancedStrategyAgent()
    >>> decision = agent.decide(market_data, indicators, portfolio, rag_analysis)
    >>>
    >>> print(f"Action: {decision['action']}")
    >>> print(f"Confidence: {decision['confidence']:.1%}")
    >>> print(f"Expected Outcome: {decision['expected_outcome']:+.2f}%")
"""

import logging
from typing import Dict, Any, Optional

from data_models import MarketData, TechnicalIndicators, PortfolioState
from tools.csv_rag_pipeline import RAGRetriever

logger = logging.getLogger(__name__)


class RAGEnhancedStrategyAgent:
    """Strategy Agent enhanced with RAG historical pattern analysis.

    This agent makes trading decisions by combining:
    - Technical analysis (RSI, MACD, etc.)
    - Market trend analysis
    - Historical pattern matching (RAG)
    - Risk/reward assessment from historical data
    - Portfolio state and exposure

    Attributes:
        rag: Optional RAGRetriever for historical analysis
        min_confidence: Minimum confidence threshold for trading (default: 0.55)
        position_sizing_mode: "fixed"|"confidence_based" (default: "confidence_based")
    """

    def __init__(
        self,
        rag_path: Optional[str] = "data/Bitcoin_Historical_Data_Raw.csv",
        min_confidence: float = 0.55,
        position_sizing_mode: str = "confidence_based"
    ):
        """Initialize RAG-Enhanced Strategy Agent.

        Args:
            rag_path: Path to RAG historical data (None to disable RAG)
            min_confidence: Minimum confidence threshold for trading (0-1)
            position_sizing_mode: "fixed" or "confidence_based"
        """
        self.min_confidence = min_confidence
        self.position_sizing_mode = position_sizing_mode

        # Initialize RAG if path provided
        if rag_path:
            try:
                self.rag = RAGRetriever(rag_path)
                logger.info(f"RAG-Enhanced Strategy Agent initialized with RAG: {rag_path}")
            except Exception as e:
                logger.warning(f"RAG initialization failed: {e}. Operating without RAG.")
                self.rag = None
        else:
            self.rag = None
            logger.info("RAG-Enhanced Strategy Agent initialized (RAG disabled)")

    def decide(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        portfolio: PortfolioState,
        rag_analysis: Optional[Dict] = None,
        k: int = 50
    ) -> Dict[str, Any]:
        """Make trading decision with RAG enhancement.

        Args:
            market_data: Current market data
            indicators: Technical indicators
            portfolio: Current portfolio state
            rag_analysis: Pre-computed RAG analysis (optional, will query if None)
            k: Number of similar patterns to retrieve (if querying RAG)

        Returns:
            dict: Trading decision with structure:
                {
                    "action": "BUY"|"SELL"|"HOLD",
                    "confidence": float (0-1),
                    "strategy": "DCA"|"SWING"|"DAY"|"HOLD",
                    "position_size_pct": float (0-100),
                    "entry_price": float,
                    "exit_target": float,
                    "stop_loss": float,
                    "expected_outcome": float (percentage),
                    "best_case": float,
                    "worst_case": float,
                    "reasoning": str,
                    "rag_backed": bool,
                    "historical_success_rate": float
                }
        """
        logger.info("RAG-Enhanced Strategy Agent: Making trading decision")

        # Get RAG analysis if not provided
        if rag_analysis is None and self.rag is not None:
            try:
                rag_results = self.rag.query(market_data, indicators, k=k)
                rag_analysis = {
                    "rag_enabled": True,
                    "rag_success_rate": rag_results["success_rate"],
                    "rag_avg_outcome": rag_results["avg_outcome"],
                    "rag_best_outcome": rag_results["best_outcome"],
                    "rag_worst_outcome": rag_results["worst_outcome"],
                    "rag_num_wins": rag_results["num_wins"],
                    "rag_num_losses": rag_results["num_losses"],
                    "rag_context": rag_results["historical_context"]
                }
            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                rag_analysis = {"rag_enabled": False}

        # Extract RAG metrics
        rag_enabled = rag_analysis.get("rag_enabled", False)
        success_rate = rag_analysis.get("rag_success_rate", 0.5)
        avg_outcome = rag_analysis.get("rag_avg_outcome", 0.0)
        best_outcome = rag_analysis.get("rag_best_outcome", 0.0)
        worst_outcome = rag_analysis.get("rag_worst_outcome", 0.0)

        # Calculate portfolio metrics
        current_price = market_data.price
        btc_value = portfolio.btc_balance * current_price
        total_value = portfolio.usd_balance + btc_value
        exposure_pct = (btc_value / total_value * 100) if total_value > 0 else 0

        # Determine action based on RAG + technical signals
        action, confidence, reasoning = self._determine_action(
            indicators=indicators,
            success_rate=success_rate,
            avg_outcome=avg_outcome,
            exposure_pct=exposure_pct
        )

        # Calculate position size
        position_size_pct = self._calculate_position_size(
            confidence=confidence,
            success_rate=success_rate,
            exposure_pct=exposure_pct,
            action=action
        )

        # Calculate price targets
        entry_price, exit_target, stop_loss = self._calculate_targets(
            current_price=current_price,
            indicators=indicators,
            avg_outcome=avg_outcome,
            worst_outcome=worst_outcome,
            action=action
        )

        # Determine strategy
        strategy = self._determine_strategy(
            indicators=indicators,
            success_rate=success_rate,
            action=action
        )

        # Build decision
        decision = {
            "action": action,
            "confidence": confidence,
            "strategy": strategy,
            "position_size_pct": position_size_pct,
            "entry_price": entry_price,
            "exit_target": exit_target,
            "stop_loss": stop_loss,
            "expected_outcome": avg_outcome,
            "best_case": best_outcome,
            "worst_case": worst_outcome,
            "reasoning": reasoning,
            "rag_backed": rag_enabled,
            "historical_success_rate": success_rate,
            "current_price": current_price,
            "current_exposure": exposure_pct,
        }

        logger.info(
            f"Decision: {action} {position_size_pct:.1f}% @ ${entry_price:,.0f} "
            f"(confidence: {confidence:.1%}, expected: {avg_outcome:+.2f}%)"
        )

        return decision

    def _determine_action(
        self,
        indicators: TechnicalIndicators,
        success_rate: float,
        avg_outcome: float,
        exposure_pct: float
    ) -> tuple[str, float, str]:
        """Determine trading action based on signals and RAG data.

        Args:
            indicators: Technical indicators
            success_rate: Historical success rate from RAG
            avg_outcome: Average historical outcome
            exposure_pct: Current portfolio exposure

        Returns:
            tuple: (action, confidence, reasoning)
        """
        signals = []
        confidence_factors = []

        # RSI signals
        if indicators.rsi_14 < 30:
            signals.append("BUY")
            confidence_factors.append(0.7)
        elif indicators.rsi_14 > 70:
            signals.append("SELL")
            confidence_factors.append(0.7)

        # MACD signals
        if indicators.macd_histogram > 0:
            signals.append("BUY")
            confidence_factors.append(0.6)
        elif indicators.macd_histogram < 0:
            signals.append("SELL")
            confidence_factors.append(0.6)

        # RAG success rate signal (strong weight)
        if success_rate >= 0.65 and avg_outcome > 2.0:
            signals.append("BUY")
            confidence_factors.append(success_rate)
        elif success_rate < 0.45 or avg_outcome < -1.0:
            signals.append("SELL")
            confidence_factors.append(1 - success_rate)

        # Determine majority action
        buy_votes = signals.count("BUY")
        sell_votes = signals.count("SELL")

        if buy_votes > sell_votes and exposure_pct < 80:
            action = "BUY"
            reasoning = f"Bullish signals (RSI: {indicators.rsi_14:.0f}, MACD: {indicators.macd_histogram:+.1f}) + {success_rate:.1%} historical success rate"
        elif sell_votes > buy_votes and exposure_pct > 20:
            action = "SELL"
            reasoning = f"Bearish signals (RSI: {indicators.rsi_14:.0f}, MACD: {indicators.macd_histogram:+.1f}) + {success_rate:.1%} historical success rate"
        else:
            action = "HOLD"
            reasoning = f"Mixed signals or portfolio constraints (exposure: {exposure_pct:.1f}%)"

        # Calculate confidence
        if confidence_factors:
            confidence = sum(confidence_factors) / len(confidence_factors)
        else:
            confidence = 0.5

        # Apply minimum confidence threshold
        if confidence < self.min_confidence and action != "HOLD":
            action = "HOLD"
            reasoning += f" (Below min confidence threshold {self.min_confidence:.1%})"

        return action, confidence, reasoning

    def _calculate_position_size(
        self,
        confidence: float,
        success_rate: float,
        exposure_pct: float,
        action: str
    ) -> float:
        """Calculate position size based on confidence and risk.

        Args:
            confidence: Trading confidence (0-1)
            success_rate: Historical success rate (0-1)
            exposure_pct: Current portfolio exposure
            action: Trading action (BUY/SELL/HOLD)

        Returns:
            float: Position size as percentage (0-100)
        """
        if action == "HOLD":
            return 0.0

        if self.position_sizing_mode == "fixed":
            return 25.0  # Fixed 25% position size

        # Confidence-based sizing
        # Base: 10-40% depending on combined confidence
        combined_confidence = (confidence + success_rate) / 2
        base_size = 10 + (combined_confidence * 30)  # 10-40%

        # Adjust for exposure
        if action == "BUY":
            # Reduce size if already heavily exposed
            if exposure_pct > 70:
                base_size *= 0.5
            elif exposure_pct > 50:
                base_size *= 0.75
        elif action == "SELL":
            # Reduce size if not much to sell
            if exposure_pct < 30:
                base_size *= 0.5
            elif exposure_pct < 50:
                base_size *= 0.75

        return min(base_size, 40.0)  # Cap at 40%

    def _calculate_targets(
        self,
        current_price: float,
        indicators: TechnicalIndicators,
        avg_outcome: float,
        worst_outcome: float,
        action: str
    ) -> tuple[float, float, float]:
        """Calculate entry, exit, and stop-loss targets.

        Args:
            current_price: Current BTC price
            indicators: Technical indicators
            avg_outcome: Average historical outcome
            worst_outcome: Worst historical outcome
            action: Trading action

        Returns:
            tuple: (entry_price, exit_target, stop_loss)
        """
        if action == "HOLD":
            return current_price, current_price, current_price

        # Entry: Use current price (market order)
        entry_price = current_price

        # Exit target: Based on average historical outcome
        if avg_outcome > 0:
            exit_target = entry_price * (1 + avg_outcome / 100)
        else:
            exit_target = entry_price * 1.03  # Default 3% target

        # Stop loss: Based on worst historical outcome (with buffer)
        if worst_outcome < 0:
            stop_loss = entry_price * (1 + (worst_outcome * 0.8) / 100)  # 80% of worst case
        else:
            stop_loss = entry_price * 0.97  # Default 3% stop

        # Ensure stop loss is reasonable
        if action == "BUY":
            stop_loss = max(stop_loss, entry_price * 0.95)  # Max 5% stop for buys
        elif action == "SELL":
            stop_loss = min(stop_loss, entry_price * 1.05)  # Max 5% stop for sells

        return entry_price, exit_target, stop_loss

    def _determine_strategy(
        self,
        indicators: TechnicalIndicators,
        success_rate: float,
        action: str
    ) -> str:
        """Determine trading strategy based on conditions.

        Args:
            indicators: Technical indicators
            success_rate: Historical success rate
            action: Trading action

        Returns:
            str: Strategy name (DCA|SWING|DAY|HOLD)
        """
        if action == "HOLD":
            return "HOLD"

        # High confidence + strong trends = Swing
        if success_rate >= 0.65 and abs(indicators.macd_histogram) > 100:
            return "SWING"

        # Medium confidence + moderate volatility = DCA
        if success_rate >= 0.55 and indicators.atr_14 > 800:
            return "DCA"

        # Low volatility + mixed signals = Day trading
        if indicators.atr_14 < 500:
            return "DAY"

        # Default
        return "DCA"


# For testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 80)
    print("RAG-Enhanced Strategy Agent - Test")
    print("=" * 80)

    # Sample data
    market_data = MarketData(
        price=65000.0,
        volume=1200000.0,
        timestamp="2025-01-15T12:00:00Z",
        change_24h=3.5,
        high_24h=66000.0,
        low_24h=64000.0
    )

    indicators = TechnicalIndicators(
        rsi_14=72.0,
        macd=250.0,
        macd_signal=230.0,
        macd_histogram=20.0,
        atr_14=1200.0,
        sma_50=63000.0,
        ema_12=64500.0,
        ema_26=63500.0
    )

    portfolio = PortfolioState(
        usd_balance=10000.0,
        btc_balance=0.1,
        last_updated="2025-01-15T12:00:00Z"
    )

    print(f"\nMarket: ${market_data.price:,.0f}, RSI: {indicators.rsi_14:.0f}")
    print(f"Portfolio: ${portfolio.usd_balance:,.0f} cash, {portfolio.btc_balance:.4f} BTC")

    # Test strategy agent
    agent = RAGEnhancedStrategyAgent(min_confidence=0.55)
    decision = agent.decide(market_data, indicators, portfolio, k=50)

    print(f"\nDecision:")
    print(f"  Action: {decision['action']}")
    print(f"  Strategy: {decision['strategy']}")
    print(f"  Confidence: {decision['confidence']:.1%}")
    print(f"  Position Size: {decision['position_size_pct']:.1f}%")
    print(f"  Entry: ${decision['entry_price']:,.0f}")
    print(f"  Target: ${decision['exit_target']:,.0f} ({decision['expected_outcome']:+.2f}%)")
    print(f"  Stop Loss: ${decision['stop_loss']:,.0f}")
    print(f"  Historical Success: {decision['historical_success_rate']:.1%}")
    print(f"  RAG-Backed: {decision['rag_backed']}")
    print(f"\n  Reasoning: {decision['reasoning']}")

    print(f"\n{'=' * 80}")
