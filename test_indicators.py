from tools.indicator_calculator import (
    calculate_rsi, calculate_macd, calculate_atr,
    calculate_sma, calculate_ema, calculate_all_indicators
)
from data_models.market_data import MarketData
from datetime import datetime

print("="*60)
print("TESTING INDICATOR CALCULATOR")
print("="*60)

# Test data: Bitcoin prices
prices = [
    61000, 61200, 60800, 61500, 61300,
    61700, 61400, 61900, 61600, 62000,
    61800, 62200, 61900, 62400, 62100,
    62500, 62200, 62700, 62400, 63000,
    62700, 63200, 62900, 63500, 63200,
    63700, 63400, 64000, 63700, 64200,
    63900, 64400, 64100, 64600, 64300,
    64800, 64500, 65000, 64700, 65200,
    64900, 65400, 65100, 65600, 65300,
    65800, 65500, 66000, 65700, 66200
]

# Test 1: RSI
print("\n1. Testing RSI...")
try:
    rsi = calculate_rsi(prices, period=14)
    print(f"[OK] RSI calculated: {rsi:.2f}")
    if 0 <= rsi <= 100:
        print(f"   [OK] RSI in valid range (0-100)")
    else:
        print(f"   [FAIL] RSI out of range: {rsi}")
except Exception as e:
    print(f"[FAIL] RSI failed: {e}")

# Test 2: MACD
print("\n2. Testing MACD...")
try:
    macd, signal, histogram = calculate_macd(prices)
    print(f"[OK] MACD calculated")
    print(f"   MACD: {macd:.2f}")
    print(f"   Signal: {signal:.2f}")
    print(f"   Histogram: {histogram:.2f}")
except Exception as e:
    print(f"[FAIL] MACD failed: {e}")

# Test 3: SMA
print("\n3. Testing SMA...")
try:
    sma = calculate_sma(prices, period=20)
    print(f"[OK] SMA-20: {sma:.2f}")
except Exception as e:
    print(f"[FAIL] SMA failed: {e}")

# Test 4: All indicators with MarketData
print("\n4. Testing calculate_all_indicators...")
try:
    # Create MarketData objects
    market_data = [
        MarketData(
            price=p,
            volume=1000000,
            timestamp=datetime.now().isoformat(),
            change_24h=0.5,
            high_24h=p * 1.02,
            low_24h=p * 0.98
        )
        for p in prices
    ]
    
    indicators = calculate_all_indicators(market_data)
    
    if indicators:
        print(f"[OK] All indicators calculated")
        print(f"   RSI: {indicators.rsi_14:.2f}")
        print(f"   MACD: {indicators.macd:.2f}")
        print(f"   ATR: {indicators.atr_14:.2f}")
        print(f"   SMA-50: {indicators.sma_50:.2f}")
    else:
        print(f"[FAIL] calculate_all_indicators returned None")
        
except Exception as e:
    print(f"[FAIL] All indicators failed: {e}")

# Test 5: Insufficient data
print("\n5. Testing error handling (insufficient data)...")
try:
    short_data = market_data[:10]  # Only 10 points
    result = calculate_all_indicators(short_data)
    if result is None:
        print("[OK] Correctly returned None for insufficient data")
    else:
        print("[FAIL] Should have returned None")
except Exception as e:
    print(f"[FAIL] Error handling failed: {e}")

print("\n" + "="*60)
print("INDICATOR TESTS COMPLETE")
print("="*60)