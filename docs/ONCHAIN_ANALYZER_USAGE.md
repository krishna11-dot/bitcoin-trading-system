# Bitcoin On-Chain Analyzer - Usage Guide

## Overview

The `BitcoinOnChainAnalyzer` provides **FREE** on-chain metrics using Blockchain.com API as an alternative to CryptoQuant (which requires paid subscription).

**✅ Advantages over CryptoQuant:**
- 100% FREE - No API keys required
- No rate limits for basic usage
- Real-time blockchain data
- Simple REST API
- No authentication needed

---

## Quick Start

### 1. Basic Usage

```python
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

# Initialize analyzer (with 2-minute caching)
analyzer = BitcoinOnChainAnalyzer(cache_duration=120)

# Get block size metrics
block_metrics = analyzer.get_block_size_metrics()
print(f"Current block size: {block_metrics['current_size_mb']:.2f} MB")
print(f"Trend: {block_metrics['trend']}")

# Get hash rate estimation
hash_metrics = analyzer.get_hash_rate_estimation()
print(f"Hash rate: {hash_metrics['hash_rate_ehs']:.2f} EH/s")

# Get mempool status
mempool_metrics = analyzer.get_mempool_metrics()
print(f"Unconfirmed transactions: {mempool_metrics['tx_count']:,}")
print(f"Congestion: {mempool_metrics['congestion_level']}")

# Get everything at once
comprehensive = analyzer.get_comprehensive_metrics()
print(f"Network health: {comprehensive['summary']['network_health']}")
```

---

## Integration with Trading Agents

### Option 1: Add to Market Analysis Agent

```python
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

class MarketAnalysisAgent:
    def __init__(self):
        self.onchain_analyzer = BitcoinOnChainAnalyzer(cache_duration=300)

    def analyze_market_conditions(self):
        # Get on-chain metrics
        onchain = self.onchain_analyzer.get_comprehensive_metrics()

        # Extract key indicators
        hash_rate = onchain['summary']['hash_rate_ehs']
        congestion = onchain['summary']['mempool_congestion']
        network_health = onchain['summary']['network_health']

        # Incorporate into trading decision
        if network_health == 'Poor' or congestion == 'Critical':
            return "AVOID - Network issues detected"

        if hash_rate > 450:  # Strong hash rate
            return "BULLISH - Network security strong"

        return "NEUTRAL"
```

### Option 2: Add to Feature Extraction

```python
def extract_onchain_features():
    """Extract on-chain metrics as ML features."""

    analyzer = BitcoinOnChainAnalyzer()
    metrics = analyzer.get_comprehensive_metrics()

    features = {
        # Block metrics
        'block_size_mb': metrics['block_metrics']['current_size_mb'],
        'block_trend': 1 if metrics['block_metrics']['trend'] == 'increasing' else 0,

        # Hash rate
        'hash_rate_ehs': metrics['hash_rate_metrics']['hash_rate_ehs'],
        'avg_block_time': metrics['hash_rate_metrics']['avg_block_time'],

        # Mempool
        'mempool_tx_count': metrics['mempool_metrics']['tx_count'],
        'mempool_size_mb': metrics['mempool_metrics']['total_size_mb'],
        'avg_fee_satoshis': metrics['mempool_metrics']['avg_fee_satoshis'],
        'congestion_severity': metrics['mempool_metrics']['backlog_severity'],

        # Derived
        'network_healthy': 1 if metrics['summary']['network_health'] in ['Excellent', 'Good'] else 0
    }

    return features
```

### Option 3: Real-time Monitoring

```python
import time
from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer

def monitor_network_conditions():
    """Monitor network for trading opportunities."""

    analyzer = BitcoinOnChainAnalyzer(cache_duration=60)

    while True:
        comprehensive = analyzer.get_comprehensive_metrics()
        summary = comprehensive['summary']

        # Check for trading opportunities
        if summary['mempool_congestion'] == 'Low':
            print("[OPPORTUNITY] Low network congestion - good time to trade")

        if summary['hash_rate_ehs'] > 500:
            print("[BULLISH] Very high hash rate - network security excellent")

        if summary['network_health'] == 'Poor':
            print("[WARNING] Poor network health - consider delaying trades")

        # Wait 5 minutes
        time.sleep(300)
```

---

## Metrics Reference

### Block Size Metrics

```python
{
    'current_size_mb': 1.45,           # Current block size in MB
    'current_size_bytes': 1_520_000,   # Current block size in bytes
    'avg_size_mb': 1.42,               # Average of last 10 blocks
    'avg_size_bytes': 1_489_000,       # Average in bytes
    'trend': 'increasing',             # 'increasing', 'decreasing', 'stable'
    'block_height': 870_123,           # Current block height
    'last_10_blocks': [...],           # List of last 10 block sizes
    'blocks_analyzed': 10,             # Number of blocks analyzed
    'timestamp': '2025-01-15T12:00:00' # Analysis timestamp
}
```

### Hash Rate Metrics

```python
{
    'hash_rate_ths': 450_000_000,      # Hash rate in TH/s (Tera Hashes)
    'hash_rate_ehs': 450,              # Hash rate in EH/s (Exa Hashes)
    'avg_block_time': 590,             # Average block time in seconds
    'difficulty': 72_000_000_000_000,  # Current difficulty
    'confidence': 'high',              # 'high', 'medium', 'low'
    'blocks_analyzed': 18,             # Number of blocks sampled
    'timestamp': '2025-01-15T12:00:00'
}
```

**Interpretation:**
- `hash_rate_ehs > 450`: **Bullish** - Strong network security
- `hash_rate_ehs < 350`: **Bearish** - Declining hash rate
- `avg_block_time < 540`: **Fast blocks** - Hash rate increasing
- `avg_block_time > 660`: **Slow blocks** - Hash rate decreasing

### Mempool Metrics

```python
{
    'tx_count': 15_234,                # Unconfirmed transactions
    'total_size_mb': 85.5,             # Total mempool size in MB
    'total_size_bytes': 89_654_784,    # Total size in bytes
    'avg_fee_satoshis': 45.2,          # Average fee per byte (satoshis)
    'avg_fee_btc': 0.00000045,         # Average fee in BTC
    'congestion_level': 'Medium',      # 'Low', 'Medium', 'High', 'Critical'
    'backlog_severity': 0.52,          # 0-1 scale (0=none, 1=severe)
    'fee_samples_analyzed': 100,       # Number of transactions analyzed
    'timestamp': '2025-01-15T12:00:00'
}
```

**Interpretation:**
- `congestion_level == 'Low'`: **GOOD** - Fast confirmations, low fees
- `congestion_level == 'Medium'`: **OK** - Normal conditions
- `congestion_level == 'High'`: **CAUTION** - Slow confirmations, high fees
- `congestion_level == 'Critical'`: **AVOID** - Very slow, very expensive

---

## Trading Signal Examples

### Example 1: Network Health Check Before Trading

```python
def is_good_time_to_trade():
    """Check if network conditions are favorable."""

    analyzer = BitcoinOnChainAnalyzer()
    metrics = analyzer.get_comprehensive_metrics()

    # Check network health
    health = metrics['summary']['network_health']
    congestion = metrics['summary']['mempool_congestion']

    if health in ['Excellent', 'Good'] and congestion in ['Low', 'Medium']:
        return True, "Network conditions favorable"

    if congestion in ['High', 'Critical']:
        return False, f"High network congestion: {congestion}"

    return True, "Acceptable network conditions"
```

### Example 2: Hash Rate Momentum

```python
def get_hash_rate_signal():
    """Get trading signal from hash rate trends."""

    analyzer = BitcoinOnChainAnalyzer()
    hash_metrics = analyzer.get_hash_rate_estimation()

    hash_rate = hash_metrics['hash_rate_ehs']
    block_time = hash_metrics['avg_block_time']

    # Fast blocks + high hash rate = Bullish
    if block_time < 540 and hash_rate > 450:
        return "STRONG_BUY"

    # Slow blocks + declining hash rate = Bearish
    if block_time > 660 and hash_rate < 350:
        return "SELL"

    return "NEUTRAL"
```

### Example 3: Fee-Based Entry Timing

```python
def should_enter_position():
    """Determine if fees are low enough to enter."""

    analyzer = BitcoinOnChainAnalyzer()
    mempool = analyzer.get_mempool_metrics()

    avg_fee = mempool['avg_fee_satoshis']
    congestion = mempool['congestion_level']

    # Only trade when fees are reasonable
    if avg_fee < 20 and congestion in ['Low', 'Medium']:
        return True, "Low fees - good time to trade"

    if avg_fee > 100:
        return False, f"High fees: {avg_fee:.0f} sat/byte - wait"

    return True, "Acceptable fees"
```

---

## API Caching

The analyzer automatically caches responses for 2 minutes (default) to avoid excessive API calls.

```python
# Initialize with custom cache duration
analyzer = BitcoinOnChainAnalyzer(cache_duration=300)  # 5 minutes

# Check cache status
cache_stats = analyzer.get_cache_stats()
print(f"Cached entries: {cache_stats['valid_entries']}")

# Clear cache manually
analyzer.clear_cache()
```

---

## Error Handling

The analyzer includes robust error handling:

```python
# Automatic retries (3 attempts)
# Exponential backoff on failures
# Fallback to cached data if available
# Default values during outages

metrics = analyzer.get_block_size_metrics()

# Check for errors
if 'error' in metrics:
    print(f"Warning: Using fallback data - {metrics['error']}")
else:
    print(f"Live data: Block size = {metrics['current_size_mb']} MB")
```

---

## Comparison: CryptoQuant vs Blockchain.com API

| Feature | CryptoQuant | Blockchain.com API |
|---------|-------------|-------------------|
| **Cost** | $99-$399/month | **FREE** |
| **API Keys** | Required | **None required** |
| **Rate Limits** | Strict (10-100/day) | **Generous** |
| **Block Data** | ✅ Yes | ✅ Yes |
| **Hash Rate** | ✅ Yes | ✅ Yes (calculated) |
| **Mempool** | ✅ Yes | ✅ Yes |
| **Historical Data** | ✅ Extensive | ⚠️ Limited |
| **Setup Complexity** | Medium | **Very Easy** |
| **Reliability** | High | **High** |

**Verdict:** For autonomous trading with real-time on-chain analysis, Blockchain.com API is **perfect** and completely free!

---

## Best Practices

1. **Use caching** - Don't make requests more than once per minute
2. **Handle errors** - Always check for 'error' key in responses
3. **Combine signals** - Use multiple metrics together
4. **Monitor trends** - Track changes over time, not just snapshots
5. **Respect API** - Don't abuse the free service

---

## Testing

```bash
# Run the test suite
python test_onchain_analyzer.py
```

Expected output:
- Block size metrics with trend analysis
- Hash rate estimation with confidence level
- Mempool analysis with congestion levels
- Comprehensive network health assessment

---

## Summary

The `BitcoinOnChainAnalyzer` provides:

✅ **FREE** alternative to paid services
✅ **Real-time** blockchain metrics
✅ **No authentication** required
✅ **Automatic caching** and error handling
✅ **Production-ready** with fallback values
✅ **Easy integration** with trading agents

Perfect for autonomous Bitcoin trading systems!
