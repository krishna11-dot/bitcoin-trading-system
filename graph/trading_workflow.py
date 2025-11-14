"""7-Node LangGraph Trading Workflow - Adaptive Strategy Selection.

WHY THIS FILE EXISTS:
This is the core orchestration engine that coordinates all 7 nodes of the
trading system using LangGraph's state machine. It manages data flow between
parallel data collection, indicator calculations, strategy selection, AI analysis,
and trade decisions.

ARCHITECTURE (7 Nodes):
    NODE 1: parallel_data_collection_node()
        - Fetches data from 3 sources simultaneously (Binance, CoinMarketCap, Blockchain.com)
        - WHY PARALLEL: Cuts data collection time from 6.5s → 3s (2x speedup)

    NODE 2: calculate_indicators_node()
        - Calculates RSI (Relative Strength Index), MACD (Moving Average Convergence Divergence),
          ATR (Average True Range), SMA (Simple Moving Average), EMA (Exponential Moving Average)
        - WHY NEEDED: AI agents need technical indicators to make informed decisions

    NODE 3: strategy_selection_node() [NEW]
        - Detects market regime (crisis, trending_up/down, ranging, high_volatility)
        - Engineers 8 custom features from market data
        - Uses LLM to select top 3 most relevant features
        - Selects optimal strategy: DCA (conservative) / SWING (moderate) / DAY (aggressive)
        - WHY ADDED: Enables adaptive trading instead of fixed DCA strategy

    NODE 4: analyze_market_node()
        - LLM analyzes technical indicators
        - RAG (Retrieval-Augmented Generation): Queries 50 similar historical patterns
        - WHY: AI can spot patterns humans miss in historical data

    NODE 5: analyze_sentiment_node()
        - LLM analyzes Fear & Greed Index (0-100 scale)
        - WHY: Market psychology drives short-term price moves

    NODE 6: assess_risk_node()
        - LLM evaluates on-chain metrics (hash rate, mempool size)
        - Assesses volatility via ATR
        - WHY: Network health affects long-term price stability

    NODE 7: dca_decision_node()
        - LLM makes final buy/hold decision
        - Combines ALL inputs: market, sentiment, risk, RAG, selected strategy
        - WHY LAST: Needs all analysis results before deciding

EXECUTION FLOW:
    parallel_data_collection → calculate_indicators → select_strategy →
    analyze_market → analyze_sentiment → assess_risk → dca_decision → END

KEY ABBREVIATIONS:
    - DCA: Dollar-Cost Averaging (buying fixed USD amounts regularly)
    - RSI: Relative Strength Index (momentum indicator, 0-100)
    - MACD: Moving Average Convergence Divergence (trend strength)
    - ATR: Average True Range (volatility measure for stop-loss)
    - SMA: Simple Moving Average (50-period average price)
    - EMA: Exponential Moving Average (gives more weight to recent prices)
    - LLM: Large Language Model (AI agent like Mistral-7B)
    - RAG: Retrieval-Augmented Generation (query historical patterns)

TIMING:
    - Total: ~110 seconds per cycle
    - Data collection: 3s (parallel)
    - Indicators: <1s
    - Strategy selection: 15-20s (LLM call)
    - 4 AI agents: 60-80s (sequential LLM calls)

Example:
    >>> import asyncio
    >>> from graph import run_trading_cycle
    >>>
    >>> config = {"dca_threshold": 3.0, "dca_amount": 100}
    >>> result = asyncio.run(run_trading_cycle(config))
    >>> print(f"Strategy: {result['strategy_recommendation']['strategy']}")
    >>> print(f"Decision: {result['trade_decision'].action}")
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agents.dca_decision_agent import make_dca_decision
from agents.market_analysis_agent import analyze_market
from agents.risk_assessment_agent import assess_risk
from agents.sentiment_analysis_agent import analyze_sentiment
from data_models import (
    MarketData,
    PortfolioState,
    SentimentData,
    TechnicalIndicators,
    TradeDecision,
)
from tools.binance_client import BinanceClient
from tools.coinmarketcap_client import CoinMarketCapClient
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer
from tools.indicator_calculator import calculate_all_indicators
from tools.strategy_switcher import StrategySwitcher

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================


class TradingState(TypedDict, total=False):
    """Complete state for HYBRID trading workflow.

    This state is passed through all nodes in the LangGraph workflow,
    accumulating data and analysis results.

    Attributes:
        # Input data (from parallel collection)
        market_data: Current market price and volume from Binance
        sentiment_data: Fear/Greed Index and sentiment metrics
        onchain_data: On-chain metrics from CryptoQuant (optional)
        indicators: Technical indicators (RSI, MACD, ATR, etc.)

        # Analysis outputs (from sequential pipeline)
        market_analysis: Market trend analysis from LLM
        sentiment_analysis: Sentiment analysis from LLM
        risk_assessment: Risk and position sizing from LLM
        trade_decision: Final DCA buy/hold decision

        # Portfolio & configuration
        portfolio_state: Current portfolio balances and positions
        config: Trading parameters (DCA threshold, position size, etc.)

        # Meta
        timestamp: Workflow execution timestamp
        errors: List of errors encountered during workflow
    """

    # Input data
    market_data: Optional[MarketData]
    sentiment_data: Optional[SentimentData]
    onchain_data: Optional[Dict]
    indicators: Optional[TechnicalIndicators]

    # Analysis outputs
    market_analysis: Optional[Dict]
    sentiment_analysis: Optional[Dict]
    risk_assessment: Optional[Dict]
    trade_decision: Optional[TradeDecision]

    # Strategy selection (NEW)
    strategy_recommendation: Optional[Dict]

    # Portfolio
    portfolio_state: Optional[PortfolioState]

    # Meta
    timestamp: str
    errors: List[str]
    config: Dict[str, Any]


# ============================================================================
# PARALLEL DATA COLLECTION AGENTS (Run simultaneously with asyncio.gather)
# ============================================================================


async def fetch_market_data() -> MarketData:
    """Fetch market data from Binance (async).

    Time: ~2 seconds

    Returns:
        MarketData: Current BTC price, volume, 24h change

    Raises:
        Exception: If Binance API fails
    """
    try:
        logger.info(" Fetching market data from Binance...")

        # Run synchronous Binance client in thread pool
        loop = asyncio.get_event_loop()
        binance = BinanceClient()

        # Get current price (runs in thread pool to not block)
        market_data = await loop.run_in_executor(
            None, binance.get_current_price, "BTCUSDT"
        )

        logger.info(
            f" Market data: ${market_data.price:,.2f} "
            f"({market_data.change_24h:+.2f}%)"
        )
        return market_data

    except Exception as e:
        logger.error(f" Market data failed: {e}")
        raise


async def fetch_sentiment_data() -> SentimentData:
    """Fetch sentiment data from CoinMarketCap (async).

    Time: ~1.5 seconds

    Returns:
        SentimentData: Fear/Greed Index and sentiment metrics

    Raises:
        Exception: If CoinMarketCap API fails
    """
    try:
        logger.info(" Fetching sentiment data from CoinMarketCap...")

        loop = asyncio.get_event_loop()
        cmc = CoinMarketCapClient()

        # Get Fear/Greed Index
        fear_greed = await loop.run_in_executor(None, cmc.get_fear_greed_index)

        # Create sentiment data
        sentiment_data = SentimentData(
            fear_greed_index=fear_greed,
            social_volume="medium",  # Placeholder
            news_sentiment=0.0,  # Placeholder
            trending_score=50,  # Placeholder
            timestamp=datetime.now().isoformat(),
        )

        logger.info(f" Sentiment: Fear/Greed={fear_greed} ({sentiment_data.get_fear_greed_label()})")
        return sentiment_data

    except Exception as e:
        logger.error(f" Sentiment data failed: {e}")
        raise


async def fetch_onchain_data() -> Dict:
    """Fetch on-chain data from CryptoQuant (async).

    Time: ~3 seconds

    Returns:
        Dict: On-chain metrics (exchange flows, MVRV, etc.)

    Note:
        On-chain data is optional - returns empty dict on failure
    """
    try:
        logger.info(" Fetching on-chain data from Blockchain.com...")

        loop = asyncio.get_event_loop()
        analyzer = BitcoinOnChainAnalyzer()

        # Get comprehensive on-chain metrics
        onchain_data = await loop.run_in_executor(None, analyzer.get_comprehensive_metrics)

        logger.info(f" On-chain data fetched ({len(onchain_data)} metrics)")
        return onchain_data

    except Exception as e:
        logger.error(f" On-chain data failed: {e}")
        # Return empty dict - on-chain is optional
        return {}


async def parallel_data_collection_node(state: TradingState) -> TradingState:
    """Run 3 data collection agents SIMULTANEOUSLY using asyncio.gather.

    This is the HYBRID ARCHITECTURE advantage:
    - Sequential execution: 2s + 1.5s + 3s = 6.5 seconds
    - Parallel execution: max(2s, 1.5s, 3s) = 3 seconds (2.17x faster!)

    Uses asyncio.gather with return_exceptions=True to ensure one failing
    agent doesn't block the others.

    Args:
        state: Current trading state

    Returns:
        TradingState: Updated state with market_data, sentiment_data, onchain_data
    """
    logger.info(" Starting PARALLEL data collection (3 agents simultaneously)...")
    start_time = datetime.now()

    try:
        # Run all 3 agents simultaneously
        results = await asyncio.gather(
            fetch_market_data(),
            fetch_sentiment_data(),
            fetch_onchain_data(),
            return_exceptions=True,  # Don't fail if one agent fails
        )

        market_data, sentiment_data, onchain_data = results

        # Check for exceptions and handle gracefully
        if isinstance(market_data, Exception):
            logger.error(f"Market data agent failed: {market_data}")
            market_data = None
            state["errors"].append(f"Market data: {str(market_data)}")

        if isinstance(sentiment_data, Exception):
            logger.error(f"Sentiment agent failed: {sentiment_data}")
            # Create default neutral sentiment
            sentiment_data = SentimentData(
                fear_greed_index=50,  # Neutral
                social_volume="medium",
                news_sentiment=0.0,
                trending_score=50,
                timestamp=datetime.now().isoformat(),
            )
            state["errors"].append(f"Sentiment data: Using default")

        if isinstance(onchain_data, Exception):
            logger.error(f"On-chain agent failed: {onchain_data}")
            onchain_data = {}
            # Don't add to errors - on-chain is optional

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f" PARALLEL data collection complete in {elapsed:.2f}s")

        return {
            **state,
            "market_data": market_data,
            "sentiment_data": sentiment_data,
            "onchain_data": onchain_data,
        }

    except Exception as e:
        logger.error(f" Parallel collection failed: {e}")
        state["errors"].append(f"Parallel collection: {str(e)}")
        return state


# ============================================================================
# SEQUENTIAL ANALYSIS PIPELINE (Runs one after another)
# ============================================================================


def calculate_indicators_node(state: TradingState) -> TradingState:
    """Calculate technical indicators from market data.

    Args:
        state: Current trading state with market_data

    Returns:
        TradingState: Updated state with indicators
    """
    logger.info(" Calculating technical indicators...")

    try:
        market_data = state.get("market_data")
        if not market_data:
            raise ValueError("Market data not available")

        # Get historical data for indicator calculation
        binance = BinanceClient()
        klines = binance.get_historical_klines(
            symbol="BTCUSDT", interval="1h", limit=100
        )
        logger.info(f"Fetched {len(klines)} klines, converting to MarketData...")

        # Convert klines to MarketData list
        market_data_list = []
        for i, kline in enumerate(klines):
            try:
                # Convert Unix timestamp (ms) to ISO 8601
                timestamp_ms = int(kline['open_time'])
                timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000).isoformat() + "Z"

                md = MarketData(
                    price=float(kline['close']),  # Close price
                    volume=float(kline['volume']),  # Volume
                    timestamp=timestamp_iso,  # ISO 8601 format
                    change_24h=0.0,  # Will calculate separately if needed
                    high_24h=float(kline['high']),  # High
                    low_24h=float(kline['low']),  # Low
                )
                market_data_list.append(md)
            except Exception as e:
                logger.error(f"Failed to create MarketData from kline {i}: {e}")
                logger.error(f"Kline data: {kline}")
                raise  # Re-raise to see full error

        # Calculate all indicators
        logger.info(f"Calculating indicators from {len(market_data_list)} data points")
        indicators = calculate_all_indicators(market_data_list)

        if indicators:
            logger.info(
                f" Indicators: RSI={indicators.rsi_14:.1f}, "
                f"MACD={indicators.macd:.2f}, ATR=${indicators.atr_14:.2f}"
            )
            return {**state, "indicators": indicators}
        else:
            logger.error("calculate_all_indicators returned None")
            raise ValueError("Indicator calculation returned None (insufficient data or calculation error)")

    except Exception as e:
        logger.error(f" Indicator calculation failed: {e}")
        state["errors"].append(f"Indicators: {str(e)}")
        return state


def strategy_selection_node(state: TradingState) -> TradingState:
    """
    Select optimal trading strategy using Strategy Switcher.

    Analyzes market regime and engineered features to determine the best strategy
    (DCA, SWING, or DAY) with adaptive DCA triggers.

    Args:
        state: Current trading state with market_data, indicators, sentiment_data

    Returns:
        TradingState: Updated state with strategy_recommendation
    """
    logger.info(" Selecting trading strategy based on market conditions...")

    try:
        # Initialize Strategy Switcher
        switcher = StrategySwitcher()

        # Get recommendation
        recommendation = switcher.analyze_and_recommend(
            market_data=state.get("market_data"),
            indicators=state.get("indicators"),
            sentiment_data=state.get("sentiment_data"),
            onchain_data=state.get("onchain_data", {})
        )

        # Store strategy selection in state
        strategy_rec = {
            "strategy": recommendation["strategy"],
            "confidence": recommendation["confidence"],
            "position_size_pct": recommendation["position_size_pct"],
            "adaptive_dca_trigger": recommendation["adaptive_dca_trigger"],
            "market_regime": recommendation["market_regime"],
            "selected_features": recommendation["selected_features"],
            "reasoning": recommendation["switch_reason"]
        }

        logger.info(
            f" Strategy: {recommendation['strategy'].upper()} "
            f"(confidence: {recommendation['confidence']:.0%}, "
            f"regime: {recommendation['market_regime']}, "
            f"trigger: {recommendation['adaptive_dca_trigger']:.1f}%)"
        )

        return {**state, "strategy_recommendation": strategy_rec}

    except Exception as e:
        logger.error(f" Strategy selection failed: {e}")
        state["errors"].append(f"Strategy selection: {str(e)}")
        # Fallback to conservative DCA
        fallback = {
            "strategy": "dca",
            "confidence": 0.6,
            "position_size_pct": 2.0,
            "adaptive_dca_trigger": 3.0,
            "market_regime": "unknown",
            "reasoning": "Fallback to conservative DCA due to error"
        }
        return {**state, "strategy_recommendation": fallback}


def market_analysis_node(state: TradingState) -> TradingState:
    """Run market analysis agent (LLM via OpenRouter).

    Args:
        state: Current trading state with market_data and indicators

    Returns:
        TradingState: Updated state with market_analysis
    """
    logger.info(" Running market analysis agent (LLM)...")

    try:
        market_data = state.get("market_data")
        indicators = state.get("indicators")

        if not market_data or not indicators:
            raise ValueError("Missing market data or indicators")

        # Call LangChain market analysis agent
        analysis = analyze_market(market_data, indicators)

        logger.info(
            f" Market analysis: {analysis['trend'].upper()} "
            f"({analysis['confidence']:.0%} confidence, "
            f"risk: {analysis['risk_level']})"
        )

        return {**state, "market_analysis": analysis}

    except Exception as e:
        logger.error(f" Market analysis failed: {e}")
        state["errors"].append(f"Market analysis: {str(e)}")
        return state


def sentiment_analysis_node(state: TradingState) -> TradingState:
    """Run sentiment analysis agent (LLM via OpenRouter).

    Args:
        state: Current trading state with sentiment_data, market_data, indicators

    Returns:
        TradingState: Updated state with sentiment_analysis
    """
    logger.info(" Running sentiment analysis agent (LLM)...")

    try:
        sentiment_data = state.get("sentiment_data")
        market_data = state.get("market_data")
        indicators = state.get("indicators")

        if not all([sentiment_data, market_data, indicators]):
            raise ValueError("Missing sentiment data, market data, or indicators")

        # Call LangChain sentiment analysis agent
        analysis = analyze_sentiment(sentiment_data, market_data, indicators)

        logger.info(
            f" Sentiment analysis: {analysis['sentiment'].upper()} "
            f"({analysis['confidence']:.0%} confidence, "
            f"psychology: {analysis['crowd_psychology']})"
        )

        return {**state, "sentiment_analysis": analysis}

    except Exception as e:
        logger.error(f" Sentiment analysis failed: {e}")
        state["errors"].append(f"Sentiment analysis: {str(e)}")
        return state


def risk_assessment_node(state: TradingState) -> TradingState:
    """Run risk assessment agent (LLM via OpenRouter).

    Args:
        state: Current trading state with portfolio, market_data, indicators, config

    Returns:
        TradingState: Updated state with risk_assessment
    """
    logger.info(" Running risk assessment agent (LLM)...")

    try:
        portfolio = state.get("portfolio_state")
        market_data = state.get("market_data")
        indicators = state.get("indicators")
        config = state.get("config", {})
        market_analysis = state.get("market_analysis")

        if not all([portfolio, market_data, indicators]):
            raise ValueError("Missing portfolio, market data, or indicators")

        # Call LangChain risk assessment agent
        assessment = assess_risk(
            portfolio, market_data, indicators, config, market_analysis
        )

        logger.info(
            f" Risk assessment: Position=${assessment['recommended_position_usd']:,.2f}, "
            f"Approved={assessment['approved']}, Risk={assessment['risk_percent']:.2f}%"
        )

        return {**state, "risk_assessment": assessment}

    except Exception as e:
        logger.error(f" Risk assessment failed: {e}")
        state["errors"].append(f"Risk assessment: {str(e)}")
        return state


def dca_decision_node(state: TradingState) -> TradingState:
    """Make final DCA decision (LLM via OpenRouter).

    Args:
        state: Complete trading state with all analyses

    Returns:
        TradingState: Updated state with trade_decision
    """
    logger.info(" Making DCA decision (LLM)...")

    try:
        # Call LangChain DCA decision agent
        decision = make_dca_decision(state)

        logger.info(
            f" DCA decision: {decision.action.upper()} "
            f"${decision.amount:.2f} at ${decision.entry_price:,.2f} "
            f"({decision.confidence:.0%} confidence)"
        )

        return {**state, "trade_decision": decision}

    except Exception as e:
        logger.error(f" DCA decision failed: {e}")
        state["errors"].append(f"DCA decision: {str(e)}")

        # Create fallback hold decision
        market_data = state.get("market_data")
        fallback = TradeDecision(
            action="hold",
            amount=0.0001,  # Minimum valid amount for validation
            entry_price=market_data.price if market_data else 100.0,  # Minimum valid price
            confidence=1.0,
            reasoning=f"Decision failed: {str(e)}. Defaulting to hold for safety.",
            timestamp=datetime.now().isoformat(),
            strategy="dca",
        )
        return {**state, "trade_decision": fallback}


# ============================================================================
# WORKFLOW CREATION
# ============================================================================


def create_trading_workflow() -> StateGraph:
    """Create HYBRID trading workflow (parallel + sequential).

    Architecture:
    1. PARALLEL: 3 data agents run simultaneously (3s)
       - fetch_market_data() - Binance
       - fetch_sentiment_data() - CoinMarketCap
       - fetch_onchain_data() - CryptoQuant

    2. SEQUENTIAL: Analysis pipeline (one after another, ~15s)
       - calculate_indicators - Technical indicators
       - market_analysis_node - LLM trend analysis
       - sentiment_analysis_node - LLM sentiment assessment
       - risk_assessment_node - LLM position sizing
       - dca_decision - LLM final decision

    Total time: ~18s (vs ~21.5s pure sequential = 18% faster!)

    Returns:
        StateGraph: Compiled LangGraph workflow
    """
    logger.info(" Creating HYBRID trading workflow (parallel + sequential)...")

    workflow = StateGraph(TradingState)

    # Add nodes (use suffix to avoid conflict with state keys)
    workflow.add_node("parallel_data", parallel_data_collection_node)  # PARALLEL
    workflow.add_node("calculate_indicators", calculate_indicators_node)
    workflow.add_node("select_strategy", strategy_selection_node)  # NEW: Strategy selection
    workflow.add_node("analyze_market", market_analysis_node)  # Changed name
    workflow.add_node("analyze_sentiment", sentiment_analysis_node)  # Changed name
    workflow.add_node("assess_risk", risk_assessment_node)  # Changed name
    workflow.add_node("dca_decision", dca_decision_node)

    # Define flow: PARALLEL first, then SEQUENTIAL
    workflow.set_entry_point("parallel_data")  # Start with parallel collection
    workflow.add_edge("parallel_data", "calculate_indicators")
    workflow.add_edge("calculate_indicators", "select_strategy")  # NEW: Strategy selection
    workflow.add_edge("select_strategy", "analyze_market")  # Updated edge
    workflow.add_edge("analyze_market", "analyze_sentiment")  # Updated edge
    workflow.add_edge("analyze_sentiment", "assess_risk")  # Updated edge
    workflow.add_edge("assess_risk", "dca_decision")  # Updated edge
    workflow.add_edge("dca_decision", END)

    app = workflow.compile()
    logger.info(" HYBRID workflow created (7 nodes: 1 parallel + 1 strategy + 5 sequential)")

    return app


# ============================================================================
# MAIN EXECUTION
# ============================================================================


async def run_trading_cycle(
    config: Optional[Dict] = None, portfolio_state: Optional[PortfolioState] = None
) -> TradingState:
    """Run one complete trading cycle with HYBRID execution.

    This is the main entry point for executing the trading workflow.
    It combines parallel data collection with sequential LLM analysis.

    Args:
        config: Trading configuration dict with:
            - dca_threshold: Price drop % to trigger DCA buy (default: 3.0)
            - dca_amount: Amount to buy in USD (default: 100)
            - atr_multiplier: ATR multiplier for stop-loss (default: 1.5)
            - max_position_size: Max position as fraction of portfolio (default: 0.20)
            - max_total_exposure: Max total exposure as fraction (default: 0.80)
            - emergency_stop: Emergency stop-loss as fraction (default: 0.25)
        portfolio_state: Current portfolio state (BTC balance, USD balance, positions).
            If None, uses default test portfolio.

    Returns:
        TradingState: Final state with trade_decision and all analyses

    Example:
        >>> import asyncio
        >>> from graph import run_trading_cycle
        >>> from data_models import PortfolioState
        >>>
        >>> config = {"dca_threshold": 3.0, "dca_amount": 100}
        >>> portfolio = PortfolioState(btc_balance=0.0, usd_balance=10000.0, ...)
        >>> result = asyncio.run(run_trading_cycle(config, portfolio))
        >>>
        >>> decision = result['trade_decision']
        >>> print(f"Action: {decision.action}")
        >>> print(f"Amount: ${decision.amount}")
    """
    # Default configuration
    if config is None:
        config = {
            "dca_threshold": 3.0,  # 3% drop triggers DCA
            "dca_amount": 100,  # $100 per DCA buy
            "atr_multiplier": 1.5,  # Stop-loss at entry - 1.5*ATR
            "max_position_size": 0.20,  # Max 20% of portfolio per trade
            "max_total_exposure": 0.80,  # Max 80% total exposure
            "emergency_stop": 0.25,  # Emergency stop at 25% portfolio loss
        }

    logger.info("=" * 70)
    logger.info(" Starting HYBRID trading cycle (parallel + sequential)")
    logger.info("=" * 70)

    start_time = datetime.now()

    # Create workflow
    app = create_trading_workflow()

    # Initialize state
    initial_state = TradingState(
        # Data (will be populated by parallel collection)
        market_data=None,
        sentiment_data=None,
        onchain_data=None,
        indicators=None,
        # Analysis (will be populated by sequential pipeline)
        market_analysis=None,
        sentiment_analysis=None,
        risk_assessment=None,
        trade_decision=None,
        # Portfolio (use provided portfolio or default test portfolio)
        portfolio_state=portfolio_state
        if portfolio_state is not None
        else PortfolioState(
            btc_balance=0.0,  # Changed from 0.5 to 0.0 for correct default
            usd_balance=10000.0,
            active_positions=[],
            last_updated=datetime.now().isoformat(),
        ),
        # Meta
        timestamp=datetime.now().isoformat(),
        errors=[],
        config=config,
    )

    # Execute workflow (ainvoke for async execution)
    result = await app.ainvoke(initial_state)

    elapsed = (datetime.now() - start_time).total_seconds()

    # Log results
    logger.info("=" * 70)
    logger.info(f" HYBRID trading cycle complete in {elapsed:.2f}s")
    logger.info("=" * 70)

    if result.get("errors"):
        logger.warning(f" {len(result['errors'])} errors occurred:")
        for error in result["errors"]:
            logger.warning(f"  - {error}")

    decision = result.get("trade_decision")
    if decision:
        logger.info(f" Final Decision:")
        logger.info(f"  Action: {decision.action.upper()}")
        logger.info(f"  Amount: ${decision.amount:.2f}")
        logger.info(f"  Entry: ${decision.entry_price:,.2f}")
        logger.info(f"  Confidence: {decision.confidence:.0%}")
        logger.info(f"  Reasoning: {decision.reasoning}")

    logger.info("=" * 70)

    return result


# For testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("\n" + "=" * 70)
    print(" HYBRID Trading Workflow Test")
    print("=" * 70)

    async def test():
        config = {
            "dca_threshold": 3.0,
            "dca_amount": 100,
            "atr_multiplier": 1.5,
            "max_position_size": 0.20,
            "max_total_exposure": 0.80,
            "emergency_stop": 0.25,
        }

        result = await run_trading_cycle(config)

        print("\n" + "=" * 70)
        print(" Test Results")
        print("=" * 70)
        print(f"Market Data: {'' if result.get('market_data') else ''}")
        print(f"Sentiment Data: {'' if result.get('sentiment_data') else ''}")
        print(f"Indicators: {'' if result.get('indicators') else ''}")
        print(f"Market Analysis: {'' if result.get('market_analysis') else ''}")
        print(f"Sentiment Analysis: {'' if result.get('sentiment_analysis') else ''}")
        print(f"Risk Assessment: {'' if result.get('risk_assessment') else ''}")
        print(f"Trade Decision: {'' if result.get('trade_decision') else ''}")
        print(f"Errors: {len(result.get('errors', []))}")
        print("=" * 70)

    # Run async test
    asyncio.run(test())
