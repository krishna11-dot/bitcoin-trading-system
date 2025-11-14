"""Test script to verify Position Manager integration in main.py

This script tests:
1. Imports work correctly
2. Components initialize properly
3. No syntax errors in main.py
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test that all imports work correctly."""
    try:
        logger.info("[TEST] Testing imports...")

        from tools.position_manager import PositionManager
        from tools.binance_client import BinanceClient
        from graph.trading_workflow import run_trading_cycle
        from guardrails.safety_checks import run_all_guardrails
        from config.settings import Settings

        logger.info("[OK] All imports successful")
        return True

    except Exception as e:
        logger.error(f"[FAIL] Import failed: {e}")
        return False


def test_position_manager_init():
    """Test Position Manager initialization."""
    try:
        logger.info("\n[TEST] Testing Position Manager initialization...")

        from tools.position_manager import PositionManager

        # Initialize with test budget
        manager = PositionManager(initial_budget=10000.0)

        # Check initialization
        budget = manager.get_budget_stats()
        assert budget['initial_budget'] == 10000.0, "Budget mismatch"
        assert budget['available_capital'] == 10000.0, "Available capital mismatch"
        assert budget['allocated_capital'] == 0.0, "Allocated capital should be 0"

        logger.info(f"[OK] Position Manager initialized with ${budget['initial_budget']:,.2f}")
        return True

    except Exception as e:
        logger.error(f"[FAIL] Position Manager initialization failed: {e}")
        logger.exception("Details:")
        return False


def test_binance_client_init():
    """Test Binance Client initialization."""
    try:
        logger.info("\n[TEST] Testing Binance Client initialization...")

        from tools.binance_client import BinanceClient

        # Initialize client
        client = BinanceClient()

        logger.info("[OK] Binance Client initialized")

        # Try to get current price (may fail if no API keys, but should not crash)
        try:
            price_data = client.get_current_price("BTCUSDT")
            logger.info(f"[OK] BTC Price: ${price_data.price:,.2f}")
        except Exception as e:
            logger.warning(f"[WARN] Could not fetch price (expected if no API keys): {e}")

        return True

    except Exception as e:
        logger.error(f"[FAIL] Binance Client initialization failed: {e}")
        logger.exception("Details:")
        return False


def test_main_syntax():
    """Test that main.py has no syntax errors."""
    try:
        logger.info("\n[TEST] Testing main.py syntax...")

        import main

        logger.info("[OK] main.py syntax valid")
        return True

    except Exception as e:
        logger.error(f"[FAIL] main.py has errors: {e}")
        logger.exception("Details:")
        return False


def main():
    """Run all integration tests."""
    logger.info("=" * 80)
    logger.info("POSITION MANAGER INTEGRATION TEST")
    logger.info("=" * 80)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Position Manager Init", test_position_manager_init()))
    results.append(("Binance Client Init", test_binance_client_init()))
    results.append(("main.py Syntax", test_main_syntax()))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        logger.info(f"{status} {test_name}")

    all_passed = all(result[1] for result in results)

    logger.info("=" * 80)

    if all_passed:
        logger.info("\n[SUCCESS] All integration tests passed!")
        logger.info("\nThe Position Manager is successfully integrated into main.py")
        logger.info("\nNext steps:")
        logger.info("  1. Configure API keys in .env")
        logger.info("  2. Set INITIAL_TRADING_BUDGET in settings (default: $10,000)")
        logger.info("  3. Run: python main.py")
        return 0
    else:
        logger.error("\n[FAIL] Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
