"""Test Market Analysis Agent (Prompt 10)"""

from agents.market_analysis_agent import analyze_market, load_prompt
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from datetime import datetime

print("=" * 60)
print("TESTING MARKET ANALYSIS AGENT")
print("=" * 60)

# Test 1: Load prompt
print("\n1. Loading prompt template...")
try:
    prompt = load_prompt("market_analysis_agent.txt")
    print(f"   [OK] Loaded: {len(prompt)} chars")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")
    exit(1)

# Test 2: Analyze market
print("\n2. Analyzing market (calls HuggingFace API)...")
try:
    market_data = MarketData(
        price=61000,
        volume=1000000,
        timestamp=datetime.now().isoformat(),
        change_24h=-3.2,
        high_24h=62000,
        low_24h=60500
    )
    
    indicators = TechnicalIndicators(
        rsi_14=32.0,
        macd=-150,
        macd_signal=-120,
        macd_histogram=-30,
        atr_14=1200,
        sma_50=60000,
        ema_12=60500,
        ema_26=60200
    )
    
    print(f"   Input: Price=${market_data.price}, RSI={indicators.rsi_14}")
    
    result = analyze_market(market_data, indicators)
    
    print(f"\n   [OK] Result:")
    print(f"   - Trend: {result['trend']}")
    print(f"   - Confidence: {result['confidence']:.2f}")
    print(f"   - Risk: {result['risk_level']}")
    print(f"   - Reasoning: {result['reasoning'][:80]}...")
    
    # Validate
    assert result['trend'] in ['bullish', 'bearish', 'neutral']
    assert 0 <= result['confidence'] <= 1
    print(f"\n   [OK] Validation passed!")
    
except Exception as e:
    print(f"   [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("[OK] PROMPT 10 COMPLETE! Ready for Prompt 11.")
print("=" * 60)