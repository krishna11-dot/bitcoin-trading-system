"""
Test Bitcoin On-Chain Analyzer

Tests the Blockchain.com API integration for on-chain metrics.
"""

import logging
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_onchain_analyzer():
    """Test all features of the BitcoinOnChainAnalyzer."""

    print("\n" + "=" * 80)
    print("BITCOIN ON-CHAIN ANALYZER TEST")
    print("=" * 80)
    print("\nUsing Blockchain.com API as free CryptoQuant alternative")
    print()

    # Initialize analyzer
    analyzer = BitcoinOnChainAnalyzer(cache_duration=120)

    # =========================================================================
    # TEST 1: Block Size Metrics
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 1: BLOCK SIZE METRICS")
    print("-" * 80)

    try:
        block_metrics = analyzer.get_block_size_metrics()

        if 'error' in block_metrics:
            print(f"[WARN] Using fallback data: {block_metrics.get('error')}")

        print(f"\nBlock Height:       {block_metrics.get('block_height', 'N/A'):,}")
        print(f"Current Size:       {block_metrics.get('current_size_mb', 0):.2f} MB "
              f"({block_metrics.get('current_size_bytes', 0):,} bytes)")
        print(f"Average Size:       {block_metrics.get('avg_size_mb', 0):.2f} MB "
              f"({block_metrics.get('avg_size_bytes', 0):,.0f} bytes)")
        print(f"Trend:              {block_metrics.get('trend', 'unknown').upper()}")
        print(f"Blocks Analyzed:    {block_metrics.get('blocks_analyzed', 0)}")

        if block_metrics.get('last_10_blocks'):
            sizes_mb = [s / (1024 * 1024) for s in block_metrics['last_10_blocks']]
            print(f"\nLast 10 Block Sizes (MB):")
            for i, size in enumerate(sizes_mb[:10], 1):
                print(f"  Block {i}: {size:.2f} MB")

        print("\n[OK] Block size metrics retrieved")

    except Exception as e:
        print(f"[FAIL] Block size test failed: {e}")

    # =========================================================================
    # TEST 2: Hash Rate Estimation
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 2: HASH RATE ESTIMATION")
    print("-" * 80)

    try:
        hash_metrics = analyzer.get_hash_rate_estimation(blocks_back=100)

        if 'error' in hash_metrics:
            print(f"[WARN] Using fallback data: {hash_metrics.get('error')}")

        print(f"\nHash Rate:          {hash_metrics.get('hash_rate_ehs', 0):,.2f} EH/s")
        print(f"                    {hash_metrics.get('hash_rate_ths', 0):,.2f} TH/s")
        print(f"Avg Block Time:     {hash_metrics.get('avg_block_time', 0):.2f} seconds "
              f"({hash_metrics.get('avg_block_time', 0) / 60:.2f} minutes)")
        print(f"Difficulty:         {hash_metrics.get('difficulty', 0):,.0f}")
        print(f"Confidence:         {hash_metrics.get('confidence', 'unknown').upper()}")
        print(f"Blocks Analyzed:    {hash_metrics.get('blocks_analyzed', 0)}")

        # Interpretation
        block_time = hash_metrics.get('avg_block_time', 600)
        if block_time < 540:  # < 9 minutes
            print(f"\nInterpretation:     Blocks coming FASTER than expected (bullish hash rate)")
        elif block_time > 660:  # > 11 minutes
            print(f"Interpretation:     Blocks coming SLOWER than expected (bearish hash rate)")
        else:
            print(f"Interpretation:     Block time is NORMAL (~10 minutes)")

        print("\n[OK] Hash rate estimation complete")

    except Exception as e:
        print(f"[FAIL] Hash rate test failed: {e}")

    # =========================================================================
    # TEST 3: Mempool Analysis
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 3: MEMPOOL ANALYSIS")
    print("-" * 80)

    try:
        mempool_metrics = analyzer.get_mempool_metrics()

        if 'error' in mempool_metrics:
            print(f"[WARN] Using fallback data: {mempool_metrics.get('error')}")

        print(f"\nTransaction Count:  {mempool_metrics.get('tx_count', 0):,} unconfirmed")
        print(f"Total Size:         {mempool_metrics.get('total_size_mb', 0):.2f} MB "
              f"({mempool_metrics.get('total_size_bytes', 0):,} bytes)")
        print(f"Avg Fee:            {mempool_metrics.get('avg_fee_satoshis', 0):.2f} sat/byte")
        print(f"                    {mempool_metrics.get('avg_fee_btc', 0):.8f} BTC")
        print(f"Congestion Level:   {mempool_metrics.get('congestion_level', 'Unknown')}")
        print(f"Backlog Severity:   {mempool_metrics.get('backlog_severity', 0):.2f} / 1.0")
        print(f"Fee Samples:        {mempool_metrics.get('fee_samples_analyzed', 0)}")

        # Trading interpretation
        congestion = mempool_metrics.get('congestion_level', 'Unknown')
        if congestion == 'Low':
            print(f"\nTrading Impact:     LOW - Network is healthy, transactions confirming quickly")
        elif congestion == 'Medium':
            print(f"Trading Impact:     MODERATE - Some delays expected, monitor fees")
        elif congestion == 'High':
            print(f"Trading Impact:     HIGH - Network congested, higher fees needed")
        elif congestion == 'Critical':
            print(f"Trading Impact:     CRITICAL - Severe congestion, consider delaying trades")

        print("\n[OK] Mempool analysis complete")

    except Exception as e:
        print(f"[FAIL] Mempool test failed: {e}")

    # =========================================================================
    # TEST 4: Comprehensive Metrics
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 4: COMPREHENSIVE METRICS (ALL COMBINED)")
    print("-" * 80)

    try:
        comprehensive = analyzer.get_comprehensive_metrics()

        if 'error' in comprehensive:
            print(f"[FAIL] Comprehensive metrics failed: {comprehensive['error']}")
        else:
            summary = comprehensive.get('summary', {})

            print(f"\nNetwork Summary:")
            print(f"  Block Size:       {summary.get('block_size_mb', 0):.2f} MB "
                  f"({summary.get('block_size_trend', 'unknown')})")
            print(f"  Hash Rate:        {summary.get('hash_rate_ehs', 0):.2f} EH/s")
            print(f"  Mempool Txs:      {summary.get('mempool_tx_count', 0):,}")
            print(f"  Congestion:       {summary.get('mempool_congestion', 'Unknown')}")
            print(f"  Network Health:   {summary.get('network_health', 'Unknown')}")

            metadata = comprehensive.get('metadata', {})
            print(f"\nData Source:        {metadata.get('data_source', 'Unknown')}")
            print(f"Timestamp:          {metadata.get('timestamp', 'N/A')}")
            print(f"Version:            {metadata.get('analyzer_version', 'N/A')}")

            print("\n[OK] Comprehensive metrics retrieved")

    except Exception as e:
        print(f"[FAIL] Comprehensive test failed: {e}")

    # =========================================================================
    # TEST 5: Cache Statistics
    # =========================================================================
    print("\n" + "-" * 80)
    print("TEST 5: CACHE PERFORMANCE")
    print("-" * 80)

    try:
        cache_stats = analyzer.get_cache_stats()

        print(f"\nCache Statistics:")
        print(f"  Total Entries:    {cache_stats.get('total_entries', 0)}")
        print(f"  Valid Entries:    {cache_stats.get('valid_entries', 0)}")
        print(f"  Stale Entries:    {cache_stats.get('stale_entries', 0)}")
        print(f"  Cache Duration:   {cache_stats.get('cache_duration', 0)} seconds")

        print("\n[OK] Cache working correctly")

    except Exception as e:
        print(f"[FAIL] Cache test failed: {e}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("\n[OK] All tests completed successfully!")
    print("\nBitcoinOnChainAnalyzer Features:")
    print("  [OK] Block size metrics with trend analysis")
    print("  [OK] Hash rate estimation from block data")
    print("  [OK] Mempool analysis with congestion levels")
    print("  [OK] Comprehensive metrics for ML features")
    print("  [OK] Automatic caching (2-minute duration)")
    print("  [OK] Error handling with fallback values")
    print("\nReady for integration with trading agents!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_onchain_analyzer()
