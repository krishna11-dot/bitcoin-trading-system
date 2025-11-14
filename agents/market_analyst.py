"""Market Analyst Agent.

This agent analyzes market data, technical indicators, and sentiment to provide
comprehensive market analysis and trend identification.

Example:
    >>> from agents.market_analyst import MarketAnalystAgent
    >>> from data_models import MarketData, TechnicalIndicators, SentimentData
    >>>
    >>> agent = MarketAnalystAgent()
    >>> analysis = agent.execute(market_data, indicators, sentiment)
    >>> print(analysis["trend"], analysis["confidence"])
"""

import logging
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentError
from data_models import MarketData, TechnicalIndicators, SentimentData
from tools import RAGRetriever


logger = logging.getLogger(__name__)


class MarketAnalystAgent(BaseAgent):
    """Agent responsible for analyzing market conditions and trends.

    This agent:
    - Analyzes price action and technical indicators
    - Identifies trends and momentum
    - Determines support/resistance levels
    - Assesses market phase and risk
    - Incorporates historical pattern matching via RAG

    Attributes:
        agent_name: "MarketAnalyst"
        rag_retriever: Optional RAG system for historical patterns
    """

    def __init__(self, rag_csv_path: Optional[str] = None):
        """Initialize Market Analyst Agent.

        Args:
            rag_csv_path: Optional path to historical data CSV for RAG
        """
        super().__init__(agent_name="MarketAnalyst")

        # Initialize RAG if path provided
        self.rag_retriever = None
        if rag_csv_path:
            try:
                self.rag_retriever = RAGRetriever(rag_csv_path)
                logger.info("[OK] RAG system initialized for historical pattern matching")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG system: {e}")

    def execute(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        sentiment: Optional[SentimentData] = None,
    ) -> Dict[str, Any]:
        """Analyze market conditions and provide comprehensive assessment.

        Args:
            market_data: Current market data (price, volume, etc.)
            indicators: Technical indicators (RSI, MACD, etc.)
            sentiment: Optional sentiment data (fear/greed, dominance, etc.)

        Returns:
            Dict containing:
                - trend: bullish|bearish|sideways
                - trend_strength: 1-10
                - momentum: increasing|decreasing|neutral
                - key_support: float
                - key_resistance: float
                - market_phase: accumulation|markup|distribution|markdown
                - risk_level: low|medium|high|extreme
                - confidence: 0-100
                - reasoning: str
                - warnings: List[str]

        Raises:
            AgentError: If analysis fails
        """
        logger.info(f"[ANALYZING] MarketAnalyst: Analyzing market at ${market_data.price}")

        try:
            # Get historical context from RAG if available
            historical_context = self._get_historical_context(market_data, indicators)

            # Prepare prompt variables
            prompt_vars = {
                # Market data
                "price": f"{market_data.price:,.2f}",
                "change_24h": f"{market_data.change_24h:+.2f}",
                "high_24h": f"{market_data.high_24h or 0:,.2f}",
                "low_24h": f"{market_data.low_24h or 0:,.2f}",
                "volume": f"{market_data.volume:,.2f}",
                # Technical indicators
                "rsi_14": f"{indicators.rsi_14:.2f}",
                "macd": f"{indicators.macd:.4f}",
                "macd_signal": f"{indicators.macd_signal:.4f}",
                "macd_histogram": f"{indicators.macd_histogram:.4f}",
                "atr_14": f"{indicators.atr_14:.2f}",
                "sma_50": f"{indicators.sma_50:,.2f}",
                "ema_12": f"{indicators.ema_12:,.2f}",
                "ema_26": f"{indicators.ema_26:,.2f}",
                "bollinger_upper": f"{indicators.bollinger_upper or 0:,.2f}",
                "bollinger_lower": f"{indicators.bollinger_lower or 0:,.2f}",
                # Sentiment data
                "fear_greed_index": sentiment.fear_greed_index if sentiment else "N/A",
                "market_cap_rank": sentiment.market_cap_rank if sentiment else "N/A",
                "dominance": f"{sentiment.dominance:.2f}" if sentiment else "N/A",
                # Historical context
                "historical_context": historical_context,
            }

            # Load and format prompt
            prompt = self.load_prompt("market_analysis.txt", **prompt_vars)

            # Generate analysis
            analysis = self.generate_json(prompt, max_tokens=600)

            # Validate response structure
            required_keys = [
                "trend",
                "trend_strength",
                "momentum",
                "key_support",
                "key_resistance",
                "market_phase",
                "risk_level",
                "confidence",
                "reasoning",
            ]

            for key in required_keys:
                if key not in analysis:
                    logger.warning(f"Missing key in analysis: {key}")
                    analysis[key] = self._get_default_value(key)

            logger.info(
                f"[OK] MarketAnalyst: {analysis['trend'].upper()} trend "
                f"(confidence: {analysis.get('confidence', 0)}%)"
            )

            return analysis

        except Exception as e:
            logger.error(f"[FAIL] MarketAnalyst execution failed: {e}")
            raise AgentError(f"Market analysis failed: {e}")

    def _get_historical_context(
        self, market_data: MarketData, indicators: TechnicalIndicators
    ) -> str:
        """Get historical context from RAG system if available.

        Args:
            market_data: Current market data
            indicators: Current technical indicators

        Returns:
            str: Historical context or placeholder message
        """
        if not self.rag_retriever:
            return "No historical data available."

        try:
            rag_results = self.rag_retriever.query(market_data, indicators, k=50)

            context = (
                f"Historical Analysis (based on {rag_results['similar_patterns']} similar patterns):\n"
                f"- Success Rate: {rag_results['success_rate']:.1f}%\n"
                f"- Average Outcome: {rag_results['avg_outcome']:+.2f}%\n"
                f"- Context: {rag_results['historical_context']}"
            )

            logger.debug(f"[DATA] RAG context: {rag_results['similar_patterns']} patterns found")
            return context

        except Exception as e:
            logger.warning(f"Failed to get historical context: {e}")
            return "Historical data unavailable due to error."

    def _get_default_value(self, key: str) -> Any:
        """Get default value for missing analysis keys.

        Args:
            key: Missing key name

        Returns:
            Default value appropriate for the key type
        """
        defaults = {
            "trend": "sideways",
            "trend_strength": 5,
            "momentum": "neutral",
            "key_support": 0.0,
            "key_resistance": 0.0,
            "market_phase": "distribution",
            "risk_level": "medium",
            "confidence": 50,
            "reasoning": "Analysis incomplete due to missing data",
            "warnings": [],
        }

        return defaults.get(key, "N/A")

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: Agent representation
        """
        rag_status = "with RAG" if self.rag_retriever else "without RAG"
        return f"MarketAnalystAgent({rag_status})"
