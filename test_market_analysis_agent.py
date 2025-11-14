"""Test script for Market Analysis Agent with LangChain.

Tests the LangChain-based market analysis agent with real market data.
"""

import logging
from agents.market_analysis_agent import analyze_market
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    """Test market analysis agent with sample data."""
    print("=" * 70)
    print("Testing LangChain Market Analysis Agent")
    print("=" * 70)

    # Create sample bullish market scenario
    print("\n[DATA] Test Scenario: Bullish Market")
    print("-" * 70)

    market_data = MarketData(
        price=106000.0,
        volume=28000000000.0,  # 28B volume
        timestamp="2025-01-10T12:00:00Z",
        change_24h=3.5,  # Strong positive change
        high_24h=107000.0,
        low_24h=102000.0,
    )

    indicators = TechnicalIndicators(
        rsi_14=68.5,  # Approaching overbought but not extreme
        macd=1250.5,
        macd_signal=1180.2,  # Bullish MACD crossover
        macd_histogram=70.3,  # Positive histogram
        atr_14=1500.0,
        sma_50=103500.0,  # Price above SMA
        ema_12=105800.0,  # Bullish EMA arrangement
        ema_26=104200.0,
    )

    print(f"Price: ${market_data.price:,.2f} ({market_data.change_24h:+.2f}%)")
    print(f"Volume: ${market_data.volume / 1e9:.1f}B")
    print(f"RSI: {indicators.rsi_14:.1f}")
    print(f"MACD: {indicators.macd:.1f} (Signal: {indicators.macd_signal:.1f})")

    print("\n[SYSTEM] Analyzing market with LangChain agent...")

    try:
        result = analyze_market(market_data, indicators)

        print("\n[OK] Analysis Result:")
        print(f"  Trend: {result['trend'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Risk Level: {result['risk_level'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

        # Validate result structure
        assert result['trend'] in ['bullish', 'bearish', 'neutral']
        assert 0 <= result['confidence'] <= 1
        assert result['risk_level'] in ['low', 'medium', 'high']
        assert len(result['reasoning']) > 0

        print("\n[OK] All validations passed!")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)

    # Test bearish scenario
    print("\n[DATA] Test Scenario: Bearish Market")
    print("-" * 70)

    market_data_bearish = MarketData(
        price=102000.0,
        volume=32000000000.0,
        timestamp="2025-01-10T14:00:00Z",
        change_24h=-4.2,  # Strong negative change
        high_24h=107000.0,
        low_24h=101500.0,
    )

    indicators_bearish = TechnicalIndicators(
        rsi_14=32.5,  # Oversold
        macd=-850.5,
        macd_signal=-780.2,  # Bearish MACD
        macd_histogram=-70.3,  # Negative histogram
        atr_14=2100.0,  # High volatility
        sma_50=105500.0,  # Price below SMA
        ema_12=103200.0,
        ema_26=104800.0,  # Bearish EMA arrangement
    )

    print(f"Price: ${market_data_bearish.price:,.2f} ({market_data_bearish.change_24h:+.2f}%)")
    print(f"RSI: {indicators_bearish.rsi_14:.1f}")
    print(f"MACD: {indicators_bearish.macd:.1f}")

    print("\n[SYSTEM] Analyzing bearish market...")

    try:
        result = analyze_market(market_data_bearish, indicators_bearish)

        print("\n[OK] Analysis Result:")
        print(f"  Trend: {result['trend'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Risk Level: {result['risk_level'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("[OK] Market Analysis Agent Testing Complete!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
