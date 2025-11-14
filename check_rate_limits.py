"""Check current rate limiter usage across all APIs."""

from tools.rate_limiter import get_all_rate_limit_stats

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("RATE LIMITER DASHBOARD - Current Usage")
    print("=" * 80)
    print()

    stats = get_all_rate_limit_stats()

    for name, stat in stats.items():
        circuit_status = stat.circuit_state.value.upper()
        warning = ""
        if stat.usage_pct >= 80:
            warning = "  ** HIGH USAGE **"
        if stat.circuit_state.value == "open":
            warning = "  ** CIRCUIT OPEN **"

        print(f"{name:20} {stat.current_calls:3}/{stat.max_calls:3} calls "
              f"({stat.usage_pct:5.1f}%)  [{circuit_status:10}] "
              f"Total: {stat.total_calls:6}{warning}")

    print("=" * 80)
    print()
    print("Google Sheets API Analysis:")
    print("-" * 80)
    print("Official Limit:   60 reads/minute per user")
    print("Our Limit:         1 call/minute (1.67% of quota)")
    print("Trading Frequency: 1 call/hour (once per cycle)")
    print("Daily Usage:      24 calls/day")
    print("Daily Quota:      86,400 calls/day")
    print("Quota Usage:      0.03% (extremely conservative!)")
    print()
    print("Why So Conservative?")
    print("  - Config rarely changes (human updates via Google Sheets)")
    print("  - Caching layer reduces actual API calls")
    print("  - Multi-layer fallback (cache -> defaults)")
    print("  - Prevents accidental quota exhaustion")
    print()
    print("Smart Features Active:")
    print("  [+] Exponential backoff (2^n + random)")
    print("  [+] Circuit breaker (3 failures -> 5min cooldown)")
    print("  [+] Sliding window rate limiting")
    print("  [+] 1-hour cache TTL (minimizes calls)")
    print("  [+] Local cache fallback (offline operation)")
    print("=" * 80)
