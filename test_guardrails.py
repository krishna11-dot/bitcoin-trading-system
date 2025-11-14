"""Simple test for guardrails without emoji issues."""

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
print(" Guardrails Safety Checks - Test")
print("=" * 70)

# Create test data
decision = TradeDecision(
    action="buy",
    amount=0.02,  # 0.02 BTC
    entry_price=105000.0,
    confidence=0.85,
    reasoning="Test buy decision for guardrails",
    timestamp=datetime.now().isoformat(),
    strategy="dca",
)

portfolio = PortfolioState(
    btc_balance=0.5,
    usd_balance=10000.0,
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

print("\nTest Data:")
print(f"  Decision: {decision.action} {decision.amount} BTC")
print(f"  Position Value: ${decision.amount * decision.entry_price:.2f} USD")
print(f"  Portfolio: ${portfolio.usd_balance:.2f} USD, {portfolio.btc_balance} BTC")
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
else:
    print("\nNo errors - all guardrails passed!")

print("\n" + "=" * 70)

if result_decision.action != "hold":
    print("SUCCESS: Trade approved by guardrails")
    exit(0)
else:
    print("BLOCKED: Trade blocked by guardrails")
    exit(1)
