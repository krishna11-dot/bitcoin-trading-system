"""Test the Strategy Switcher with different market scenarios."""

import logging
from tools.strategy_switcher import StrategySwitcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_crisis_market():
    """Test strategy selection during a market crisis."""
    logger.info("=" * 80)
    logger.info("TEST 1: CRISIS MARKET (High Fear, High Volatility)")
    logger.info("=" * 80)

    switcher = StrategySwitcher()

    # Simulate crisis: high fear, dropping price, high volatility
    market_data = {
        "current_price": 58000,
        "price_24h_ago": 65000,  # -10.8% drop
        "price_7d_ago": 68000,
        "volume_24h": 45_000_000_000,  # High volume
        "market_cap": 1_140_000_000_000,
    }

    indicators = {
        "rsi": 28,  # Oversold
        "macd": -850,  # Bearish
        "macd_signal": -600,
        "bb_upper": 62000,
        "bb_middle": 60000,
        "bb_lower": 58000,
        "atr": 2800,  # High volatility
        "adx": 45,  # Strong trend
        "obv": -5_000_000,  # Negative
        "sma_50": 61000,  # Above current price (bearish)
    }

    sentiment_data = {
        "fear_greed_index": 18,  # Extreme fear
        "sentiment_score": -0.65,  # Very negative
    }

    onchain_data = {
        "hash_rate": {"hash_rate_ehs": 580},
        "mempool": {"tx_count": 85000},  # High congestion
        "block_metrics": {"latest_block_size_mb": 2.1},
    }

    result = switcher.analyze_and_recommend(
        market_data, indicators, sentiment_data, onchain_data
    )

    logger.info(f"\nMarket Regime: {result['market_regime']}")
    logger.info(f"Selected Strategy: {result['strategy']}")
    logger.info(f"Confidence: {result['confidence']:.1%}")
    logger.info(f"Adaptive DCA Trigger: {result['adaptive_dca_trigger']:.1f}%")
    logger.info(f"Position Size: {result['position_size_pct']:.1f}%")

    logger.info("\nTop 3 Features Selected:")
    for feat, val in result["selected_features"].items():
        logger.info(f"  {feat}: {val:.3f}")

    logger.info("\nRationale:")
    logger.info(f"  {result['switch_reason']}")

    assert result["strategy"] in ["dca", "swing", "day"], "Invalid strategy"
    logger.info("\n[PASS] Crisis market test completed\n")


def test_bull_trend():
    """Test strategy selection during a bull trend."""
    logger.info("=" * 80)
    logger.info("TEST 2: BULL TREND (Strong Uptrend, Positive Momentum)")
    logger.info("=" * 80)

    switcher = StrategySwitcher()

    # Simulate bull trend: greed, rising price, moderate volatility
    market_data = {
        "current_price": 72000,
        "price_24h_ago": 70500,  # +2.1% gain
        "price_7d_ago": 68000,  # +5.9% gain
        "volume_24h": 38_000_000_000,
        "market_cap": 1_420_000_000_000,
    }

    indicators = {
        "rsi": 68,  # Bullish but not overbought
        "macd": 420,  # Bullish
        "macd_signal": 280,
        "bb_upper": 74000,
        "bb_middle": 71000,
        "bb_lower": 68000,
        "atr": 1200,  # Moderate volatility
        "adx": 38,  # Trending
        "obv": 8_500_000,  # Positive
        "sma_50": 69500,  # Below current price (bullish)
    }

    sentiment_data = {
        "fear_greed_index": 72,  # Greed
        "sentiment_score": 0.55,  # Positive
    }

    onchain_data = {
        "hash_rate": {"hash_rate_ehs": 625},
        "mempool": {"tx_count": 45000},
        "block_metrics": {"latest_block_size_mb": 1.8},
    }

    result = switcher.analyze_and_recommend(
        market_data, indicators, sentiment_data, onchain_data
    )

    logger.info(f"\nMarket Regime: {result['market_regime']}")
    logger.info(f"Selected Strategy: {result['strategy']}")
    logger.info(f"Confidence: {result['confidence']:.1%}")
    logger.info(f"Adaptive DCA Trigger: {result['adaptive_dca_trigger']:.1f}%")
    logger.info(f"Position Size: {result['position_size_pct']:.1f}%")

    logger.info("\nTop 3 Features Selected:")
    for feat, val in result["selected_features"].items():
        logger.info(f"  {feat}: {val:.3f}")

    logger.info("\nRationale:")
    logger.info(f"  {result['switch_reason']}")

    assert result["strategy"] in ["dca", "swing", "day"], "Invalid strategy"
    logger.info("\n[PASS] Bull trend test completed\n")


def test_high_volatility():
    """Test strategy selection during high volatility choppy market."""
    logger.info("=" * 80)
    logger.info("TEST 3: HIGH VOLATILITY (Choppy Market, No Clear Trend)")
    logger.info("=" * 80)

    switcher = StrategySwitcher()

    # Simulate choppy market: neutral sentiment, high volatility, no trend
    market_data = {
        "current_price": 65000,
        "price_24h_ago": 64800,  # +0.3% (flat)
        "price_7d_ago": 65500,  # -0.8% (flat)
        "volume_24h": 42_000_000_000,
        "market_cap": 1_280_000_000_000,
    }

    indicators = {
        "rsi": 52,  # Neutral
        "macd": -45,  # Weak signal
        "macd_signal": -30,
        "bb_upper": 68000,
        "bb_middle": 65000,
        "bb_lower": 62000,
        "atr": 3200,  # Very high volatility
        "adx": 22,  # Weak trend
        "obv": 1_200_000,  # Slightly positive
        "sma_50": 65200,  # Near current price (neutral)
    }

    sentiment_data = {
        "fear_greed_index": 48,  # Neutral
        "sentiment_score": 0.05,  # Neutral
    }

    onchain_data = {
        "hash_rate": {"hash_rate_ehs": 605},
        "mempool": {"tx_count": 55000},
        "block_metrics": {"latest_block_size_mb": 1.9},
    }

    result = switcher.analyze_and_recommend(
        market_data, indicators, sentiment_data, onchain_data
    )

    logger.info(f"\nMarket Regime: {result['market_regime']}")
    logger.info(f"Selected Strategy: {result['strategy']}")
    logger.info(f"Confidence: {result['confidence']:.1%}")
    logger.info(f"Adaptive DCA Trigger: {result['adaptive_dca_trigger']:.1f}%")
    logger.info(f"Position Size: {result['position_size_pct']:.1f}%")

    logger.info("\nTop 3 Features Selected:")
    for feat, val in result["selected_features"].items():
        logger.info(f"  {feat}: {val:.3f}")

    logger.info("\nRationale:")
    logger.info(f"  {result['switch_reason']}")

    assert result["strategy"] in ["dca", "swing", "day"], "Invalid strategy"
    logger.info("\n[PASS] High volatility test completed\n")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("STRATEGY SWITCHER TEST SUITE")
    logger.info("=" * 80 + "\n")

    try:
        test_crisis_market()
        test_bull_trend()
        test_high_volatility()

        logger.info("=" * 80)
        logger.info("[SUCCESS] All tests passed")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"\n[FAIL] Test failed: {e}")
        logger.exception("Error details:")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
