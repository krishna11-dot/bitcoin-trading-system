"""RAG-Enhanced Market Analysis Agent.

This enhanced version integrates the RAG (Retrieval-Augmented Generation) pipeline
to provide data-driven market analysis backed by historical pattern matching.

Key enhancements over standard MarketAnalysisAgent:
1. Historical pattern matching - finds similar past market conditions
2. Statistical confidence - success rates from similar patterns
3. Risk quantification - best/worst case scenarios from history
4. Expected outcomes - average profit/loss from similar situations
5. Trading insights - data-driven recommendations

Example:
    >>> from agents.rag_enhanced_market_analyst import RAGEnhancedMarketAnalyst
    >>> from data_models import MarketData, TechnicalIndicators
    >>>
    >>> analyst = RAGEnhancedMarketAnalyst()
    >>> result = analyst.analyze(market_data, indicators)
    >>>
    >>> print(f"Trend: {result['trend']}")
    >>> print(f"RAG Success Rate: {result['rag_success_rate']:.1%}")
    >>> print(f"Expected Outcome: {result['rag_avg_outcome']:+.2f}%")
"""

import logging
from pathlib import Path
from typing import Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.market_analysis_agent import (
    analyze_market as standard_analyze,
    _parse_and_validate_response,
    _get_default_response,
    load_prompt
)
from config.settings import Settings
from data_models import MarketData, TechnicalIndicators
from tools.csv_rag_pipeline import RAGRetriever
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

logger = logging.getLogger(__name__)


class RAGEnhancedMarketAnalyst:
    """Market Analysis Agent enhanced with RAG historical pattern matching.

    This agent combines LLM-based market analysis with historical pattern
    matching to provide data-driven insights. It finds similar past market
    conditions and uses their outcomes to enhance decision-making.

    Attributes:
        rag: RAGRetriever instance for historical pattern matching
        settings: System configuration settings
        rag_enabled: Whether RAG analysis is enabled

    Example:
        >>> analyst = RAGEnhancedMarketAnalyst(rag_path="data/Bitcoin_Historical_Data_Raw.csv")
        >>> result = analyst.analyze(market_data, indicators, k=50)
        >>> if result['rag_success_rate'] > 0.65:
        ...     print("High confidence trade based on historical data!")
    """

    def __init__(
        self,
        rag_path: str = "data/Bitcoin_Historical_Data_Raw.csv",
        enable_rag: bool = True,
        enable_onchain: bool = True
    ):
        """Initialize RAG-Enhanced Market Analyst.

        Args:
            rag_path: Path to historical data CSV for RAG
            enable_rag: Whether to enable RAG analysis (can disable for fallback)
            enable_onchain: Whether to enable on-chain analysis (default: True)
        """
        self.settings = Settings.get_instance()
        self.rag_enabled = enable_rag
        self.onchain_enabled = enable_onchain

        # Initialize RAG retriever
        if self.rag_enabled:
            try:
                self.rag = RAGRetriever(rag_path)
                logger.info(f"RAG-Enhanced Market Analyst initialized with RAG: {rag_path}")
            except Exception as e:
                logger.warning(f"RAG initialization failed: {e}. Falling back to standard analysis.")
                self.rag_enabled = False
                self.rag = None
        else:
            self.rag = None
            logger.info("RAG-Enhanced Market Analyst initialized (RAG disabled)")

        # Initialize On-Chain Analyzer
        if self.onchain_enabled:
            try:
                self.onchain = BitcoinOnChainAnalyzer(cache_duration=300)  # 5-minute cache
                logger.info("On-chain analyzer initialized (Blockchain.com API)")
            except Exception as e:
                logger.warning(f"On-chain analyzer initialization failed: {e}")
                self.onchain_enabled = False
                self.onchain = None
        else:
            self.onchain = None
            logger.info("On-chain analysis disabled")

    def analyze(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        k: int = 50,
        include_standard_analysis: bool = True
    ) -> Dict[str, Any]:
        """Analyze market with RAG-enhanced insights.

        This method:
        1. Queries RAG for similar historical patterns
        2. Calculates statistical confidence from historical data
        3. Optionally includes standard LLM analysis
        4. Combines both for comprehensive market assessment

        Args:
            market_data: Current market data (price, volume, etc.)
            indicators: Technical indicators (RSI, MACD, ATR, etc.)
            k: Number of similar patterns to retrieve (default: 50)
            include_standard_analysis: Whether to include LLM analysis

        Returns:
            dict: Enhanced market analysis with structure:
                {
                    # Standard fields (if include_standard_analysis=True)
                    "trend": "bullish"|"bearish"|"neutral",
                    "confidence": 0.0-1.0,
                    "reasoning": str,
                    "risk_level": "low"|"medium"|"high",

                    # RAG-enhanced fields
                    "rag_enabled": bool,
                    "rag_similar_patterns": int,
                    "rag_success_rate": float (0-1),
                    "rag_avg_outcome": float (percentage),
                    "rag_median_outcome": float,
                    "rag_best_outcome": float,
                    "rag_worst_outcome": float,
                    "rag_num_wins": int,
                    "rag_num_losses": int,
                    "rag_confidence": "high"|"medium"|"low",
                    "rag_recommendation": str,
                    "rag_context": str,

                    # Combined analysis
                    "combined_confidence": float,
                    "data_driven_insight": str
                }

        Example:
            >>> result = analyst.analyze(market_data, indicators, k=50)
            >>> if result['rag_success_rate'] >= 0.65:
            ...     print(f"High confidence: {result['rag_context']}")
            >>> else:
            ...     print("Proceed with caution")
        """
        logger.info(f"Starting RAG-enhanced market analysis (k={k})")

        result = {}

        # Step 1: Get RAG insights if enabled
        if self.rag_enabled and self.rag is not None:
            try:
                rag_results = self.rag.query(market_data, indicators, k=k)

                # Add RAG insights to result
                result.update({
                    "rag_enabled": True,
                    "rag_similar_patterns": rag_results["similar_patterns"],
                    "rag_success_rate": rag_results["success_rate"],
                    "rag_avg_outcome": rag_results["avg_outcome"],
                    "rag_median_outcome": rag_results["median_outcome"],
                    "rag_best_outcome": rag_results["best_outcome"],
                    "rag_worst_outcome": rag_results["worst_outcome"],
                    "rag_num_wins": rag_results["num_wins"],
                    "rag_num_losses": rag_results["num_losses"],
                    "rag_context": rag_results["historical_context"],
                })

                # Determine RAG confidence level
                if rag_results["success_rate"] >= 0.65:
                    result["rag_confidence"] = "high"
                    result["rag_recommendation"] = "Favorable conditions for trading"
                elif rag_results["success_rate"] >= 0.50:
                    result["rag_confidence"] = "medium"
                    result["rag_recommendation"] = "Proceed with caution"
                else:
                    result["rag_confidence"] = "low"
                    result["rag_recommendation"] = "Unfavorable conditions, consider holding"

                logger.info(
                    f"RAG Analysis: {result['rag_success_rate']:.1%} success rate "
                    f"({result['rag_num_wins']}/{result['rag_similar_patterns']} wins), "
                    f"avg outcome: {result['rag_avg_outcome']:+.2f}%"
                )

            except Exception as e:
                logger.error(f"RAG query failed: {e}")
                result.update({
                    "rag_enabled": False,
                    "rag_error": str(e),
                    "rag_success_rate": 0.5,  # Neutral
                    "rag_confidence": "unknown"
                })
        else:
            result.update({
                "rag_enabled": False,
                "rag_success_rate": 0.5,  # Neutral when RAG disabled
                "rag_confidence": "unknown"
            })

        # Step 2: Get on-chain metrics if enabled
        if self.onchain_enabled and self.onchain is not None:
            try:
                onchain_metrics = self.onchain.get_comprehensive_metrics()
                summary = onchain_metrics.get('summary', {})

                # Add on-chain insights to result
                result.update({
                    "onchain_enabled": True,
                    "onchain_hash_rate_ehs": summary.get('hash_rate_ehs', 0),
                    "onchain_block_trend": summary.get('block_size_trend', 'unknown'),
                    "onchain_mempool_congestion": summary.get('mempool_congestion', 'Unknown'),
                    "onchain_network_health": summary.get('network_health', 'Unknown'),
                    "onchain_mempool_tx_count": summary.get('mempool_tx_count', 0),
                    "onchain_block_size_mb": summary.get('block_size_mb', 0),
                })

                # Determine on-chain signal
                health = summary.get('network_health', 'Unknown')
                congestion = summary.get('mempool_congestion', 'Unknown')
                hash_rate = summary.get('hash_rate_ehs', 0)

                if health in ['Excellent', 'Good'] and congestion == 'Low':
                    result["onchain_signal"] = "bullish"
                    result["onchain_recommendation"] = "Network conditions favorable"
                elif health == 'Poor' or congestion in ['High', 'Critical']:
                    result["onchain_signal"] = "bearish"
                    result["onchain_recommendation"] = "Network stress detected - caution advised"
                else:
                    result["onchain_signal"] = "neutral"
                    result["onchain_recommendation"] = "Network conditions acceptable"

                # Hash rate momentum
                if hash_rate > 500:
                    result["onchain_hash_momentum"] = "strong"
                elif hash_rate < 350:
                    result["onchain_hash_momentum"] = "weak"
                else:
                    result["onchain_hash_momentum"] = "normal"

                logger.info(
                    f"On-Chain Analysis: {health} health, {congestion} congestion, "
                    f"{hash_rate:.0f} EH/s hash rate"
                )

            except Exception as e:
                logger.error(f"On-chain analysis failed: {e}")
                result.update({
                    "onchain_enabled": False,
                    "onchain_error": str(e),
                    "onchain_signal": "neutral"
                })
        else:
            result.update({
                "onchain_enabled": False,
                "onchain_signal": "neutral"
            })

        # Step 3: Include standard LLM analysis if requested
        if include_standard_analysis:
            try:
                standard_result = standard_analyze(market_data, indicators)
                result.update(standard_result)

                logger.info(
                    f"Standard Analysis: {result['trend']} "
                    f"(confidence: {result['confidence']:.2f})"
                )

            except Exception as e:
                logger.error(f"Standard analysis failed: {e}")
                result.update(_get_default_response(str(e)))

        # Step 4: Create combined analysis (RAG + On-Chain + LLM)
        result["combined_confidence"] = self._calculate_combined_confidence(result)
        result["data_driven_insight"] = self._generate_insight(result, market_data, indicators)

        logger.info(
            f"Combined Analysis Complete: {result.get('trend', 'unknown')} trend, "
            f"combined confidence: {result['combined_confidence']:.2f}"
        )

        return result

    def _calculate_combined_confidence(self, result: Dict) -> float:
        """Calculate combined confidence from RAG, on-chain, and standard analysis.

        Weights (when all enabled):
        - RAG success rate: 50%
        - On-chain signal: 20%
        - Standard LLM confidence: 30%

        Args:
            result: Analysis results with RAG, on-chain, and standard fields

        Returns:
            float: Combined confidence (0-1)
        """
        rag_enabled = result.get("rag_enabled", False)
        onchain_enabled = result.get("onchain_enabled", False)

        if rag_enabled and onchain_enabled:
            # All three sources available
            rag_weight = 0.5
            onchain_weight = 0.2
            standard_weight = 0.3

            rag_confidence = result.get("rag_success_rate", 0.5)
            standard_confidence = result.get("confidence", 0.5)

            # Convert on-chain signal to confidence score
            onchain_signal = result.get("onchain_signal", "neutral")
            if onchain_signal == "bullish":
                onchain_confidence = 0.75
            elif onchain_signal == "bearish":
                onchain_confidence = 0.25
            else:
                onchain_confidence = 0.5

            combined = (
                (rag_confidence * rag_weight) +
                (onchain_confidence * onchain_weight) +
                (standard_confidence * standard_weight)
            )

        elif rag_enabled:
            # RAG + Standard only
            rag_weight = 0.6
            standard_weight = 0.4

            rag_confidence = result.get("rag_success_rate", 0.5)
            standard_confidence = result.get("confidence", 0.5)

            combined = (rag_confidence * rag_weight) + (standard_confidence * standard_weight)

        else:
            # Fall back to standard confidence if RAG disabled
            combined = result.get("confidence", 0.5)

        return combined

    def _generate_insight(
        self,
        result: Dict,
        market_data: MarketData,
        indicators: TechnicalIndicators
    ) -> str:
        """Generate human-readable data-driven insight.

        Args:
            result: Analysis results
            market_data: Current market data
            indicators: Technical indicators

        Returns:
            str: Comprehensive insight message
        """
        insights = []

        # Add RAG insights
        if result.get("rag_enabled"):
            rag_conf = result.get("rag_confidence", "unknown")
            success_rate = result.get("rag_success_rate", 0)
            avg_outcome = result.get("rag_avg_outcome", 0)
            wins = result.get("rag_num_wins", 0)
            losses = result.get("rag_num_losses", 0)

            insights.append(
                f"Historical Analysis: {rag_conf.upper()} confidence. "
                f"Found {wins + losses} similar patterns with {success_rate:.1%} success rate "
                f"({wins} wins, {losses} losses). "
                f"Average historical outcome: {avg_outcome:+.2f}%."
            )

            # Add best/worst case
            best = result.get("rag_best_outcome", 0)
            worst = result.get("rag_worst_outcome", 0)
            insights.append(
                f"Risk/Reward: Best case {best:+.2f}%, Worst case {worst:+.2f}%."
            )

        # Add on-chain insights
        if result.get("onchain_enabled"):
            health = result.get("onchain_network_health", "Unknown")
            congestion = result.get("onchain_mempool_congestion", "Unknown")
            hash_rate = result.get("onchain_hash_rate_ehs", 0)
            hash_momentum = result.get("onchain_hash_momentum", "normal")

            insights.append(
                f"On-Chain: {health} network health, {congestion} congestion, "
                f"{hash_rate:.0f} EH/s hash rate ({hash_momentum} momentum)."
            )

            # Add on-chain recommendation
            if result.get("onchain_recommendation"):
                insights.append(f"Network Status: {result['onchain_recommendation']}")

        # Add market context
        insights.append(
            f"Current: Price ${market_data.price:,.0f}, "
            f"RSI {indicators.rsi_14:.0f}, "
            f"MACD {indicators.macd:+.1f}."
        )

        # Add trend analysis if available
        if "trend" in result:
            trend = result["trend"]
            insights.append(
                f"Market Trend: {trend.upper()} "
                f"(LLM confidence: {result.get('confidence', 0):.1%})."
            )

        # Add recommendation
        if result.get("rag_recommendation"):
            insights.append(f"Recommendation: {result['rag_recommendation']}")

        return " ".join(insights)

    def get_rag_stats(self) -> Dict:
        """Get RAG system statistics.

        Returns:
            dict: RAG statistics or error if RAG disabled
        """
        if self.rag_enabled and self.rag is not None:
            return self.rag.get_stats()
        else:
            return {"error": "RAG not enabled"}


# Convenience function for backward compatibility
def analyze_market_with_rag(
    market_data: MarketData,
    indicators: TechnicalIndicators,
    k: int = 50,
    rag_path: str = "data/Bitcoin_Historical_Data_Raw.csv"
) -> Dict[str, Any]:
    """Analyze market with RAG enhancement (convenience function).

    Args:
        market_data: Current market data
        indicators: Technical indicators
        k: Number of similar patterns to retrieve
        rag_path: Path to historical data CSV

    Returns:
        dict: RAG-enhanced market analysis

    Example:
        >>> result = analyze_market_with_rag(market_data, indicators, k=50)
        >>> print(f"Success rate: {result['rag_success_rate']:.1%}")
    """
    analyst = RAGEnhancedMarketAnalyst(rag_path=rag_path)
    return analyst.analyze(market_data, indicators, k=k)


# For testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 80)
    print("RAG-Enhanced Market Analysis Agent - Test")
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

    print(f"\nMarket State:")
    print(f"  Price: ${market_data.price:,.0f}")
    print(f"  RSI: {indicators.rsi_14:.1f}")
    print(f"  MACD: {indicators.macd:+.1f}")

    # Test RAG-enhanced analysis
    analyst = RAGEnhancedMarketAnalyst()
    result = analyst.analyze(market_data, indicators, k=50, include_standard_analysis=False)

    print(f"\nRAG-Enhanced Analysis:")
    print(f"  Similar Patterns: {result.get('rag_similar_patterns', 0)}")
    print(f"  Success Rate: {result.get('rag_success_rate', 0):.1%}")
    print(f"  Wins/Losses: {result.get('rag_num_wins', 0)}/{result.get('rag_num_losses', 0)}")
    print(f"  Avg Outcome: {result.get('rag_avg_outcome', 0):+.2f}%")
    print(f"  Best/Worst: {result.get('rag_best_outcome', 0):+.2f}% / {result.get('rag_worst_outcome', 0):+.2f}%")
    print(f"  Confidence: {result.get('rag_confidence', 'unknown').upper()}")
    print(f"  Recommendation: {result.get('rag_recommendation', 'N/A')}")
    print(f"\n  Insight: {result.get('data_driven_insight', 'N/A')}")

    print(f"\n{'=' * 80}")
