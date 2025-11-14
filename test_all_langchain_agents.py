"""Comprehensive test script for all LangChain agents.

Tests all 4 LangChain-based trading agents:
1. Market Analysis Agent
2. Sentiment Analysis Agent
3. DCA Decision Agent
4. Risk Assessment Agent
"""

import logging

from agents import (
    analyze_market,
    analyze_sentiment,
    assess_risk,
    make_dca_decision,
)
from data_models import (
    MarketData,
    PortfolioState,
    SentimentData,
    TechnicalIndicators,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_market_analysis():
    """Test Market Analysis Agent."""
    print_section("TEST 1: Market Analysis Agent")

    # Bullish market scenario
    market_data = MarketData(
        price=106000.0,
        volume=28000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=3.5,
        high_24h=107000.0,
        low_24h=102000.0,
    )

    indicators = TechnicalIndicators(
        rsi_14=68.5,
        macd=1250.5,
        macd_signal=1180.2,
        macd_histogram=70.3,
        atr_14=1500.0,
        sma_50=103500.0,
        ema_12=105800.0,
        ema_26=104200.0,
    )

    print(f"\n[DATA] Market Data:")
    print(f"  Price: ${market_data.price:,.2f} ({market_data.change_24h:+.2f}%)")
    print(f"  Volume: ${market_data.volume / 1e9:.1f}B")
    print(f"  RSI: {indicators.rsi_14:.1f}")

    print(f"\n[SYSTEM] Calling Market Analysis Agent...")

    try:
        result = analyze_market(market_data, indicators)

        print(f"\n[OK] Result:")
        print(f"  Trend: {result['trend'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Risk Level: {result['risk_level'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

        # Validate
        assert result["trend"] in ["bullish", "bearish", "neutral"]
        assert 0 <= result["confidence"] <= 1
        assert result["risk_level"] in ["low", "medium", "high"]

        print("\n[OK] Market Analysis Test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Market Analysis Test FAILED: {e}")
        return False


def test_sentiment_analysis():
    """Test Sentiment Analysis Agent."""
    print_section("TEST 2: Sentiment Analysis Agent")

    # Fear scenario
    sentiment_data = SentimentData(
        fear_greed_index=35,  # Fear
        social_volume="high",
        news_sentiment=-0.2,
        timestamp="2025-01-10T12:00:00Z",
    )

    market_data = MarketData(
        price=102000.0,
        volume=32000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=-4.2,
        high_24h=107000.0,
        low_24h=101500.0,
    )

    indicators = TechnicalIndicators(
        rsi_14=32.5,
        macd=-850.5,
        macd_signal=-780.2,
        macd_histogram=-70.3,
        atr_14=2100.0,
        sma_50=105500.0,
        ema_12=103200.0,
        ema_26=104800.0,
    )

    print(f"\n[DATA] Sentiment Data:")
    print(f"  Fear/Greed Index: {sentiment_data.fear_greed_index}")
    print(f"  Social Volume: {sentiment_data.social_volume}")
    print(f"  News Sentiment: {sentiment_data.news_sentiment:+.2f}")

    print(f"\n[SYSTEM] Calling Sentiment Analysis Agent...")

    try:
        result = analyze_sentiment(sentiment_data, market_data, indicators)

        print(f"\n[OK] Result:")
        print(f"  Sentiment: {result['sentiment'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Crowd Psychology: {result['crowd_psychology'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

        # Validate
        assert result["sentiment"] in ["bullish", "bearish", "neutral"]
        assert 0 <= result["confidence"] <= 1
        assert result["crowd_psychology"] in ["fear", "greed", "neutral"]

        print("\n[OK] Sentiment Analysis Test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Sentiment Analysis Test FAILED: {e}")
        return False


def test_dca_decision():
    """Test DCA Decision Agent."""
    print_section("TEST 3: DCA Decision Agent")

    # DCA opportunity (price drop)
    market_data = MarketData(
        price=102000.0,
        volume=32000000000.0,
        timestamp="2025-01-10T14:00:00Z",
        change_24h=-4.2,  # Triggers DCA threshold
        high_24h=107000.0,
        low_24h=101500.0,
    )

    indicators = TechnicalIndicators(
        rsi_14=32.5,  # Oversold
        macd=-850.5,
        macd_signal=-780.2,
        macd_histogram=-70.3,
        atr_14=2100.0,
        sma_50=105500.0,
        ema_12=103200.0,
        ema_26=104800.0,
    )

    portfolio = PortfolioState(
        btc_balance=0.5,
        usd_balance=5000.0,
        active_positions=[],
        last_updated="2025-01-10T14:00:00Z",
    )

    state = {
        "market_data": market_data,
        "indicators": indicators,
        "portfolio_state": portfolio,
        "config": {"dca_threshold": 3.0, "dca_amount": 100},
        "market_analysis": {"trend": "bearish"},
        "sentiment_analysis": {"sentiment": "fear"},
        "rag_patterns": {
            "similar_patterns": 5,
            "success_rate": 0.75,
            "avg_outcome": 5.2,
        },
    }

    print(f"\n[DATA] Market Conditions:")
    print(
        f"  Price: ${market_data.price:,.2f} ({market_data.change_24h:+.2f}%) - Triggers DCA"
    )
    print(f"  RSI: {indicators.rsi_14:.1f} (oversold)")
    print(f"  USD Balance: ${portfolio.usd_balance:,.2f}")

    print(f"\n[SYSTEM] Calling DCA Decision Agent...")

    try:
        decision = make_dca_decision(state)

        print(f"\n[OK] Result:")
        print(f"  Action: {decision.action.upper()}")
        print(f"  Amount: ${decision.amount:.2f}")
        print(f"  Entry Price: ${decision.entry_price:,.2f}")
        print(f"  Confidence: {decision.confidence:.2%}")
        print(f"  Strategy: {decision.strategy.upper()}")
        print(f"  Reasoning: {decision.reasoning}")

        # Validate
        assert decision.action in ["buy", "hold"]
        assert decision.amount >= 0
        assert decision.strategy == "dca"

        print("\n[OK] DCA Decision Test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] DCA Decision Test FAILED: {e}")
        return False


def test_risk_assessment():
    """Test Risk Assessment Agent."""
    print_section("TEST 4: Risk Assessment Agent")

    portfolio = PortfolioState(
        btc_balance=0.5,
        usd_balance=10000.0,
        active_positions=[],
        last_updated="2025-01-10T14:00:00Z",
    )

    market_data = MarketData(
        price=106000.0,
        volume=28000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=3.5,
        high_24h=107000.0,
        low_24h=102000.0,
    )

    indicators = TechnicalIndicators(
        rsi_14=68.5,
        macd=1250.5,
        macd_signal=1180.2,
        macd_histogram=70.3,
        atr_14=1500.0,
        sma_50=103500.0,
        ema_12=105800.0,
        ema_26=104200.0,
    )

    config = {
        "atr_multiplier": 1.5,
        "max_position_size": 0.20,
        "max_total_exposure": 0.80,
        "emergency_stop": 0.25,
    }

    market_analysis = {"trend": "bullish", "confidence": 0.85}

    # Calculate total value
    btc_value = portfolio.btc_balance * market_data.price
    total_value = btc_value + portfolio.usd_balance

    print(f"\n[DATA] Portfolio State:")
    print(f"  BTC Balance: {portfolio.btc_balance} BTC (${btc_value:,.2f})")
    print(f"  USD Balance: ${portfolio.usd_balance:,.2f}")
    print(f"  Total Value: ${total_value:,.2f}")

    print(f"\n[ANALYSIS] Market Conditions:")
    print(f"  Price: ${market_data.price:,.2f}")
    print(f"  ATR (14): ${indicators.atr_14:.2f}")

    print(f"\n[SYSTEM] Calling Risk Assessment Agent...")

    try:
        result = assess_risk(portfolio, market_data, indicators, config, market_analysis)

        print(f"\n[OK] Result:")
        print(f"  Recommended Position: ${result['recommended_position_usd']:,.2f}")
        print(f"  Stop-Loss Price: ${result['stop_loss_price']:,.2f}")
        print(f"  Risk Percentage: {result['risk_percent']:.2f}%")
        print(f"  Approved: {result['approved']}")
        print(f"  Reasoning: {result['reasoning']}")

        # Validate
        assert result["recommended_position_usd"] >= 0
        assert result["stop_loss_price"] >= 0
        assert 0 <= result["risk_percent"] <= 100
        assert isinstance(result["approved"], bool)

        print("\n[OK] Risk Assessment Test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Risk Assessment Test FAILED: {e}")
        return False


def main():
    """Run all agent tests."""
    print_section("LangChain Agents - Comprehensive Testing")

    results = {
        "Market Analysis": test_market_analysis(),
        "Sentiment Analysis": test_sentiment_analysis(),
        "DCA Decision": test_dca_decision(),
        "Risk Assessment": test_risk_assessment(),
    }

    # Print summary
    print_section("TEST SUMMARY")

    for agent_name, passed in results.items():
        status = "[OK] PASSED" if passed else "[FAIL] FAILED"
        print(f"  {agent_name}: {status}")

    total = len(results)
    passed_count = sum(results.values())

    print(f"\n  Total: {passed_count}/{total} tests passed")

    if passed_count == total:
        print("\n ALL TESTS PASSED! All LangChain agents working correctly.")
        return 0
    else:
        print(f"\n[WARN] {total - passed_count} test(s) failed. Check logs above.")
        return 1


if __name__ == "__main__":
    exit(main())
