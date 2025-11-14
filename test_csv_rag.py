from tools.csv_rag_pipeline import RAGRetriever
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from datetime import datetime
import pandas as pd
import numpy as np

print("="*60)
print("TESTING CSV RAG PIPELINE")
print("="*60)

# Test 1: Create sample CSV
print("\n1. Creating sample historical data...")
try:
    # Generate synthetic data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=1000, freq='D')
    
    data = {
        'Date': dates,
        'Price': np.random.uniform(40000, 70000, 1000),
        'RSI': np.random.uniform(20, 80, 1000),
        'MACD': np.random.uniform(-300, 300, 1000),
        'ATR': np.random.uniform(800, 2000, 1000),
        'Volume': np.random.uniform(500000, 2000000, 1000),
        'Action': np.random.choice(['bought', 'sold', 'held'], 1000),
        'Outcome': np.random.uniform(-10, 15, 1000),
        'Success': np.random.choice([0, 1], 1000, p=[0.4, 0.6])
    }
    
    df = pd.DataFrame(data)
    df.to_csv('data/Bitcoin_Historical_Data_Raw.csv', index=False)
    print("[OK] Sample CSV created (1000 rows)")
    print(f"   Success rate in data: {df['Success'].mean():.1%}")
    
except Exception as e:
    print(f"[FAIL] Failed to create CSV: {e}")
    exit(1)

# Test 2: Initialize RAG
print("\n2. Initializing RAG retriever...")
try:
    rag = RAGRetriever('data/Bitcoin_Historical_Data_Raw.csv')
    print("[OK] RAG retriever initialized")
except Exception as e:
    print(f"[FAIL] RAG initialization failed: {e}")
    exit(1)

# Test 3: Query similar patterns
print("\n3. Querying similar patterns...")
try:
    # Create test market data
    market_data = MarketData(
        price=61000,
        volume=1000000,
        timestamp=datetime.now().isoformat(),
        change_24h=-3.2,
        high_24h=62000,
        low_24h=60500
    )
    
    indicators = TechnicalIndicators(
        rsi_14=35.0,  # Oversold
        macd=-150,
        macd_signal=-120,
        macd_histogram=-30,
        atr_14=1200,
        sma_50=60000,
        ema_12=60500,
        ema_26=60200
    )
    
    results = rag.query(market_data, indicators, k=50)
    
    print("[OK] Query successful")
    print(f"   Similar patterns: {results['similar_patterns']}")
    print(f"   Success rate: {results['success_rate']:.1%}")
    print(f"   Avg outcome: {results['avg_outcome']:+.2f}%")
    print(f"   Context: {results['historical_context']}")
    
except Exception as e:
    print(f"[FAIL] Query failed: {e}")

# Test 4: Different market conditions
print("\n4. Testing with different conditions...")
try:
    # Overbought scenario
    indicators2 = TechnicalIndicators(
        rsi_14=75.0,  # Overbought
        macd=200,
        macd_signal=150,
        macd_histogram=50,
        atr_14=1000,
        sma_50=58000,
        ema_12=60000,
        ema_26=59000
    )
    
    results2 = rag.query(market_data, indicators2, k=50)
    print("[OK] Overbought scenario")
    print(f"   Success rate: {results2['success_rate']:.1%}")
    
except Exception as e:
    print(f"[FAIL] Second query failed: {e}")

# Test 5: Performance test
print("\n5. Performance test (10 queries)...")
try:
    import time
    start = time.time()
    
    for _ in range(10):
        rag.query(market_data, indicators, k=50)
    
    elapsed = time.time() - start
    avg_time = elapsed / 10 * 1000  # Convert to ms
    
    print(f"[OK] Average query time: {avg_time:.1f}ms")
    if avg_time < 100:
        print("   [OK] Performance excellent (< 100ms)")
    else:
        print("   [WARN]  Performance acceptable but could be optimized")
        
except Exception as e:
    print(f"[FAIL] Performance test failed: {e}")

print("\n" + "="*60)
print("CSV RAG TESTS COMPLETE")
print("="*60)