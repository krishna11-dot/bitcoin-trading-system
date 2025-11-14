"""
Test script for Prompt 11: Remaining Agents with OpenRouter

Tests all 3 additional LangChain agents.
"""

from agents.sentiment_analysis_agent import analyze_sentiment
from agents.dca_decision_agent import make_dca_decision
from agents.risk_assessment_agent import assess_risk
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from data_models.sentiment import SentimentData
from data_models.portfolio import PortfolioState
from datetime import datetime

print("=" * 60)
print("TESTING ALL AGENTS (PROMPT 11 - OpenRouter)")
print("=" * 60)

# Test data
market_data = MarketData(
    price=61000,
    volume=1000000,
    timestamp=datetime.now().isoformat(),
    change_24h=-3.5,
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

sentiment_data = SentimentData(
    fear_greed_index=25,  # Fear
    social_volume="low",
    news_sentiment=-0.3,
    trending_score=45,
    timestamp=datetime.now().isoformat()
)

portfolio = PortfolioState(
    btc_balance=0.5,
    usd_balance=10000.0,
    active_positions=[],
    last_updated=datetime.now().isoformat()
)

# Test 1: Sentiment Agent
print("\n1. Testing Sentiment Analysis Agent...")
print("   Input: Fear/Greed=25 (fear), Social=low, RSI=32")
try:
    sentiment = analyze_sentiment(sentiment_data, market_data, indicators)
    
    print(f"\n   [OK] Result:")
    print(f"   - Sentiment: {sentiment['sentiment']}")
    print(f"   - Confidence: {sentiment['confidence']:.2f}")
    print(f"   - Psychology: {sentiment['crowd_psychology']}")
    print(f"   - Reasoning: {sentiment['reasoning'][:70]}...")
    
    # Validate
    assert sentiment['sentiment'] in ['bullish', 'bearish', 'neutral'], f"Invalid sentiment: {sentiment['sentiment']}"
    assert 0 <= sentiment['confidence'] <= 1, f"Invalid confidence: {sentiment['confidence']}"
    assert sentiment['crowd_psychology'] in ['fear', 'greed', 'neutral'], f"Invalid psychology: {sentiment['crowd_psychology']}"
    
    print(f"\n   [OK] Validation passed!")
    
except Exception as e:
    print(f"\n   [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: DCA Decision Agent
print("\n2. Testing DCA Decision Agent...")
print("   Input: Price drop -3.5%, RSI=32, $10k balance")
try:
    state = {
        "market_data": market_data,
        "indicators": indicators,
        "config": {
            "dca_threshold": 3.0,
            "dca_amount": 100
        },
        "portfolio_state": portfolio,
        "market_analysis": {"trend": "bearish", "confidence": 0.7},
        "sentiment_analysis": {"sentiment": "bearish", "confidence": 0.7},
        "rag_patterns": {
            "similar_patterns": 50,
            "success_rate": 0.65,
            "avg_outcome": 5.2
        }
    }
    
    decision = make_dca_decision(state)
    
    print(f"\n   [OK] Result:")
    print(f"   - Action: {decision.action}")
    print(f"   - Amount: ${decision.amount}")
    print(f"   - Entry Price: ${decision.entry_price}")
    print(f"   - Confidence: {decision.confidence:.2f}")
    print(f"   - Strategy: {decision.strategy}")
    print(f"   - Reasoning: {decision.reasoning[:70]}...")
    
    # Validate
    assert decision.action in ['buy', 'hold'], f"Invalid action: {decision.action}"
    assert decision.strategy == 'dca', f"Wrong strategy: {decision.strategy}"
    assert isinstance(decision.amount, (int, float)), f"Invalid amount type: {type(decision.amount)}"
    
    print(f"\n   [OK] Validation passed!")
    
except Exception as e:
    print(f"\n   [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Risk Assessment Agent
print("\n3. Testing Risk Assessment Agent...")
print("   Input: Portfolio=$35.5k, ATR=1200, Position limits")
try:
    config = {
        "atr_multiplier": 1.5,
        "max_position_size": 0.20,
        "max_total_exposure": 0.80,
        "emergency_stop": 0.25
    }
    
    # Add trend/confidence for risk agent
    market_analysis = {"trend": "bearish", "confidence": 0.7}
    
    risk = assess_risk(portfolio, market_data, indicators, config)
    
    print(f"\n   [OK] Result:")
    print(f"   - Recommended Position: ${risk['recommended_position_usd']:.2f}")
    print(f"   - Stop-loss Price: ${risk['stop_loss_price']:.2f}")
    print(f"   - Risk Percent: {risk['risk_percent']:.2f}%")
    print(f"   - Approved: {risk['approved']}")
    print(f"   - Reasoning: {risk['reasoning'][:70]}...")
    
    # Validate
    assert isinstance(risk['recommended_position_usd'], (int, float)), f"Invalid position type"
    assert isinstance(risk['stop_loss_price'], (int, float)), f"Invalid stop-loss type"
    assert isinstance(risk['approved'], bool), f"Invalid approved type: {type(risk['approved'])}"
    assert 0 <= risk['risk_percent'] <= 100, f"Invalid risk percent: {risk['risk_percent']}"
    
    print(f"\n   [OK] Validation passed!")
    
except Exception as e:
    print(f"\n   [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("ALL AGENT TESTS COMPLETE")
print("=" * 60)

print("\n[DATA] Summary:")
print("[OK] Sentiment Agent - Analyzes fear/greed and social sentiment")
print("[OK] DCA Agent - Makes buy/hold decisions based on strategy")
print("[OK] Risk Agent - Calculates position sizing and stop-losses")

print("\n If all 3 agents passed, you're ready for Prompt 12!")
print("   (LangGraph Workflow - connects all agents together)")