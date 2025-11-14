"""Pre-execution safety checks (Guardrails).

This module implements guardrails that run AFTER decision-making but BEFORE
trade execution. These are the last line of defense against bad trades.

Guardrails block trades by changing the action to "hold" if ANY check fails.
They never crash - they just block trades and log why.

Example:
    >>> from guardrails import run_all_guardrails
    >>> state = {
    ...     "trade_decision": TradeDecision(action="buy", amount=1000, ...),
    ...     "portfolio_state": portfolio,
    ...     "config": config,
    ...     "market_data": market_data
    ... }
    >>> state = run_all_guardrails(state)
    >>> if state["trade_decision"].action == "hold":
    ...     print("Trade blocked by guardrails")
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from data_models.decisions import TradeDecision
from data_models.market_data import MarketData
from data_models.portfolio import PortfolioState

# Configure logger
logger = logging.getLogger(__name__)

# Global trade tracking (in-memory for trade frequency check)
RECENT_TRADES: List[datetime] = []


# ============================================================================
# INDIVIDUAL SAFETY CHECKS
# ============================================================================


def check_sufficient_balance(
    decision: TradeDecision, portfolio: PortfolioState
) -> Tuple[bool, str]:
    """Check if sufficient balance exists for the trade.

    For buy orders: Checks if USD balance >= trade value (amount * entry_price)
    For sell orders: Checks if BTC balance >= amount
    For hold: Always passes

    Args:
        decision: Trade decision with action and amount (in BTC)
        portfolio: Current portfolio state with balances

    Returns:
        Tuple[bool, str]: (passed, message) where:
            - passed: True if check passes, False if fails
            - message: Explanation of check result

    Example:
        >>> decision = TradeDecision(action="buy", amount=0.05, entry_price=50000, ...)
        >>> portfolio = PortfolioState(usd_balance=2000, ...)
        >>> passed, msg = check_sufficient_balance(decision, portfolio)
        >>> print(passed, msg)
        False Insufficient USD: need $2500.00, have $2000.00
    """
    if decision.action == "hold":
        return True, "Hold - no balance check needed"

    if decision.action == "buy":
        # Calculate USD needed for the BTC purchase
        usd_needed = decision.amount * decision.entry_price

        if portfolio.usd_balance >= usd_needed:
            return (
                True,
                f"Sufficient USD: ${portfolio.usd_balance:.2f} >= ${usd_needed:.2f}",
            )
        else:
            return (
                False,
                f"Insufficient USD: need ${usd_needed:.2f}, have ${portfolio.usd_balance:.2f}",
            )

    elif decision.action == "sell":
        # Check if we have enough BTC to sell
        if portfolio.btc_balance >= decision.amount:
            return (
                True,
                f"Sufficient BTC: {portfolio.btc_balance:.4f} >= {decision.amount:.4f}",
            )
        else:
            return (
                False,
                f"Insufficient BTC: need {decision.amount:.4f}, have {portfolio.btc_balance:.4f}",
            )

    return True, "Unknown action"


def check_position_limits(
    decision: TradeDecision, portfolio: PortfolioState, config: Dict
) -> Tuple[bool, str]:
    """Check if position size is within configured limits.

    Position size must be <= max_position_size (e.g., 20% of total portfolio).
    This prevents over-concentration in a single trade.

    Args:
        decision: Trade decision with amount (in BTC)
        portfolio: Current portfolio state
        config: Configuration with max_position_size (default: 0.20)

    Returns:
        Tuple[bool, str]: (passed, message)

    Example:
        >>> decision = TradeDecision(action="buy", amount=0.1, entry_price=50000, ...)
        >>> portfolio = PortfolioState(usd_balance=10000, btc_balance=0, ...)
        >>> config = {"max_position_size": 0.20}
        >>> passed, msg = check_position_limits(decision, portfolio, config)
        >>> print(passed)
        False  # 5000/10000 = 50% > 20% limit
    """
    if decision.action == "hold":
        return True, "Hold - no position check needed"

    max_position_pct = config.get("max_position_size", 0.20)

    # Calculate total portfolio value in USD
    total_value = portfolio.usd_balance + (
        portfolio.btc_balance * decision.entry_price
    )

    if total_value <= 0:
        return False, "Cannot calculate position size: total portfolio value is zero"

    # Calculate position value in USD
    position_value_usd = decision.amount * decision.entry_price

    # Calculate position as percentage of total value
    position_pct = position_value_usd / total_value

    if position_pct <= max_position_pct:
        return (
            True,
            f"Position OK: {position_pct:.1%} <= {max_position_pct:.1%} limit",
        )
    else:
        return (
            False,
            f"Position too large: {position_pct:.1%} > {max_position_pct:.1%} limit",
        )


def check_total_exposure(
    portfolio: PortfolioState,
    config: Dict,
    current_btc_price: float,
    decision: TradeDecision = None,
) -> Tuple[bool, str]:
    """Check if total BTC exposure is within configured limits.

    Total BTC value must be <= max_total_exposure (e.g., 80% of portfolio).
    This prevents over-exposure to BTC volatility.

    CRITICAL FIX: Now calculates exposure AFTER the proposed trade executes,
    not just current exposure. This prevents trades that would push exposure
    over the limit.

    Args:
        portfolio: Current portfolio state
        config: Configuration with max_total_exposure (default: 0.80)
        current_btc_price: Current BTC price for valuation
        decision: Trade decision to simulate (optional)

    Returns:
        Tuple[bool, str]: (passed, message)

    Example:
        >>> portfolio = PortfolioState(btc_balance=1.0, usd_balance=10000, ...)
        >>> decision = TradeDecision(action="buy", amount=0.5, ...)
        >>> config = {"max_total_exposure": 0.80}
        >>> passed, msg = check_total_exposure(portfolio, config, 100000.0, decision)
        >>> # After trade: BTC = 1.5, USD = 10000 - 50000 = -40000 (insufficient!)
        >>> # But exposure calculation: (1.5 * 100000) / (1.5*100000 + (-40000))
        >>> print(passed)
        True or False (depending on calculation)
    """
    max_exposure_pct = config.get("max_total_exposure", 0.80)

    # Calculate portfolio value AFTER the proposed trade (if any)
    if decision and decision.action == "buy":
        # Simulate buy: Add BTC, subtract USD
        btc_after_trade = portfolio.btc_balance + decision.amount
        usd_after_trade = portfolio.usd_balance - (decision.amount * current_btc_price)
        logger.info(f"  [EXPOSURE DEBUG] Action=BUY, Amount={decision.amount:.8f} BTC (${decision.amount * current_btc_price:.2f})")
        logger.info(f"  [EXPOSURE DEBUG] Before: BTC={portfolio.btc_balance:.8f}, USD=${portfolio.usd_balance:.2f}")
        logger.info(f"  [EXPOSURE DEBUG] After: BTC={btc_after_trade:.8f}, USD=${usd_after_trade:.2f}")
    elif decision and decision.action == "sell":
        # Simulate sell: Subtract BTC, add USD
        btc_after_trade = portfolio.btc_balance - decision.amount
        usd_after_trade = portfolio.usd_balance + (decision.amount * current_btc_price)
    else:
        # No trade or hold: Use current balances
        btc_after_trade = portfolio.btc_balance
        usd_after_trade = portfolio.usd_balance

    # Calculate total portfolio value after trade
    btc_value = btc_after_trade * current_btc_price
    total_value = usd_after_trade + btc_value

    if total_value <= 0:
        return True, "No exposure - portfolio value is zero"

    # Calculate BTC exposure as percentage
    exposure_pct = btc_value / total_value
    logger.info(f"  [EXPOSURE DEBUG] Exposure={exposure_pct:.1%} (BTC value=${btc_value:.2f} / Total=${total_value:.2f})")

    if exposure_pct <= max_exposure_pct:
        return (
            True,
            f"Exposure OK: {exposure_pct:.1%} <= {max_exposure_pct:.1%} limit (after trade)",
        )
    else:
        return (
            False,
            f"Exposure too high: {exposure_pct:.1%} > {max_exposure_pct:.1%} limit (after trade)",
        )


def check_emergency_stop(portfolio: PortfolioState, config: Dict) -> Tuple[bool, str]:
    """Check if emergency stop-loss has been triggered.

    If portfolio loss >= emergency_stop threshold (e.g., 25%), block ALL trades.
    This is the nuclear option to prevent catastrophic losses.

    Args:
        portfolio: Current portfolio state with profit_loss_pct
        config: Configuration with emergency_stop (default: 0.25)

    Returns:
        Tuple[bool, str]: (passed, message)

    Example:
        >>> portfolio = PortfolioState(profit_loss_pct=-0.30, ...)  # -30% loss
        >>> config = {"emergency_stop": 0.25}  # 25% threshold
        >>> passed, msg = check_emergency_stop(portfolio, config)
        >>> print(passed)
        False  # Loss exceeds threshold
    """
    emergency_threshold = config.get("emergency_stop", 0.25)

    if portfolio.profit_loss_pct is not None:
        # Check if loss (negative P/L) exceeds threshold
        if portfolio.profit_loss_pct < 0:  # We have a loss
            loss_pct = abs(portfolio.profit_loss_pct)

            if loss_pct >= emergency_threshold:
                return (
                    False,
                    f"[ALERT] EMERGENCY STOP: Portfolio loss {loss_pct:.1%} >= {emergency_threshold:.1%}",
                )

    return True, "Emergency stop not triggered"


def check_trade_frequency(config: Dict) -> Tuple[bool, str]:
    """Check if trade frequency is within configured limits.

    Limits number of trades per hour (e.g., max 5 trades/hour).
    This prevents excessive trading and potential bugs.

    Uses global RECENT_TRADES list to track trades.

    Args:
        config: Configuration with max_trades_per_hour (default: 5)

    Returns:
        Tuple[bool, str]: (passed, message)

    Example:
        >>> # Assume 5 trades were made in last hour
        >>> config = {"max_trades_per_hour": 5}
        >>> passed, msg = check_trade_frequency(config)
        >>> print(passed)
        False  # Already at limit
    """
    global RECENT_TRADES

    max_trades = config.get("max_trades_per_hour", 5)
    one_hour_ago = datetime.now() - timedelta(hours=1)

    # Remove trades older than 1 hour
    RECENT_TRADES = [t for t in RECENT_TRADES if t > one_hour_ago]

    trades_last_hour = len(RECENT_TRADES)

    if trades_last_hour < max_trades:
        return (
            True,
            f"Trade frequency OK: {trades_last_hour}/{max_trades} trades in last hour",
        )
    else:
        return (
            False,
            f"Trade frequency exceeded: {trades_last_hour}/{max_trades} trades in last hour",
        )


def check_price_sanity(
    decision: TradeDecision, market_data: MarketData
) -> Tuple[bool, str]:
    """Check if entry price is within reasonable range of current market price.

    Entry price must be within 5% of current market price.
    This prevents trades with stale or incorrect prices.

    Args:
        decision: Trade decision with entry_price
        market_data: Current market data with current price

    Returns:
        Tuple[bool, str]: (passed, message)

    Example:
        >>> decision = TradeDecision(entry_price=100000, ...)
        >>> market_data = MarketData(price=110000, ...)  # 10% difference
        >>> passed, msg = check_price_sanity(decision, market_data)
        >>> print(passed)
        False  # Difference > 5%
    """
    if decision.action == "hold":
        return True, "Hold - no price check needed"

    current_price = market_data.price
    entry_price = decision.entry_price

    # Calculate absolute difference as percentage
    price_diff_pct = abs(entry_price - current_price) / current_price

    if price_diff_pct <= 0.05:  # Within 5%
        return (
            True,
            f"Price sane: Entry ${entry_price:,.2f} vs Market ${current_price:,.2f} ({price_diff_pct:.1%})",
        )
    else:
        return (
            False,
            f"Price check failed: Entry ${entry_price:,.2f} vs Market ${current_price:,.2f} ({price_diff_pct:.1%} difference)",
        )


# ============================================================================
# TRADE TRACKING
# ============================================================================


def record_trade():
    """Record a trade for frequency tracking.

    Should be called AFTER successful trade execution.
    Updates the global RECENT_TRADES list.

    Example:
        >>> # After successful trade execution
        >>> record_trade()
        >>> # Now trade frequency check will see this trade
    """
    global RECENT_TRADES
    RECENT_TRADES.append(datetime.now())
    logger.info(f"[NOTE] Trade recorded. Total in last hour: {len(RECENT_TRADES)}")


def get_recent_trades_count() -> int:
    """Get count of trades in last hour.

    Returns:
        int: Number of trades in last hour

    Example:
        >>> count = get_recent_trades_count()
        >>> print(f"Trades in last hour: {count}")
    """
    global RECENT_TRADES
    one_hour_ago = datetime.now() - timedelta(hours=1)
    RECENT_TRADES = [t for t in RECENT_TRADES if t > one_hour_ago]
    return len(RECENT_TRADES)


# ============================================================================
# MAIN GUARDRAILS FUNCTION
# ============================================================================


def run_all_guardrails(state: Dict) -> Dict:
    """Run ALL safety checks before trade execution.

    This is the main entry point for guardrails. It runs all safety checks
    and blocks the trade if ANY check fails.

    If any check fails:
    - Changes decision action to "hold"
    - Sets amount to 0
    - Updates reasoning with failure details
    - Adds failures to errors list
    - Logs everything

    Args:
        state: Trading state dict containing:
            - trade_decision: TradeDecision to validate
            - portfolio_state: Current portfolio
            - config: Trading configuration
            - market_data: Current market data
            - errors: List of errors (optional)

    Returns:
        Dict: Updated state with potentially modified trade_decision

    Example:
        >>> state = {
        ...     "trade_decision": TradeDecision(action="buy", amount=1000, ...),
        ...     "portfolio_state": portfolio,
        ...     "config": {"max_position_size": 0.20},
        ...     "market_data": market_data,
        ...     "errors": []
        ... }
        >>> state = run_all_guardrails(state)
        >>> if state["trade_decision"].action == "hold":
        ...     print("Trade blocked by guardrails")
    """
    decision = state.get("trade_decision")
    portfolio = state.get("portfolio_state")
    config = state.get("config", {})
    market_data = state.get("market_data")

    # Validate inputs
    if not decision:
        logger.warning("[WARN] No trade decision to check")
        return state

    if not portfolio:
        logger.warning("[WARN] No portfolio state - skipping guardrails")
        return state

    if not market_data:
        logger.warning("[WARN] No market data - skipping price sanity check")

    # If already hold, skip checks
    if decision.action == "hold":
        logger.info("[INFO] Decision is hold, skipping guardrails")
        return state

    logger.info("[SAFETY] Running guardrails (pre-execution safety checks)...")

    # Get current BTC price for exposure check
    current_btc_price = market_data.price if market_data else decision.entry_price

    # Run all checks
    checks = [
        ("Sufficient Balance", check_sufficient_balance(decision, portfolio)),
        ("Position Limits", check_position_limits(decision, portfolio, config)),
        (
            "Total Exposure",
            check_total_exposure(portfolio, config, current_btc_price, decision),
        ),
        ("Emergency Stop", check_emergency_stop(portfolio, config)),
        ("Trade Frequency", check_trade_frequency(config)),
    ]

    # Add price sanity check only if market_data is available
    if market_data:
        checks.append(("Price Sanity", check_price_sanity(decision, market_data)))

    # Log each check and collect failures
    failures = []
    for name, (passed, message) in checks:
        status = "[OK]" if passed else "[FAIL]"
        logger.info(f"  {status} {name}: {message}")

        if not passed:
            failures.append(f"{name}: {message}")

    # If any failed, block trade
    if failures:
        logger.warning(f" TRADE BLOCKED by guardrails ({len(failures)} checks failed)")
        for failure in failures:
            logger.warning(f"   - {failure}")

        # Change decision to hold
        original_action = decision.action
        original_amount = decision.amount

        decision.action = "hold"
        decision.amount = 0.0001  # Minimum valid amount (Pydantic requires amount > 0)
        decision.reasoning = (
            f"BLOCKED by guardrails (original: {original_action} ${original_amount:.2f}). "
            f"Failures: {'; '.join(failures)}"
        )

        # Add to errors list
        if "errors" not in state:
            state["errors"] = []

        for failure in failures:
            state["errors"].append(f"Guardrail: {failure}")

        logger.info(f"[OK] Decision changed to HOLD for safety")

    else:
        logger.info("[OK] All guardrails passed! Trade approved for execution.")

    return {**state, "trade_decision": decision}


# For testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("=" * 70)
    print(" Guardrails Safety Checks - Test")
    print("=" * 70)

    # Create test data
    decision = TradeDecision(
        action="buy",
        amount=0.02,  # 0.02 BTC (amount is in BTC, not USD!)
        entry_price=105000.0,
        confidence=0.85,
        reasoning="Test buy decision",
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

    print("\n[DATA] Test Data:")
    print(f"  Decision: {decision.action} ${decision.amount:.2f}")
    print(f"  Portfolio: ${portfolio.usd_balance:.2f} USD, {portfolio.btc_balance} BTC")
    print(f"  Market Price: ${market_data.price:,.2f}")

    print("\n[SAFETY] Running guardrails...")
    print("-" * 70)

    result_state = run_all_guardrails(state)

    print("\n[DATA] Result:")
    result_decision = result_state["trade_decision"]
    print(f"  Action: {result_decision.action.upper()}")
    print(f"  Amount: ${result_decision.amount:.2f}")
    print(f"  Reasoning: {result_decision.reasoning}")

    if result_state.get("errors"):
        print(f"\n[WARN] Errors ({len(result_state['errors'])}):")
        for error in result_state["errors"]:
            print(f"  - {error}")

    print("\n" + "=" * 70)
