# Smart Rate Limiting - Complete Guide

## Overview

The trading system uses **intelligent rate limiting** across all external APIs to ensure:
- No quota exhaustion (stay well under limits)
- Automatic retry with exponential backoff
- Circuit breaker pattern to prevent cascading failures
- Caching to minimize unnecessary API calls
- Multi-layer fallback for reliability

---

## Google Sheets API - Smart Implementation

### Official Google Limits (from Documentation):

```
Read Requests:
├─ Per minute per project: 300 reads/min
└─ Per minute per user per project: 60 reads/min

Write Requests:
├─ Per minute per project: 300 writes/min
└─ Per minute per user per project: 60 writes/min

Recommendations:
├─ Use exponential backoff on 429 errors
└─ Maximum payload: 2 MB
```

### Our Implementation:

```python
# File: tools/rate_limiter.py (lines 486-495)
google_sheets_rate_limit = SmartRateLimiter(
    max_calls=1,              # Only 1 call per minute
    period=60,                # Per 60 seconds
    name="GoogleSheets",
    circuit_breaker_threshold=3,    # Open circuit after 3 failures
    circuit_breaker_timeout=300,    # 5-minute cooldown
)
```

**Quota Usage Analysis:**
```
Official Limit:  60 calls/minute
Our Limit:        1 call/minute  (1.67% of quota)
Trading Cycle:    1 call/hour    (once per 30-min cycle)
Daily Usage:     24 calls/day
Daily Quota:  86,400 calls/day   (60/min × 1440 min)
Actual Usage:    0.03% of quota  (EXTREMELY CONSERVATIVE)
```

---

## Smart Features Explained

### 1. Exponential Backoff Algorithm

**What It Does:**
Automatically retries failed requests with exponentially increasing wait times.

**Implementation:**
```python
# File: tools/google_sheets_sync.py
for attempt in range(5):
    try:
        result = fetch_from_sheets()
        return result
    except Exception:
        wait_time = (2 ** attempt) + random.uniform(0, 1)
        logger.info(f"Retrying in {wait_time:.1f}s...")
        time.sleep(wait_time)
```

**Example Retry Sequence:**
```
Attempt 1: Fail → Wait 1.3s  (2^0 + 0.3 random)
Attempt 2: Fail → Wait 2.7s  (2^1 + 0.7 random)
Attempt 3: Fail → Wait 4.5s  (2^2 + 0.5 random)
Attempt 4: Fail → Wait 8.2s  (2^3 + 0.2 random)
Attempt 5: Fail → Fall back to cache
```

**Why Random Component?**
Prevents synchronized retry storms when multiple systems hit rate limits simultaneously.

---

### 2. Circuit Breaker Pattern

**What It Does:**
Opens circuit after repeated failures to prevent cascading system failures.

**States:**
```
CLOSED (Normal)
    ↓ (3 consecutive failures)
OPEN (Blocking calls)
    ↓ (After 5-minute cooldown)
HALF_OPEN (Test if recovered)
    ↓ (Success)
CLOSED (Normal)
```

**Implementation:**
```python
class SmartRateLimiter:
    def _check_circuit_breaker(self):
        if self._circuit_state == CircuitState.OPEN:
            if time.time() < cooldown_expires:
                raise CircuitBreakerOpen(...)
            else:
                self._circuit_state = CircuitState.HALF_OPEN
```

**Real-World Scenario:**
```
1. Google Sheets API down (maintenance)
2. Request 1: Fail
3. Request 2: Fail
4. Request 3: Fail → Circuit OPENS
5. All subsequent requests blocked for 5 minutes
6. After 5 minutes: Test request (HALF_OPEN)
7. If success: Circuit CLOSES (back to normal)
```

---

### 3. Sliding Window Rate Limiting

**What It Does:**
Tracks exact timestamps of API calls and removes old calls outside the rate limit window.

**Implementation:**
```python
def _clean_old_calls(self):
    current_time = time.time()
    cutoff_time = current_time - self.period

    # Remove timestamps older than the window
    while self._call_times and self._call_times[0] < cutoff_time:
        self._call_times.popleft()
```

**Example:**
```
Rate Limit: 60 calls per 60 seconds
Sliding Window:

00:00:00 ─────────────────── 00:01:00
    │                              │
    ├─ Call at 00:00:15           │
    ├─ Call at 00:00:30           │
    └─ Call at 00:00:45           │
                                   │
At 00:01:16:
    - Call at 00:00:15 expires (outside window)
    - Quota refreshed by 1
```

**Why Sliding Window vs Fixed Window?**
- Fixed: All quota resets at fixed times (e.g., top of minute)
- Sliding: Quota constantly refreshes as old calls expire
- Result: Smoother traffic distribution, no request bursts

---

### 4. Caching Layer

**What It Does:**
Stores API results in memory with configurable TTL (time-to-live).

**Implementation:**
```python
@cache_result(ttl=3600)  # Cache for 1 hour
@google_sheets_rate_limit
def get_config_from_sheets():
    return sheets_client.fetch_config()
```

**Cache Hit Ratio:**
```
30-minute trading cycle × 2 = 60 minutes
First call (00:00):  Cache MISS → API call → Cache result
Second call (00:30): Cache HIT  → Return cached result (no API call)
Third call (01:00):  Cache HIT  → Return cached result (no API call)
Fourth call (01:30): Cache EXPIRED → API call → Cache result

Result: 2 API calls instead of 4 (50% reduction)
```

**Why 1-Hour Cache for Trading Config?**
- Trading parameters (DCA threshold, position limits) are set by humans
- Humans don't change config every 30 minutes
- 1-hour cache allows config updates within reasonable time
- Reduces API calls by 50%

---

### 5. Multi-Layer Fallback

**What It Does:**
Ensures system always has valid configuration, even if APIs fail.

**Fallback Hierarchy:**
```
1. TRY: Fetch from Google Sheets (with rate limiter + retries)
   ↓ (If rate limited or API down)
2. TRY: Use local cache file (config/sheets_cache.json)
   ↓ (If cache missing or corrupted)
3. USE: Default configuration (hardcoded in code)
   ↓
4. ALWAYS: Sync successful fetches to cache for next time
```

**Code:**
```python
def get_config(self, force_refresh=False):
    # Try Google Sheets
    try:
        config = self._fetch_from_sheets()
        self._save_to_cache(config)
        return config
    except RateLimitExceeded:
        logger.warning("Rate limited, using cache")
    except Exception as e:
        logger.error(f"Fetch failed: {e}")

    # Fallback: Local cache
    if self.cache_file.exists():
        return self._load_from_cache()

    # Final fallback: Defaults
    return DEFAULT_CONFIG
```

**Real-World Scenario:**
```
Scenario 1: Normal Operation
  → Fetch from Sheets (success) → Use fresh config

Scenario 2: Internet Down
  → Fetch fails → Use cached config (system keeps running)

Scenario 3: First Startup (No Cache)
  → Fetch from Sheets (success) → Save to cache → Use config

Scenario 4: Rate Limited
  → Hit rate limit → Use cached config → Retry next cycle

Scenario 5: Complete Failure
  → All methods fail → Use default config (system keeps running)
```

---

## Rate Limiter Configuration for All APIs

### Current Limits (Ultra-Conservative):

```python
# Binance: 100 calls/60s (Official: 1200/min)
binance_rate_limit = SmartRateLimiter(
    max_calls=100,
    period=60,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=30,
)

# CoinMarketCap: 1 call/300s (Official: 10,000/month free tier)
coinmarketcap_rate_limit = SmartRateLimiter(
    max_calls=1,
    period=300,  # 5 minutes between calls
    circuit_breaker_threshold=2,
    circuit_breaker_timeout=600,
)

# HuggingFace: 150 calls/60s (Free tier limit)
huggingface_rate_limit = SmartRateLimiter(
    max_calls=150,
    period=60,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60,
)

# OpenRouter: 15 calls/60s (Free Mistral-7B tier)
openrouter_rate_limit = SmartRateLimiter(
    max_calls=15,
    period=60,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=120,
)

# Google Sheets: 1 call/60s (Official: 60/min)
google_sheets_rate_limit = SmartRateLimiter(
    max_calls=1,
    period=60,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=300,
)

# Blockchain.com: No rate limiter needed (FREE public API)
```

---

## Usage Statistics Dashboard

Run at any time to see current usage:

```bash
python check_rate_limits.py
```

**Example Output:**
```
================================================================================
RATE LIMITER DASHBOARD - Current Usage
================================================================================

Binance                0/100 calls (  0.0%)  [CLOSED    ] Total:      0
CoinMarketCap          0/  1 calls (  0.0%)  [CLOSED    ] Total:      0
YFinance               0/  1 calls (  0.0%)  [CLOSED    ] Total:      0
HuggingFace            0/150 calls (  0.0%)  [CLOSED    ] Total:      0
OpenRouter             0/ 15 calls (  0.0%)  [CLOSED    ] Total:      0
GoogleSheets           1/  1 calls (100.0%)  [CLOSED    ] Total:      3
================================================================================
```

---

## Monitoring & Alerts

### Warning Thresholds:

```python
# Warnings logged at 80% quota usage
if current_usage >= 0.80:
    logger.warning(
        f"Rate limiter '{self.name}' at {current_usage:.0%} capacity "
        f"({len(self._call_times)}/{self.max_calls} calls)"
    )
```

**When You'll See Warnings:**
```
Example: OpenRouter limit = 15 calls/min
  - At 12 calls: Warning logged (80% capacity)
  - At 15 calls: Rate limiter blocks, waits for quota refresh
  - After 60s: Oldest call expires, 1 call available
```

---

## Cost Analysis

**Total API Costs: $0/month** (All free tiers)

**Daily Quotas vs Usage:**
```
API              Daily Limit    Daily Usage    % Used
─────────────────────────────────────────────────────
Binance          1,728,000           144       0.008%
CoinMarketCap          288            24       8.33%
HuggingFace      216,000           ~100        0.05%
OpenRouter        21,600           ~100        0.46%
Google Sheets     86,400            24         0.03%
Blockchain.com   Unlimited         144        N/A
```

**Most Restrictive API:** CoinMarketCap (8.33% of free tier daily quota)

---

## Optimization Opportunities

### If You Want More Frequent Syncs:

**Current:** 1 sync/hour (24/day)

**Option 1: Every 30 Minutes** (48/day)
```python
# Change in config/settings.py
GOOGLE_SHEETS_SYNC_INTERVAL = 1800  # 30 minutes
# Usage: 48/day = 0.06% of quota (still very safe)
```

**Option 2: Every 15 Minutes** (96/day)
```python
GOOGLE_SHEETS_SYNC_INTERVAL = 900  # 15 minutes
# Usage: 96/day = 0.11% of quota (still safe)
```

**Option 3: Every 5 Minutes** (288/day)
```python
GOOGLE_SHEETS_SYNC_INTERVAL = 300  # 5 minutes
# Usage: 288/day = 0.33% of quota (still under 1%!)
```

**Why We Don't Do This:**
- Config changes are infrequent (human-driven)
- Caching makes frequent syncs unnecessary
- Conservative approach prevents quota issues

---

## Testing Rate Limiters

**Simulate Rate Limit Hit:**
```bash
python -c "
from tools.rate_limiter import google_sheets_rate_limit
import time

# Make rapid calls to trigger rate limiter
for i in range(5):
    @google_sheets_rate_limit
    def test_call():
        print(f'Call {i+1} succeeded')

    test_call()
"
```

**Expected Output:**
```
Call 1 succeeded
Rate limit reached for 'GoogleSheets'. Waiting 60.0s...
Call 2 succeeded
Rate limit reached for 'GoogleSheets'. Waiting 60.0s...
...
```

---

## Best Practices

1. **Always Use Caching:** Combine rate limiters with `@cache_result()`
2. **Log Everything:** Monitor quota usage via dashboard
3. **Set Conservative Limits:** Better to be under quota than hit 429 errors
4. **Use Circuit Breakers:** Prevent cascading failures when APIs go down
5. **Test Retry Logic:** Ensure exponential backoff works as expected
6. **Monitor Warnings:** Watch for 80% capacity warnings

---

## Summary

The trading system's rate limiting is **extremely smart and conservative**:

✓ **Google Sheets:** Using 0.03% of available quota
✓ **Exponential Backoff:** Automatically retries with increasing delays
✓ **Circuit Breaker:** Prevents system overload during API failures
✓ **Sliding Window:** Accurate quota tracking with smooth distribution
✓ **Caching:** Reduces API calls by 50%
✓ **Multi-Layer Fallback:** System never stops due to API issues
✓ **Monitoring:** Real-time usage dashboard
✓ **Zero Cost:** All APIs on free tiers

**Conclusion:** The rate limiting is production-ready and follows Google's recommended best practices from their official documentation.

---

**Related Files:**
- [tools/rate_limiter.py](tools/rate_limiter.py) - Core rate limiting implementation
- [tools/google_sheets_sync.py](tools/google_sheets_sync.py) - Google Sheets sync with retries
- [config/settings.py](config/settings.py) - Rate limit configuration
- [check_rate_limits.py](check_rate_limits.py) - Usage dashboard

**Last Updated:** 2025-11-14
