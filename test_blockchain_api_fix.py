"""Test the fixed Blockchain.com API calls."""

import logging
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_fix():
    """Test that the hash rate API fix works."""
    logger.info("=" * 80)
    logger.info("TESTING BLOCKCHAIN.COM API FIX")
    logger.info("=" * 80)

    try:
        analyzer = BitcoinOnChainAnalyzer(cache_duration=10)

        # Test hash rate (this was failing before)
        logger.info("\n[TEST] Fetching hash rate using fixed API...")
        hash_metrics = analyzer.get_hash_rate_estimation(blocks_back=50)

        logger.info(f"\n[OK] Hash rate: {hash_metrics['hash_rate_ehs']:.2f} EH/s")
        logger.info(f"     Confidence: {hash_metrics['confidence']}")
        logger.info(f"     Blocks analyzed: {hash_metrics['blocks_analyzed']}")

        # Test comprehensive metrics
        logger.info("\n[TEST] Fetching comprehensive metrics...")
        metrics = analyzer.get_comprehensive_metrics()

        logger.info(f"\n[OK] Comprehensive metrics:")
        logger.info(f"     Hash rate: {metrics['summary']['hash_rate_ehs']:.2f} EH/s")
        logger.info(f"     Mempool: {metrics['summary']['mempool_tx_count']} txs")
        logger.info(f"     Block size: {metrics['summary']['block_size_mb']:.2f} MB")
        logger.info(f"     Network health: {metrics['summary']['network_health']}")

        logger.info("\n" + "=" * 80)
        logger.info("[SUCCESS] API fix working correctly!")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"\n[FAIL] Test failed: {e}")
        logger.exception("Error details:")
        return False

if __name__ == "__main__":
    success = test_api_fix()
    exit(0 if success else 1)
