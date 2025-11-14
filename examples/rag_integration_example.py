"""RAG Integration Examples - Complete Trading Workflow.

This file demonstrates how to integrate RAG-enhanced agents into your
Bitcoin trading system for data-driven decision-making.

Examples include:
1. Basic RAG market analysis
2. RAG-enhanced strategy decisions
3. Complete trading workflow with RAG
4. Risk management with RAG insights
5. Performance comparison (with/without RAG)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# RAG-enhanced agents
from agents.rag_enhanced_market_analyst import RAGEnhancedMarketAnalyst
from agents.rag_enhanced_strategy_agent import RAGEnhancedStrategyAgent

# Standard data models
from data_models import MarketData, TechnicalIndicators, PortfolioState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Example 1: Basic RAG Market Analysis
# =============================================================================

def example_1_basic_rag_analysis():
    """Example 1: Basic RAG market analysis with historical patterns."""

    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic RAG Market Analysis")
    print("=" * 80)

    # Current market data
    market_data = MarketData(
        price=65000.0,
        volume=1200000.0,
        timestamp=datetime.now().isoformat(),
        change_24h=3.5,
        high_24h=66000.0,
        low_24h=64000.0
    )

    # Technical indicators
    indicators = TechnicalIndicators(
        rsi_14=72.0,  # Overbought
        macd=250.0,
        macd_signal=230.0,
        macd_histogram=20.0,  # Bullish crossover
        atr_14=1200.0,
        sma_50=63000.0,
        ema_12=64500.0,
        ema_26=63500.0
    )

    print(f"\nCurrent Market State:")
    print(f"  Price: ${market_data.price:,.0f}")
    print(f"  RSI: {indicators.rsi_14:.1f} (Overbought)")
    print(f"  MACD Histogram: {indicators.macd_histogram:+.1f} (Bullish)")

    # Create RAG-enhanced analyst
    analyst = RAGEnhancedMarketAnalyst(
        rag_path="data/Bitcoin_Historical_Data_Raw.csv",
        enable_rag=True
    )

    # Analyze market with RAG
    result = analyst.analyze(
        market_data=market_data,
        indicators=indicators,
        k=50,  # Find 50 similar patterns
        include_standard_analysis=False  # RAG only for this example
    )

    print(f"\nRAG Historical Analysis:")
    print(f"  Similar Patterns Found: {result['rag_similar_patterns']}")
    print(f"  Historical Success Rate: {result['rag_success_rate']:.1%}")
    print(f"  Wins/Losses: {result['rag_num_wins']}/{result['rag_num_losses']}")
    print(f"  Average Outcome: {result['rag_avg_outcome']:+.2f}%")
    print(f"  Best Case: {result['rag_best_outcome']:+.2f}%")
    print(f"  Worst Case: {result['rag_worst_outcome']:+.2f}%")
    print(f"  Confidence Level: {result['rag_confidence'].upper()}")
    print(f"  Recommendation: {result['rag_recommendation']}")

    print(f"\nData-Driven Insight:")
    print(f"  {result['data_driven_insight']}")

    # Trading decision based on RAG
    if result['rag_success_rate'] >= 0.65:
        print(f"\n[OK] HIGH CONFIDENCE: Historical data supports trading")
        print(f"  Expected profit: {result['rag_avg_outcome']:+.2f}%")
    elif result['rag_success_rate'] >= 0.50:
        print(f"\n[\!] MEDIUM CONFIDENCE: Proceed with caution")
    else:
        print(f"\n[FAIL] LOW CONFIDENCE: Consider holding")

    return result


# =============================================================================
# Example 2: RAG-Enhanced Strategy Decision
# =============================================================================

def example_2_rag_strategy_decision():
    """Example 2: Use RAG for strategic trading decisions."""

    print("\n" + "=" * 80)
    print("EXAMPLE 2: RAG-Enhanced Strategy Decision")
    print("=" * 80)

    # Market data
    market_data = MarketData(
        price=45000.0,
        volume=900000.0,
        timestamp=datetime.now().isoformat(),
        change_24h=-2.8,
        high_24h=46000.0,
        low_24h=44500.0
    )

    # Indicators (oversold conditions)
    indicators = TechnicalIndicators(
        rsi_14=28.0,  # Oversold
        macd=-180.0,
        macd_signal=-150.0,
        macd_histogram=-30.0,  # Bearish
        atr_14=950.0,
        sma_50=47000.0,
        ema_12=45500.0,
        ema_26=46500.0
    )

    # Portfolio state
    portfolio = PortfolioState(
        usd_balance=10000.0,
        btc_balance=0.05,  # Small position
        last_updated=datetime.now().isoformat()
    )

    print(f"\nMarket: ${market_data.price:,.0f} (RSI: {indicators.rsi_14:.0f} - Oversold)")
    print(f"Portfolio: ${portfolio.usd_balance:,.0f} cash, {portfolio.btc_balance:.4f} BTC")
    print(f"Position: ${portfolio.btc_balance * market_data.price:,.2f} value")

    # Create strategy agent
    strategy_agent = RAGEnhancedStrategyAgent(
        rag_path="data/Bitcoin_Historical_Data_Raw.csv",
        min_confidence=0.55
    )

    # Make decision
    decision = strategy_agent.decide(
        market_data=market_data,
        indicators=indicators,
        portfolio=portfolio,
        k=50
    )

    print(f"\nStrategy Decision:")
    print(f"  Action: {decision['action']}")
    print(f"  Strategy: {decision['strategy']}")
    print(f"  Confidence: {decision['confidence']:.1%}")
    print(f"  Position Size: {decision['position_size_pct']:.1f}%")
    print(f"  Entry Price: ${decision['entry_price']:,.0f}")
    print(f"  Exit Target: ${decision['exit_target']:,.0f} ({decision['expected_outcome']:+.2f}%)")
    print(f"  Stop Loss: ${decision['stop_loss']:,.0f}")
    print(f"  Historical Success: {decision['historical_success_rate']:.1%}")
    print(f"  RAG-Backed: {'Yes' if decision['rag_backed'] else 'No'}")

    print(f"\nReasoning:")
    print(f"  {decision['reasoning']}")

    # Calculate trade details
    if decision['action'] == "BUY":
        trade_amount = portfolio.usd_balance * (decision['position_size_pct'] / 100)
        btc_to_buy = trade_amount / decision['entry_price']
        expected_profit = trade_amount * (decision['expected_outcome'] / 100)

        print(f"\nTrade Details:")
        print(f"  Cash to invest: ${trade_amount:,.2f} ({decision['position_size_pct']:.1f}%)")
        print(f"  BTC to buy: {btc_to_buy:.6f}")
        print(f"  Expected profit: ${expected_profit:+,.2f}")

    return decision


# =============================================================================
# Example 3: Complete Trading Workflow with RAG
# =============================================================================

def example_3_complete_workflow():
    """Example 3: Complete trading workflow integrating both RAG agents."""

    print("\n" + "=" * 80)
    print("EXAMPLE 3: Complete Trading Workflow with RAG")
    print("=" * 80)

    # Setup
    market_data = MarketData(
        price=55000.0,
        volume=1000000.0,
        timestamp=datetime.now().isoformat(),
        change_24h=0.5,
        high_24h=55500.0,
        low_24h=54500.0
    )

    indicators = TechnicalIndicators(
        rsi_14=50.0,  # Neutral
        macd=25.0,
        macd_signal=20.0,
        macd_histogram=5.0,
        atr_14=800.0,
        sma_50=54800.0,
        ema_12=55100.0,
        ema_26=54900.0
    )

    portfolio = PortfolioState(
        usd_balance=10000.0,
        btc_balance=0.1,
        last_updated=datetime.now().isoformat()
    )

    print(f"\nMarket: ${market_data.price:,.0f}, RSI: {indicators.rsi_14:.0f} (Neutral)")
    print(f"Portfolio: ${portfolio.usd_balance:,.0f} + {portfolio.btc_balance:.4f} BTC")

    # Step 1: Market Analysis with RAG
    print(f"\n--- Step 1: Market Analysis ---")
    analyst = RAGEnhancedMarketAnalyst()
    analysis = analyst.analyze(market_data, indicators, k=50)

    print(f"  RAG Success Rate: {analysis['rag_success_rate']:.1%}")
    print(f"  Avg Outcome: {analysis['rag_avg_outcome']:+.2f}%")
    print(f"  Confidence: {analysis['rag_confidence'].upper()}")

    # Step 2: Strategy Decision with RAG
    print(f"\n--- Step 2: Strategy Decision ---")
    strategy_agent = RAGEnhancedStrategyAgent()
    decision = strategy_agent.decide(
        market_data=market_data,
        indicators=indicators,
        portfolio=portfolio,
        rag_analysis=analysis,  # Use pre-computed analysis
        k=50
    )

    print(f"  Action: {decision['action']}")
    print(f"  Position Size: {decision['position_size_pct']:.1f}%")
    print(f"  Expected Outcome: {decision['expected_outcome']:+.2f}%")

    # Step 3: Risk Assessment
    print(f"\n--- Step 3: Risk Assessment ---")
    risk_reward = decision['best_case'] / abs(decision['worst_case']) if decision['worst_case'] != 0 else 0
    print(f"  Best Case: {decision['best_case']:+.2f}%")
    print(f"  Worst Case: {decision['worst_case']:+.2f}%")
    print(f"  Risk/Reward Ratio: {risk_reward:.2f}:1")

    # Step 4: Final Decision
    print(f"\n--- Step 4: Final Decision ---")

    if decision['action'] != "HOLD":
        if decision['confidence'] >= 0.65:
            print(f"  [OK] EXECUTE: High confidence trade")
        elif decision['confidence'] >= 0.55:
            print(f"  [\!] EXECUTE WITH CAUTION: Medium confidence")
        else:
            print(f"  [FAIL] SKIP: Below confidence threshold")
    else:
        print(f"  -> HOLD: No clear opportunity")

    print(f"\n  Reasoning: {decision['reasoning']}")

    return analysis, decision


# =============================================================================
# Example 4: Risk Management with RAG
# =============================================================================

def example_4_risk_management():
    """Example 4: Use RAG for risk management and position sizing."""

    print("\n" + "=" * 80)
    print("EXAMPLE 4: Risk Management with RAG")
    print("=" * 80)

    # High-risk scenario (volatile market)
    market_data = MarketData(
        price=70000.0,
        volume=2000000.0,
        timestamp=datetime.now().isoformat(),
        change_24h=8.5,  # Large move
        high_24h=72000.0,
        low_24h=64000.0
    )

    indicators = TechnicalIndicators(
        rsi_14=85.0,  # Very overbought
        macd=450.0,
        macd_signal=380.0,
        macd_histogram=70.0,
        atr_14=2500.0,  # High volatility
        sma_50=65000.0,
        ema_12=68000.0,
        ema_26=66000.0
    )

    portfolio = PortfolioState(
        usd_balance=10000.0,
        btc_balance=0.0,  # No position
        last_updated=datetime.now().isoformat()
    )

    print(f"\nHigh-Risk Scenario:")
    print(f"  Price: ${market_data.price:,.0f} (+{market_data.change_24h:.1f}%)")
    print(f"  RSI: {indicators.rsi_14:.0f} (Extremely Overbought)")
    print(f"  ATR: ${indicators.atr_14:,.0f} (High Volatility)")

    # Get RAG risk assessment
    analyst = RAGEnhancedMarketAnalyst()
    analysis = analyst.analyze(market_data, indicators, k=100)  # More patterns for better stats

    print(f"\nRAG Risk Assessment:")
    print(f"  Similar Patterns: {analysis['rag_similar_patterns']}")
    print(f"  Historical Success: {analysis['rag_success_rate']:.1%}")
    print(f"  Avg Outcome: {analysis['rag_avg_outcome']:+.2f}%")
    print(f"  Worst Case: {analysis['rag_worst_outcome']:+.2f}%")

    # Risk-adjusted decision
    strategy_agent = RAGEnhancedStrategyAgent(
        min_confidence=0.70,  # Higher threshold for high-risk
        position_sizing_mode="confidence_based"
    )

    decision = strategy_agent.decide(
        market_data=market_data,
        indicators=indicators,
        portfolio=portfolio,
        rag_analysis=analysis
    )

    print(f"\nRisk-Adjusted Decision:")
    print(f"  Action: {decision['action']}")
    print(f"  Position Size: {decision['position_size_pct']:.1f}% (Risk-adjusted)")
    print(f"  Stop Loss: ${decision['stop_loss']:,.0f}")
    print(f"  Max Loss: {((decision['stop_loss'] - decision['entry_price']) / decision['entry_price'] * 100):+.2f}%")

    if decision['action'] == "HOLD":
        print(f"\n  -> Market too risky. RAG recommends HOLDING.")
    else:
        print(f"\n  -> Proceeding with reduced position size due to high risk.")

    return decision


# =============================================================================
# Example 5: Performance Comparison (With/Without RAG)
# =============================================================================

def example_5_performance_comparison():
    """Example 5: Compare decisions with and without RAG."""

    print("\n" + "=" * 80)
    print("EXAMPLE 5: Performance Comparison (With vs Without RAG)")
    print("=" * 80)

    # Same market conditions
    market_data = MarketData(
        price=60000.0,
        volume=1100000.0,
        timestamp=datetime.now().isoformat(),
        change_24h=1.5,
        high_24h=60500.0,
        low_24h=59500.0
    )

    indicators = TechnicalIndicators(
        rsi_14=68.0,
        macd=180.0,
        macd_signal=160.0,
        macd_histogram=20.0,
        atr_14=1100.0,
        sma_50=58000.0,
        ema_12=59500.0,
        ema_26=58500.0
    )

    portfolio = PortfolioState(
        usd_balance=10000.0,
        btc_balance=0.05,
        last_updated=datetime.now().isoformat()
    )

    print(f"\nMarket: ${market_data.price:,.0f}, RSI: {indicators.rsi_14:.0f}")

    # Decision WITHOUT RAG (simple rules)
    print(f"\n--- WITHOUT RAG (Rule-Based) ---")

    if indicators.rsi_14 > 70:
        simple_action = "SELL"
        simple_confidence = 0.6
        simple_reasoning = "RSI > 70 (Overbought)"
    elif indicators.rsi_14 < 30:
        simple_action = "BUY"
        simple_confidence = 0.6
        simple_reasoning = "RSI < 30 (Oversold)"
    else:
        simple_action = "HOLD"
        simple_confidence = 0.5
        simple_reasoning = "RSI in neutral range"

    print(f"  Action: {simple_action}")
    print(f"  Confidence: {simple_confidence:.1%}")
    print(f"  Reasoning: {simple_reasoning}")
    print(f"  Expected Outcome: Unknown")
    print(f"  Historical Success Rate: Unknown")

    # Decision WITH RAG (data-driven)
    print(f"\n--- WITH RAG (Data-Driven) ---")

    strategy_agent = RAGEnhancedStrategyAgent()
    rag_decision = strategy_agent.decide(market_data, indicators, portfolio, k=50)

    print(f"  Action: {rag_decision['action']}")
    print(f"  Confidence: {rag_decision['confidence']:.1%}")
    print(f"  Reasoning: {rag_decision['reasoning']}")
    print(f"  Expected Outcome: {rag_decision['expected_outcome']:+.2f}%")
    print(f"  Historical Success Rate: {rag_decision['historical_success_rate']:.1%}")
    print(f"  Best/Worst Case: {rag_decision['best_case']:+.2f}% / {rag_decision['worst_case']:+.2f}%")

    # Comparison
    print(f"\n--- COMPARISON ---")
    print(f"  Simple rules rely on thresholds (RSI > 70 = sell)")
    print(f"  RAG uses {rag_decision['rag_backed'] and 'ACTUAL HISTORICAL DATA' or 'N/A'}")
    print(f"  ")
    print(f"  Simple: '{simple_reasoning}'")
    print(f"  RAG: '{rag_decision['reasoning']}'")
    print(f"  ")
    print(f"  [OK] RAG provides statistical evidence for decisions")
    print(f"  [OK] RAG quantifies risk/reward from historical outcomes")
    print(f"  [OK] RAG adapts position size based on confidence")

    return rag_decision


# =============================================================================
# Main: Run All Examples
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("RAG INTEGRATION EXAMPLES - Bitcoin Trading System")
    print("=" * 80)
    print("\nThese examples demonstrate how to integrate RAG (Retrieval-Augmented")
    print("Generation) into your trading workflow for data-driven decisions.")

    try:
        # Run all examples
        example_1_basic_rag_analysis()
        example_2_rag_strategy_decision()
        example_3_complete_workflow()
        example_4_risk_management()
        example_5_performance_comparison()

        print("\n" + "=" * 80)
        print("[OK] ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)

        print("\nKey Takeaways:")
        print("  1. RAG provides statistical confidence for every trade")
        print("  2. Historical success rates reduce emotional decision-making")
        print("  3. Risk/reward is quantified from actual historical data")
        print("  4. Position sizing adapts to confidence levels")
        print("  5. Data-driven decisions outperform simple rule-based systems")

        print("\nNext Steps:")
        print("  • Integrate RAG agents into your main trading workflow")
        print("  • Monitor performance and compare with/without RAG")
        print("  • Adjust confidence thresholds based on your risk tolerance")
        print("  • Continuously update historical data for better accuracy")

    except Exception as e:
        logger.exception("Example execution failed:")
        print(f"\n[FAIL] Error: {e}")

    print("\n" + "=" * 80)
