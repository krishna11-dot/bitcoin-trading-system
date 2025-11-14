"""Adaptive Strategy Switcher with LLM Feature Engineering.

This module implements intelligent strategy switching between DCA (conservative),
Swing Trading (moderate), and Day Trading (aggressive) based on engineered
features and market regime detection.

Key Components:
1. Feature Engineering: Creates 9 custom features from market data
2. Market Regime Detection: Identifies 5 market conditions
3. LLM Feature Selection: Uses AI to select most relevant features
4. Strategy Selection: Chooses optimal strategy with position sizing
5. Adaptive Triggers: Adjusts DCA triggers based on market volatility

Example:
    >>> switcher = StrategySwitcher()
    >>> result = switcher.analyze_and_recommend(
    ...     market_data, indicators, sentiment_data, onchain_data
    ... )
    >>> print(f"Strategy: {result['strategy']}")
    Strategy: swing
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from config.settings import Settings
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from data_models.sentiment import SentimentData

# Configure logger
logger = logging.getLogger(__name__)


class StrategySwitcher:
    """
    Adaptive strategy switching with LLM-powered feature engineering.

    The StrategySwitcher analyzes market conditions using custom engineered
    features and selects the optimal trading strategy (DCA, Swing, or Day)
    based on current market regime and risk profile.

    Strategies:
        DCA: Conservative long-term accumulation during downtrends/crises
        SWING: Moderate trend-following for clear directional moves
        DAY: Aggressive volatility trading for choppy markets

    Attributes:
        current_strategy: Currently active strategy name
        previous_strategy: Previously active strategy (for tracking switches)
        switch_count: Total number of strategy switches
        last_switch_time: Timestamp of last strategy change
    """

    def __init__(self):
        """Initialize strategy switcher with default conservative stance."""
        self.current_strategy = "dca"  # Start conservative
        self.previous_strategy = None
        self.switch_count = 0
        self.last_switch_time = None

        logger.info("StrategySwitcher initialized (default: DCA)")

    def analyze_and_recommend(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        sentiment_data: SentimentData,
        onchain_data: Dict
    ) -> Dict:
        """
        Perform complete market analysis and generate strategy recommendation.

        This is the main entry point that orchestrates the entire analysis:
        1. Detects current market regime (crisis, trending, etc.)
        2. Engineers all 9 custom features
        3. Uses LLM to select top 3 most relevant features
        4. Selects optimal strategy based on regime and features
        5. Calculates adaptive DCA trigger thresholds

        Args:
            market_data: Current BTC price, volume, and price changes
            indicators: Technical indicators (RSI, MACD, ATR, SMA, EMA)
            sentiment_data: Fear/Greed index and market psychology
            onchain_data: Network metrics (hash rate, mempool, blocks)

        Returns:
            dict: Complete recommendation including:
                - strategy: Selected strategy name (dca/swing/day)
                - confidence: Confidence level (0-1)
                - position_size_pct: Recommended position size
                - adaptive_dca_trigger: Dynamic DCA trigger threshold
                - market_regime: Detected market condition
                - selected_features: Top 3 features chosen by LLM
                - switch_reason: Explanation for strategy choice

        Example:
            >>> result = switcher.analyze_and_recommend(...)
            >>> print(f"Strategy: {result['strategy']}")
            >>> print(f"Confidence: {result['confidence']:.1%}")
        """
        logger.info("Analyzing market for strategy recommendation...")

        # Step 1: Detect market regime
        regime = self.detect_market_regime(market_data, indicators, sentiment_data)
        logger.info(f"Market regime detected: {regime.upper()}")

        # Step 2: Engineer all features
        simple = self.engineer_simple_features(market_data, indicators)
        smart = self.engineer_smart_features(market_data, indicators, onchain_data)
        unique = self.engineer_unique_features(simple, smart, sentiment_data)

        all_features = {**simple, **smart, **unique}
        logger.info(f"Engineered {len(all_features)} features")

        # Step 3: LLM feature selection
        selected_features = self.select_top_features_with_llm(regime, all_features)
        logger.info(f"Top features: {', '.join(selected_features.keys())}")

        # Step 4: Select strategy
        current_positions = 0  # TODO: Get from position manager
        strategy_rec = self.select_strategy(regime, selected_features, current_positions)

        # Check for strategy change
        if strategy_rec["strategy"] != self.current_strategy:
            self.previous_strategy = self.current_strategy
            self.current_strategy = strategy_rec["strategy"]
            self.switch_count += 1
            self.last_switch_time = datetime.now()

            logger.warning(
                f"STRATEGY SWITCH: {self.previous_strategy.upper()} -> "
                f"{self.current_strategy.upper()}"
            )

        # Step 5: Calculate adaptive DCA trigger
        adaptive_trigger = self.calculate_adaptive_dca_trigger(regime, selected_features)

        # Build complete response
        result = {
            "strategy": strategy_rec["strategy"],
            "previous_strategy": self.previous_strategy,
            "switch_reason": strategy_rec["reason"],
            "market_regime": regime,
            "confidence": strategy_rec["confidence"],
            "position_size_pct": strategy_rec["position_size_pct"],
            "adaptive_dca_trigger": adaptive_trigger,
            "selected_features": selected_features,
            "all_features": all_features,
            "switch_count": self.switch_count,
            "last_switch": self.last_switch_time.isoformat() if self.last_switch_time else None
        }

        logger.info(
            f"Recommendation: {result['strategy'].upper()} "
            f"({result['confidence']:.0%} confidence, "
            f"{result['position_size_pct']:.1f}% position)"
        )

        return result

    def detect_market_regime(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        sentiment_data: SentimentData
    ) -> str:
        """
        Detect current market regime using rule-based heuristics.

        Market regimes help contextualize feature importance:
        - crisis: Extreme fear or volatility (protect capital)
        - high_volatility: Large price swings (trading opportunities)
        - trending_up: Clear uptrend (momentum strategy)
        - trending_down: Clear downtrend (accumulation opportunity)
        - ranging: Sideways movement (mean reversion)

        Args:
            market_data: Price and volume data
            indicators: Technical indicators for trend/volatility
            sentiment_data: Market psychology indicators

        Returns:
            str: Market regime name

        Example:
            >>> regime = switcher.detect_market_regime(...)
            >>> print(regime)
            'high_volatility'
        """
        # Handle both dict and object access
        current_price = market_data.get('current_price') if isinstance(market_data, dict) else market_data.price
        atr = indicators.get('atr') if isinstance(indicators, dict) else indicators.atr_14
        rsi = indicators.get('rsi') if isinstance(indicators, dict) else indicators.rsi_14
        sma_50 = indicators.get('sma_50', current_price) if isinstance(indicators, dict) else getattr(indicators, 'sma_50', current_price)
        fgi = sentiment_data.get('fear_greed_index') if isinstance(sentiment_data, dict) else sentiment_data.fear_greed_index

        atr_pct = (atr / current_price) * 100

        # Crisis: Extreme fear OR extreme volatility
        if fgi < 25 or atr_pct > 8:
            return "crisis"

        # High volatility: ATR > 5% of price
        if atr_pct > 5:
            return "high_volatility"

        # Trending up: Price above SMA AND RSI bullish
        if current_price > sma_50 and rsi > 50:
            return "trending_up"

        # Trending down: Price below SMA AND RSI bearish
        if current_price < sma_50 and rsi < 50:
            return "trending_down"

        # Default: Ranging (sideways movement)
        return "ranging"

    def engineer_simple_features(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators
    ) -> Dict[str, float]:
        """
        Engineer simple normalized features from technical indicators.

        WHY FEATURE ENGINEERING:
        Raw indicators (RSI, ATR, SMA) are not directly comparable across
        different market conditions. Feature engineering normalizes these
        values so the LLM can compare them meaningfully.

        FEATURES CREATED:
        1. volatility_efficiency: Measures how volatile the market is relative
           to price. Higher = more volatile = favor DAY trading.
           Formula: (ATR / current_price) * 100
           Why: 2% ATR on $100k BTC = same volatility as 2% ATR on $50k BTC

        2. trend_strength: Measures how far price has moved from its average,
           normalized by volatility (ATR). Higher = stronger trend = favor SWING.
           Formula: abs(current_price - SMA_50) / ATR
           Why: Being 3 ATRs above SMA is strong regardless of absolute price

        3. momentum_score: RSI (Relative Strength Index) centered at 0 instead
           of 50. Negative = oversold, Positive = overbought.
           Formula: (RSI - 50) / 50  # Maps 0-100 RSI to -1.0 to +1.0
           Why: -1.0 = deeply oversold (RSI 0), +1.0 = overbought (RSI 100)

        ABBREVIATIONS:
        - ATR: Average True Range (14-period volatility measure)
        - RSI: Relative Strength Index (0-100 momentum indicator)
        - SMA: Simple Moving Average (50-period average price)

        Args:
            market_data: Current market price data
            indicators: Technical indicators (RSI, ATR, SMA, etc.)

        Returns:
            dict: Three simple features with normalized values (-1.0 to +1.0 scale)

        Example:
            >>> features = switcher.engineer_simple_features(market_data, indicators)
            >>> features['volatility_efficiency']
            2.5  # 2.5% volatility relative to price
            >>> features['momentum_score']
            -0.3  # RSI at 35 (slightly oversold)
        """
        # Handle both dict and object access
        current_price = market_data.get('current_price') if isinstance(market_data, dict) else market_data.price
        atr = indicators.get('atr') if isinstance(indicators, dict) else indicators.atr_14
        rsi = indicators.get('rsi') if isinstance(indicators, dict) else indicators.rsi_14
        sma_50 = indicators.get('sma_50', current_price) if isinstance(indicators, dict) else getattr(indicators, 'sma_50', current_price)

        return {
            "volatility_efficiency": (atr / current_price) * 100,
            "trend_strength": abs(current_price - sma_50) / atr,
            "momentum_score": (rsi - 50) / 50
        }

    def engineer_smart_features(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        onchain_data: Dict
    ) -> Dict[str, float]:
        """
        Engineer smart features combining multiple data sources.

        These features combine on-chain metrics with price data:
        - network_health: Hash rate strength adjusted for congestion
        - blockchain_pressure: Transaction backlog severity
        - miner_confidence: Hash rate relative to price

        Args:
            market_data: Market price and volume
            indicators: Technical indicators
            onchain_data: On-chain network metrics

        Returns:
            dict: Three smart cross-domain features
        """
        # Handle both dict and object access for market data
        current_price = market_data.get('current_price') if isinstance(market_data, dict) else market_data.price

        hash_rate = onchain_data.get("hash_rate", {}).get("hash_rate_ehs", 600)
        mempool = onchain_data.get("mempool", {})
        mempool_size = mempool.get("tx_count", 0) if isinstance(mempool, dict) else 0
        block_metrics = onchain_data.get("block_metrics", {})
        block_size = block_metrics.get("latest_block_size_mb", 1.5) if isinstance(block_metrics, dict) else 1.5

        return {
            "network_health": (hash_rate / 100) * (1 - min(mempool_size / 20000, 1)),
            "blockchain_pressure": (block_size * mempool_size) / 1000,
            "miner_confidence": hash_rate / max(current_price / 1000, 1)
        }

    def engineer_unique_features(
        self,
        simple_features: Dict[str, float],
        smart_features: Dict[str, float],
        sentiment_data: SentimentData
    ) -> Dict[str, float]:
        """
        Engineer unique proprietary feature combinations.

        These are custom combinations not found in standard analysis:
        - fear_greed_modulated: Sentiment adjusted for volatility
        - smart_volume: Volume weighted by trend strength
        - risk_adjusted_signal: Momentum normalized by volatility

        Args:
            simple_features: Simple engineered features
            smart_features: Smart cross-domain features
            sentiment_data: Market sentiment data

        Returns:
            dict: Three unique proprietary features
        """
        # Handle both dict and object access
        fear_greed = sentiment_data.get('fear_greed_index') if isinstance(sentiment_data, dict) else sentiment_data.fear_greed_index

        return {
            "fear_greed_modulated": fear_greed * (1 + simple_features["volatility_efficiency"] / 100),
            "risk_adjusted_signal": simple_features["momentum_score"] / max(simple_features["volatility_efficiency"], 0.1)
        }

    def select_top_features_with_llm(
        self,
        market_regime: str,
        all_features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Use LLM to intelligently select top 3 most relevant features.

        The LLM analyzes market regime and available features to select
        the most predictive indicators for current conditions.

        Regime-specific priorities:
        - high_volatility: volatility_efficiency, blockchain_pressure
        - trending_up: trend_strength, momentum_score, network_health
        - trending_down: fear_greed_modulated, miner_confidence
        - ranging: blockchain_pressure, volatility_efficiency
        - crisis: network_health, fear_greed_modulated, miner_confidence

        Args:
            market_regime: Current market condition
            all_features: All 9 engineered features

        Returns:
            dict: Top 3 features selected by LLM (or rule-based fallback)

        Example:
            >>> selected = switcher.select_top_features_with_llm(...)
            >>> print(list(selected.keys()))
            ['trend_strength', 'momentum_score', 'network_health']
        """
        try:
            settings = Settings.get_instance()

            llm = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
                model="mistralai/mistral-7b-instruct:free",
                temperature=0.1,
                max_tokens=200
            )

            prompt = f"""You are a Bitcoin trading analyst. Select the top 3 most relevant features for the current market regime.

Market Regime: {market_regime}

Available Features (name: value):
{json.dumps(all_features, indent=2)}

Selection Rules by Regime:
- high_volatility: Prioritize volatility_efficiency, blockchain_pressure, fear_greed_modulated
- trending_up: Prioritize trend_strength, momentum_score, network_health
- trending_down: Prioritize fear_greed_modulated, miner_confidence, risk_adjusted_signal
- ranging: Prioritize blockchain_pressure, volatility_efficiency
- crisis: Prioritize network_health, fear_greed_modulated, miner_confidence

Select exactly 3 features from the Available Features list above. Return ONLY valid JSON using the ACTUAL feature names (no markdown, no explanation):
{{"actual_feature_name_1": value1, "actual_feature_name_2": value2, "actual_feature_name_3": value3}}

Example: {{"volatility_efficiency": 4.83, "network_health": 5.8, "momentum_score": -0.44}}"""

            response = llm.invoke(prompt)

            # Parse response
            if isinstance(response, AIMessage):
                response = response.content

            # Clean and parse JSON
            response_clean = response.replace("```json", "").replace("```", "").strip()
            selected = json.loads(response_clean)

            logger.info(f"LLM selected features: {list(selected.keys())}")
            return selected

        except Exception as e:
            logger.warning(f"LLM feature selection failed: {e}, using rule-based fallback")

            # Fallback: Rule-based selection
            defaults = {
                "high_volatility": ["volatility_efficiency", "blockchain_pressure", "fear_greed_modulated"],
                "trending_up": ["trend_strength", "momentum_score", "network_health"],
                "trending_down": ["fear_greed_modulated", "miner_confidence", "risk_adjusted_signal"],
                "ranging": ["blockchain_pressure", "volatility_efficiency", "network_health"],
                "crisis": ["network_health", "fear_greed_modulated", "miner_confidence"]
            }

            feature_names = defaults.get(
                market_regime,
                ["volatility_efficiency", "network_health", "momentum_score"]
            )

            return {name: all_features[name] for name in feature_names if name in all_features}

    def select_strategy(
        self,
        market_regime: str,
        selected_features: Dict[str, float],
        current_positions: int
    ) -> Dict:
        """
        Select optimal trading strategy based on market conditions.

        Strategy logic:
        - DCA: Used in crisis, downtrends, or strong network fundamentals
        - SWING: Used in clear trends with moderate volatility
        - DAY: Used in high volatility or ranging markets

        Args:
            market_regime: Current market condition
            selected_features: Top 3 features from LLM selection
            current_positions: Number of open positions (unused currently)

        Returns:
            dict: Strategy recommendation with confidence and position size

        Example:
            >>> rec = switcher.select_strategy('trending_up', features, 2)
            >>> print(rec['strategy'])
            'swing'
        """
        # Extract feature values with safe defaults
        volatility_eff = selected_features.get("volatility_efficiency", 2.0)
        network_health = selected_features.get("network_health", 0.5)
        trend_strength = selected_features.get("trend_strength", 1.0)
        momentum = selected_features.get("momentum_score", 0)

        # Strategy selection rules

        # 1. CRISIS: Always DCA (conservative capital preservation)
        if market_regime == "crisis":
            return {
                "strategy": "dca",
                "reason": "Crisis detected - accumulate at low prices",
                "position_size_pct": 2.0,
                "confidence": 0.90
            }

        # 2. TRENDING UP: Swing trading (ride the trend)
        if market_regime == "trending_up" and momentum > 0.2:
            return {
                "strategy": "swing",
                "reason": "Strong uptrend with positive momentum",
                "position_size_pct": 10.0,
                "confidence": 0.80
            }

        # 3. HIGH VOLATILITY: Day trading (capture swings)
        if market_regime == "high_volatility" and volatility_eff > 4.0:
            return {
                "strategy": "day",
                "reason": "High volatility creates trading opportunities",
                "position_size_pct": 5.0,
                "confidence": 0.70
            }

        # 4. TRENDING DOWN + Strong Network: DCA (buy the dip)
        if market_regime == "trending_down" and network_health > 0.7:
            return {
                "strategy": "dca",
                "reason": "Price down but network strong - good accumulation",
                "position_size_pct": 3.0,
                "confidence": 0.85
            }

        # 5. RANGING: Day trading (scalp the range)
        if market_regime == "ranging":
            return {
                "strategy": "day",
                "reason": "Ranging market - trade the bounds",
                "position_size_pct": 4.0,
                "confidence": 0.65
            }

        # 6. DEFAULT: DCA (conservative fallback)
        return {
            "strategy": "dca",
            "reason": "Default conservative approach",
            "position_size_pct": 2.0,
            "confidence": 0.60
        }

    def calculate_adaptive_dca_trigger(
        self,
        market_regime: str,
        selected_features: Dict[str, float]
    ) -> float:
        """
        Calculate adaptive DCA trigger threshold based on market volatility.

        Base trigger is 2.0% price drop. Adjustments:
        - High volatility: +1.0% (wait for bigger drops)
        - Low volatility: -0.5% (tighter triggers)
        - Crisis: -0.5% (aggressive accumulation)
        - Trending up: +0.5% (more selective)

        Range: 1.5% to 3.5%

        Args:
            market_regime: Current market condition
            selected_features: Top features with volatility info

        Returns:
            float: Adaptive DCA trigger percentage

        Example:
            >>> trigger = switcher.calculate_adaptive_dca_trigger('crisis', features)
            >>> print(trigger)
            1.5
        """
        base_trigger = 2.0

        volatility_eff = selected_features.get("volatility_efficiency", 2.0)

        # Volatility adjustment
        if volatility_eff > 5.0:
            base_trigger += 1.0  # High vol: wait for bigger drops
        elif volatility_eff < 2.0:
            base_trigger -= 0.5  # Low vol: tighter triggers

        # Regime adjustment
        if market_regime == "crisis":
            base_trigger -= 0.5  # Aggressive in crisis
        elif market_regime == "trending_up":
            base_trigger += 0.5  # Selective in uptrend

        # Clamp to safe range
        adaptive = max(1.5, min(3.5, base_trigger))

        logger.info(f"Adaptive DCA trigger: {adaptive:.1f}%")

        return adaptive
