"""Simple example of running a single trading cycle.

This demonstrates the basic usage of the HYBRID LangGraph trading workflow.
"""

import asyncio
import logging

from graph import run_trading_cycle

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def main():
    """Run a single trading cycle and display results."""

    print("\n" + "=" * 70)
    print(" Bitcoin Trading System - Single Cycle Example")
    print("=" * 70)

    # Configure trading parameters
    config = {
        "dca_threshold": 3.0,  # Trigger DCA buy on 3% price drop
        "dca_amount": 100,  # Buy $100 worth of BTC per DCA
        "atr_multiplier": 1.5,  # Stop-loss at entry - 1.5 * ATR
        "max_position_size": 0.20,  # Max 20% of portfolio per trade
        "max_total_exposure": 0.80,  # Max 80% total BTC exposure
        "emergency_stop": 0.25,  # Emergency stop at 25% portfolio loss
    }

    print("\n Configuration:")
    print(f"  DCA Threshold: {config['dca_threshold']}% price drop")
    print(f"  DCA Amount: ${config['dca_amount']} per buy")
    print(f"  Max Position Size: {config['max_position_size']:.0%} of portfolio")

    print("\n[STARTING] Running trading cycle...")
    print("-" * 70)

    # Run workflow
    result = await run_trading_cycle(config)

    # Display results
    print("\n" + "=" * 70)
    print(" Results")
    print("=" * 70)

    # Market data
    market_data = result.get("market_data")
    if market_data:
        print(f"\n Market:")
        print(f"  Price: ${market_data.price:,.2f}")
        print(f"  24h Change: {market_data.change_24h:+.2f}%")
        print(f"  Volume: ${market_data.volume / 1e9:.1f}B")

    # Market analysis
    market_analysis = result.get("market_analysis")
    if market_analysis:
        print(f"\n[DATA] Market Analysis:")
        print(f"  Trend: {market_analysis['trend'].upper()}")
        print(f"  Confidence: {market_analysis['confidence']:.0%}")
        print(f"  Risk Level: {market_analysis['risk_level'].upper()}")

    # Sentiment analysis
    sentiment_analysis = result.get("sentiment_analysis")
    if sentiment_analysis:
        print(f"\n[SENTIMENT] Sentiment:")
        print(f"  Sentiment: {sentiment_analysis['sentiment'].upper()}")
        print(f"  Crowd Psychology: {sentiment_analysis['crowd_psychology'].upper()}")

    # Risk assessment
    risk_assessment = result.get("risk_assessment")
    if risk_assessment:
        print(f"\n[WARN] Risk Assessment:")
        print(f"  Recommended Position: ${risk_assessment['recommended_position_usd']:,.2f}")
        print(f"  Stop-Loss: ${risk_assessment['stop_loss_price']:,.2f}")
        print(f"  Approved: {'[OK]' if risk_assessment['approved'] else '[FAIL]'}")

    # Final decision
    decision = result.get("trade_decision")
    if decision:
        print(f"\n[FINANCIAL] Trading Decision:")
        print(f"  Action: {decision.action.upper()}")
        print(f"  Amount: ${decision.amount:.2f}")
        print(f"  Entry Price: ${decision.entry_price:,.2f}")
        print(f"  Confidence: {decision.confidence:.0%}")
        print(f"  Reasoning: {decision.reasoning}")

    # Errors
    errors = result.get("errors", [])
    if errors:
        print(f"\n[WARN] Errors:")
        for error in errors:
            print(f"  - {error}")

    print("\n" + "=" * 70)

    # Next steps
    if decision and decision.action == "buy":
        print("\n[OK] Next Step: Execute buy order via Binance API")
        print(f"   Buy ${decision.amount:.2f} BTC at ${decision.entry_price:,.2f}")
    elif decision and decision.action == "hold":
        print("\n⏸ Next Step: Hold position, wait for next cycle")
    else:
        print("\n[WARN] Next Step: Review errors and retry")

    print()


if __name__ == "__main__":
    asyncio.run(main())
