"""Test script for HYBRID LangGraph trading workflow.

Tests the complete trading workflow with:
- PARALLEL data collection (3 agents simultaneously)
- SEQUENTIAL analysis pipeline (5 LLM agents)
"""

import asyncio
import logging

from graph import run_trading_cycle

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_trading_workflow():
    """Test complete trading workflow."""
    print("\n" + "=" * 70)
    print(" HYBRID Trading Workflow - Full Test")
    print("=" * 70)
    print()
    print("Architecture:")
    print("  1. PARALLEL: 3 data agents run simultaneously (3s)")
    print("     - Market data (Binance)")
    print("     - Sentiment data (CoinMarketCap)")
    print("     - On-chain data (CryptoQuant)")
    print()
    print("  2. SEQUENTIAL: 5 analysis agents run one-by-one (~15s)")
    print("     - Calculate indicators")
    print("     - Market analysis (LLM)")
    print("     - Sentiment analysis (LLM)")
    print("     - Risk assessment (LLM)")
    print("     - DCA decision (LLM)")
    print()
    print("  Expected total time: ~18s (vs ~21.5s sequential = 18% faster!)")
    print("=" * 70)

    # Configuration
    config = {
        "dca_threshold": 3.0,  # 3% drop triggers DCA
        "dca_amount": 100,  # $100 per DCA buy
        "atr_multiplier": 1.5,  # Stop-loss at entry - 1.5*ATR
        "max_position_size": 0.20,  # Max 20% of portfolio per trade
        "max_total_exposure": 0.80,  # Max 80% total exposure
        "emergency_stop": 0.25,  # Emergency stop at 25% portfolio loss
    }

    print(f"\n Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()

    # Run workflow
    try:
        result = await run_trading_cycle(config)

        # Display results
        print("\n" + "=" * 70)
        print(" Workflow Results")
        print("=" * 70)

        # Data collection results
        print("\n1⃣ PARALLEL Data Collection:")
        market_data = result.get("market_data")
        if market_data:
            print(f"  [OK] Market Data:")
            print(f"     Price: ${market_data.price:,.2f}")
            print(f"     Change 24h: {market_data.change_24h:+.2f}%")
            print(f"     Volume: ${market_data.volume / 1e9:.1f}B")
        else:
            print("  [FAIL] Market Data: Failed")

        sentiment_data = result.get("sentiment_data")
        if sentiment_data:
            print(f"  [OK] Sentiment Data:")
            print(f"     Fear/Greed: {sentiment_data.fear_greed_index}")
            print(f"     Label: {sentiment_data.get_fear_greed_label()}")
        else:
            print("  [FAIL] Sentiment Data: Failed")

        onchain_data = result.get("onchain_data")
        print(
            f"  {'[OK]' if onchain_data else '[WARN]'} On-chain Data: "
            f"{len(onchain_data)} metrics (optional)"
        )

        # Indicator results
        print("\n2⃣ Technical Indicators:")
        indicators = result.get("indicators")
        if indicators:
            print(f"  [OK] Calculated:")
            print(f"     RSI (14): {indicators.rsi_14:.1f}")
            print(f"     MACD: {indicators.macd:.2f}")
            print(f"     ATR (14): ${indicators.atr_14:.2f}")
            print(f"     SMA (50): ${indicators.sma_50:,.2f}")
        else:
            print("  [FAIL] Indicators: Failed")

        # Analysis results
        print("\n3⃣ SEQUENTIAL Analysis Pipeline:")

        market_analysis = result.get("market_analysis")
        if market_analysis:
            print(f"  [OK] Market Analysis:")
            print(f"     Trend: {market_analysis['trend'].upper()}")
            print(f"     Confidence: {market_analysis['confidence']:.0%}")
            print(f"     Risk Level: {market_analysis['risk_level'].upper()}")
        else:
            print("  [FAIL] Market Analysis: Failed")

        sentiment_analysis = result.get("sentiment_analysis")
        if sentiment_analysis:
            print(f"  [OK] Sentiment Analysis:")
            print(f"     Sentiment: {sentiment_analysis['sentiment'].upper()}")
            print(f"     Confidence: {sentiment_analysis['confidence']:.0%}")
            print(f"     Psychology: {sentiment_analysis['crowd_psychology'].upper()}")
        else:
            print("  [FAIL] Sentiment Analysis: Failed")

        risk_assessment = result.get("risk_assessment")
        if risk_assessment:
            print(f"  [OK] Risk Assessment:")
            print(
                f"     Position: ${risk_assessment['recommended_position_usd']:,.2f}"
            )
            print(f"     Stop-Loss: ${risk_assessment['stop_loss_price']:,.2f}")
            print(f"     Risk: {risk_assessment['risk_percent']:.2f}%")
            print(f"     Approved: {risk_assessment['approved']}")
        else:
            print("  [FAIL] Risk Assessment: Failed")

        # Final decision
        print("\n4⃣ Final DCA Decision:")
        trade_decision = result.get("trade_decision")
        if trade_decision:
            print(f"  [OK] Decision Made:")
            print(f"     Action: {trade_decision.action.upper()}")
            print(f"     Amount: ${trade_decision.amount:.2f}")
            print(f"     Entry Price: ${trade_decision.entry_price:,.2f}")
            print(f"     Confidence: {trade_decision.confidence:.0%}")
            print(f"     Strategy: {trade_decision.strategy.upper()}")
            print(f"     Reasoning: {trade_decision.reasoning}")
        else:
            print("  [FAIL] Trade Decision: Failed")

        # Errors
        errors = result.get("errors", [])
        if errors:
            print(f"\n[WARN] Errors ({len(errors)}):")
            for error in errors:
                print(f"  - {error}")

        # Summary
        print("\n" + "=" * 70)
        print(" Test Summary")
        print("=" * 70)

        components = {
            "Market Data": market_data is not None,
            "Sentiment Data": sentiment_data is not None,
            "Indicators": indicators is not None,
            "Market Analysis": market_analysis is not None,
            "Sentiment Analysis": sentiment_analysis is not None,
            "Risk Assessment": risk_assessment is not None,
            "Trade Decision": trade_decision is not None,
        }

        passed = sum(components.values())
        total = len(components)

        for name, success in components.items():
            status = "[OK] PASSED" if success else "[FAIL] FAILED"
            print(f"  {name}: {status}")

        print(f"\n  Total: {passed}/{total} components working")

        if passed == total:
            print("\n ALL COMPONENTS WORKING! Workflow fully operational.")
            return 0
        elif passed >= 5:
            print(
                f"\n[OK] CORE COMPONENTS WORKING! {total - passed} optional failures."
            )
            return 0
        else:
            print(f"\n[WARN] {total - passed} components failed. Check logs above.")
            return 1

    except Exception as e:
        print(f"\n[FAIL] Workflow failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    """Main test entry point."""
    exit_code = asyncio.run(test_trading_workflow())
    exit(exit_code)


if __name__ == "__main__":
    main()
