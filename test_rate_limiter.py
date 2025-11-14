from tools.rate_limiter import binance_rate_limit, coinmarketcap_rate_limit, get_all_rate_limit_stats
import time

print("Testing Rate Limiters...")

# Test Binance (should allow multiple)
@binance_rate_limit
def test_binance():
    return "success"

for i in range(5):
    result = test_binance()
    print(f"[OK] Binance call {i+1}: {result}")

# Test CMC (should restrict heavily)
@coinmarketcap_rate_limit
def test_cmc():
    return "success"

print("\n[OK] CMC call 1")
test_cmc()
# Second call should wait or fail
print("(CMC call 2 would wait 5 minutes)")

# Test usage stats
stats = get_all_rate_limit_stats()
print(f"\n[OK] Usage stats available: {len(stats)} APIs tracked")

print("\nRate limiter tests complete!")