"""Quick test to diagnose workflow execution time."""

import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow_speed():
    """Test how long the workflow takes."""

    logger.info("=" * 80)
    logger.info("WORKFLOW SPEED TEST")
    logger.info("=" * 80)

    try:
        # Test 1: Import time
        start = time.time()
        logger.info("\n[TEST 1] Importing trading_workflow...")
        from graph.trading_workflow import run_trading_cycle
        elapsed = time.time() - start
        logger.info(f"[OK] Import took {elapsed:.2f}s")

        # Test 2: Execute workflow
        start = time.time()
        logger.info("\n[TEST 2] Running one trading cycle...")
        logger.info("   This should take 1-2 minutes normally...")

        config = {
            "dca_threshold": 3.0,
            "dca_amount": 100,
            "atr_multiplier": 1.5,
            "max_position_size": 0.20,
            "max_total_exposure": 0.80,
            "emergency_stop": 0.25,
        }

        result = await run_trading_cycle(config)
        elapsed = time.time() - start

        logger.info(f"\n[OK] Workflow completed in {elapsed:.2f}s")

        # Show result
        if result.get("trade_decision"):
            td = result["trade_decision"]
            logger.info(f"\n[RESULT] Trade Decision:")
            logger.info(f"   Action: {td.action}")
            logger.info(f"   Amount: {td.amount:.4f} BTC")
            logger.info(f"   Confidence: {td.confidence:.0%}")
        else:
            logger.warning("[WARN] No trade decision in result")

        if result.get("errors"):
            logger.warning(f"\n[ERRORS] {len(result['errors'])} errors:")
            for error in result["errors"]:
                logger.warning(f"   - {error}")

        logger.info("\n" + "=" * 80)
        logger.info("[SUCCESS] Workflow test complete")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n[FAIL] Test failed: {e}")
        logger.exception("Full error:")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_workflow_speed())
    exit(0 if success else 1)
