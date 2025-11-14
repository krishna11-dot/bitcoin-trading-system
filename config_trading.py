"""
Trading System Configuration

Configure your Position Manager for 24/7 autonomous operation.
Adjust settings here before starting main.py.
"""

import logging
from tools.position_manager import PositionManager

logger = logging.getLogger(__name__)


def setup_position_manager():
    """
    Initialize Position Manager with your trading configuration.

    Returns:
        PositionManager: Configured position manager instance
    """

    # =========================================================================
    # BUDGET CONFIGURATION
    # =========================================================================
    # Starting capital (in USD equivalent)
    #
    # For Testnet: Use $10,000 fake money
    # For Real Trading: Adjust to your actual budget
    #
    # Examples:
    #   - Conservative: $1,000
    #   - Moderate: $10,000
    #   - Aggressive: $100,000

    INITIAL_BUDGET = 10000.0  # <<< CHANGE THIS TO YOUR BUDGET

    # =========================================================================
    # INITIALIZE MANAGER (Singleton Pattern)
    # =========================================================================
    manager = PositionManager(
        initial_budget=INITIAL_BUDGET,
        positions_file="data/positions.json"
    )

    # =========================================================================
    # STRATEGY 1: DCA (Dollar Cost Averaging)
    # =========================================================================
    # Best for: Long-term accumulation on price drops
    # Risk Level: Low (wide stop-losses)
    # Time Horizon: Days to weeks

    manager.STRATEGY_DEFAULTS["dca"]["enabled"] = True           # Enable/Disable
    manager.STRATEGY_DEFAULTS["dca"]["atr_multiplier"] = 2.0     # Wide stops (2× ATR)
    manager.STRATEGY_DEFAULTS["dca"]["allocation_limit"] = 0.5   # Max 50% of budget
    manager.STRATEGY_DEFAULTS["dca"]["time_between_buys"] = 3600 # 1 hour minimum between buys
    manager.STRATEGY_DEFAULTS["dca"]["min_hold_time"] = 86400    # Hold for 24 hours minimum

    # =========================================================================
    # STRATEGY 2: SWING TRADING
    # =========================================================================
    # Best for: Medium-term trades on technical signals
    # Risk Level: Medium (moderate stop-losses)
    # Time Horizon: Hours to days

    manager.STRATEGY_DEFAULTS["swing"]["enabled"] = True         # Enable/Disable
    manager.STRATEGY_DEFAULTS["swing"]["atr_multiplier"] = 1.5   # Moderate stops (1.5× ATR)
    manager.STRATEGY_DEFAULTS["swing"]["allocation_limit"] = 0.3 # Max 30% of budget
    manager.STRATEGY_DEFAULTS["swing"]["min_hold_time"] = 3600   # Hold for 1 hour minimum

    # =========================================================================
    # STRATEGY 3: DAY TRADING (DISABLED BY DEFAULT - RISKY)
    # =========================================================================
    # Best for: Short-term intraday positions
    # Risk Level: High (tight stop-losses, quick exits)
    # Time Horizon: Minutes to hours
    #
    # [WARN] WARNING: Day trading is high risk and requires constant monitoring.
    #             Keep this disabled unless you know what you're doing!

    manager.STRATEGY_DEFAULTS["day"]["enabled"] = False          # Keep disabled
    manager.STRATEGY_DEFAULTS["day"]["atr_multiplier"] = 1.0     # Tight stops (1× ATR)
    manager.STRATEGY_DEFAULTS["day"]["allocation_limit"] = 0.2   # Max 20% of budget
    manager.STRATEGY_DEFAULTS["day"]["min_hold_time"] = 900      # Hold for 15 minutes minimum

    # =========================================================================
    # EMERGENCY SAFEGUARDS (Already set by default, but can be adjusted)
    # =========================================================================
    #
    # Emergency Stop: Triggers when portfolio loses 25%
    # - Blocks all new positions
    # - Sends critical alerts
    # - Optionally closes all positions
    #
    # Global Allocation Limit: Keep 5% cash buffer
    # - Prevents full allocation
    # - Maintains liquidity

    # Uncomment to adjust (default values shown):
    # manager.EMERGENCY_STOP_THRESHOLD = -0.25  # -25% portfolio loss
    # manager.MAX_TOTAL_ALLOCATION = 0.95       # Keep 5% cash buffer

    # =========================================================================
    # LOG CONFIGURATION
    # =========================================================================
    logger.info("=" * 80)
    logger.info("POSITION MANAGER CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Initial Budget: ${INITIAL_BUDGET:,.2f}")
    logger.info(f"")
    logger.info(f"Strategy Configuration:")
    logger.info(f"  DCA:   [{'ON' if manager.STRATEGY_DEFAULTS['dca']['enabled'] else 'OFF'}]  "
                f"(k={manager.STRATEGY_DEFAULTS['dca']['atr_multiplier']}, "
                f"limit={manager.STRATEGY_DEFAULTS['dca']['allocation_limit']:.0%})")
    logger.info(f"  Swing: [{'ON' if manager.STRATEGY_DEFAULTS['swing']['enabled'] else 'OFF'}]  "
                f"(k={manager.STRATEGY_DEFAULTS['swing']['atr_multiplier']}, "
                f"limit={manager.STRATEGY_DEFAULTS['swing']['allocation_limit']:.0%})")
    logger.info(f"  Day:   [{'ON' if manager.STRATEGY_DEFAULTS['day']['enabled'] else 'OFF'}]  "
                f"(k={manager.STRATEGY_DEFAULTS['day']['atr_multiplier']}, "
                f"limit={manager.STRATEGY_DEFAULTS['day']['allocation_limit']:.0%})")
    logger.info(f"")
    logger.info(f"Safeguards:")
    logger.info(f"  Emergency Stop: {manager.EMERGENCY_STOP_THRESHOLD:.0%} portfolio loss")
    logger.info(f"  Max Allocation: {manager.MAX_TOTAL_ALLOCATION:.0%} of budget")
    logger.info("=" * 80)

    return manager


if __name__ == "__main__":
    """Test configuration"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 80)
    print("TESTING POSITION MANAGER CONFIGURATION")
    print("=" * 80 + "\n")

    # Initialize manager
    manager = setup_position_manager()

    # Show budget stats
    print("\n" + "-" * 80)
    print("BUDGET STATUS")
    print("-" * 80)

    stats = manager.get_budget_stats()

    print(f"Initial Budget:     ${stats['initial_budget']:>12,.2f}")
    print(f"Available Capital:  ${stats['available_capital']:>12,.2f}")
    print(f"Allocated Capital:  ${stats['allocated_capital']:>12,.2f} ({stats['allocation_pct']:>6.1%})")
    print(f"Portfolio Value:    ${stats['portfolio_value']:>12,.2f}")
    print(f"Unrealized P&L:     ${stats['unrealized_pnl']:>12,.2f}")
    print(f"Realized P&L:       ${stats['realized_pnl']:>12,.2f}")
    print(f"Total P&L:          ${stats['total_pnl']:>12,.2f}")

    print("\n" + "-" * 80)
    print("STRATEGY ALLOCATION")
    print("-" * 80)

    for strategy in ["dca", "swing", "day"]:
        s = stats["by_strategy"][strategy]
        enabled = "[ON]" if manager.STRATEGY_DEFAULTS[strategy]["enabled"] else "[OFF]"
        print(f"{enabled} {strategy.upper():6s}: {s['count']} positions, "
              f"${s['allocated']:>10,.2f} ({s['allocation_pct']:>6.1%})")

    print("\n" + "-" * 80)
    print("NEXT STEPS")
    print("-" * 80)
    print("1. Adjust settings above if needed")
    print("2. Get Binance Testnet API keys from https://testnet.binance.vision/")
    print("3. Create .env file with your keys")
    print("4. Run: python main.py")
    print("")
    print("[OK] Configuration test complete!")
    print("=" * 80 + "\n")
