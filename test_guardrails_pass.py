"""Test guardrails with a portfolio that should pass all checks."""

import logging
from datetime import datetime

from data_models.decisions import TradeDecision
from data_models.market_data import MarketData
from data_models.portfolio import PortfolioState
from guardrails import run_all_guardrails

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

print("=" * 70)
print(" Guardrails Test - Should PASS All Checks")
print("=" * 70)

# Create test data with lower BTC exposure
decision = TradeDecision(
    action="buy",
    amount=0.01,  # Small position: 0.01 BTC
    entry_price=105000.0,
    confidence=0.85,
    reasoning="Test buy decision - should pass all guardrails",
    timestamp=datetime.now().isoformat(),
    strategy="dca",
)

# Portfolio with lower BTC exposure (only 0.1 BTC instead of 0.5)
portfolio = PortfolioState(
    btc_balance=0.1,  # Lower BTC balance to keep exposure under 80%
    usd_balance=50000.0,  # More USD
    active_positions=[],
    last_updated=datetime.now().isoformat(),
)

market_data = MarketData(
    price=106000.0,
    volume=25000000000.0,
    timestamp=datetime.now().isoformat(),
    change_24h=2.5,
    high_24h=107000.0,
    low_24h=105000.0,
)

config = {
    "max_position_size": 0.20,
    "max_total_exposure": 0.80,
    "emergency_stop": 0.25,
    "max_trades_per_hour": 5,
}

state = {
    "trade_decision": decision,
    "portfolio_state": portfolio,
    "market_data": market_data,
    "config": config,
    "errors": [],
}

# Calculate exposure
btc_value = portfolio.btc_balance * decision.entry_price
total_value = portfolio.usd_balance + btc_value
current_exposure = btc_value / total_value if total_value > 0 else 0

print("\nTest Data:")
print(f"  Decision: {decision.action} {decision.amount} BTC")
print(f"  Position Value: ${decision.amount * decision.entry_price:,.2f} USD")
print(f"  Portfolio: ${portfolio.usd_balance:,.2f} USD, {portfolio.btc_balance} BTC")
print(f"  BTC Value: ${btc_value:,.2f}")
print(f"  Total Value: ${total_value:,.2f}")
print(f"  Current BTC Exposure: {current_exposure:.1%}")
print(f"  Market Price: ${market_data.price:,.2f}")

print("\nRunning guardrails...")
print("-" * 70)

result_state = run_all_guardrails(state)

print("\nResult:")
result_decision = result_state["trade_decision"]
print(f"  Action: {result_decision.action.upper()}")
print(f"  Amount: {result_decision.amount} BTC")
print(f"  Reasoning: {result_decision.reasoning}")

if result_state.get("errors"):
    print(f"\nErrors ({len(result_state['errors'])}):")
    for error in result_state["errors"]:
        print(f"  - {error}")
    print("\nFAILED: Trade blocked by guardrails")
    exit(1)
else:
    print("\nSUCCESS: All guardrails passed! Trade approved.")
    exit(0)
