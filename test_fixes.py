"""Quick test to verify all fixes are working."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("="*80)
print("TESTING ALL FIXES")
print("="*80)

# Test 1: Import BitcoinOnChainAnalyzer (replacing CryptoQuantClient)
print("\n[TEST 1] Testing BitcoinOnChainAnalyzer import...")
try:
    from tools.bitcoin_onchain_analyzer import BitcoinOnChainAnalyzer
    analyzer = BitcoinOnChainAnalyzer()
    print("[OK] BitcoinOnChainAnalyzer imported and initialized")
except Exception as e:
    print(f"[FAIL] {e}")
    exit(1)

# Test 2: Test Binance kline format with MarketData
print("\n[TEST 2] Testing kline to MarketData conversion...")
try:
    from tools.binance_client import BinanceClient
    from data_models import MarketData
    from datetime import datetime

    binance = BinanceClient()
    klines = binance.get_historical_klines("BTCUSDT", "1h", limit=5)

    print(f"  Fetched {len(klines)} klines")
    print(f"  Kline format: {type(klines[0])}")
    print(f"  Kline keys: {list(klines[0].keys())}")

    # Try converting first kline to MarketData
    kline = klines[0]
    timestamp_ms = int(kline['open_time'])
    timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000).isoformat() + "Z"

    md = MarketData(
        price=float(kline['close']),
        volume=float(kline['volume']),
        timestamp=timestamp_iso,
        change_24h=0.0,
        high_24h=float(kline['high']),
        low_24h=float(kline['low']),
    )

    print(f"[OK] Successfully converted kline to MarketData")
    print(f"  Price: ${md.price:,.2f}")
    print(f"  Volume: {md.volume:.4f} BTC")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Test TradeDecision with minimum valid amount
print("\n[TEST 3] Testing TradeDecision with hold action...")
try:
    from data_models import TradeDecision
    from datetime import datetime

    # Test hold decision with minimum valid amount
    decision = TradeDecision(
        action="hold",
        amount=0.0001,  # Minimum valid amount
        entry_price=104000.0,
        confidence=1.0,
        reasoning="Testing hold decision with minimum valid amount for validation.",
        timestamp=datetime.now().isoformat(),
        strategy="dca",
    )

    print(f"[OK] TradeDecision created successfully")
    print(f"  Action: {decision.action}")
    print(f"  Amount: {decision.amount} BTC")
    print(f"  Entry Price: ${decision.entry_price:,.2f}")

except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Test workflow imports
print("\n[TEST 4] Testing workflow imports...")
try:
    from graph.trading_workflow import run_trading_cycle
    print("[OK] Trading workflow imports successful")
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*80)
print("[SUCCESS] ALL TESTS PASSED!")
print("="*80)
print("\nFixed issues:")
print("  1. ✅ Replaced CryptoQuantClient with BitcoinOnChainAnalyzer")
print("  2. ✅ Fixed kline dictionary access (was using list indices)")
print("  3. ✅ Fixed TradeDecision validation (amount must be > 0)")
print("\nYour system should now run without those errors!")
print("="*80)
