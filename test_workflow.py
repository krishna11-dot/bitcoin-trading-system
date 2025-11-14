"""
Test script for Prompt 12: LangGraph Workflow

Tests complete trading workflow with all agents.
"""

import asyncio
from graph.trading_workflow import run_trading_cycle, create_trading_workflow

print("=" * 60)
print("TESTING LANGGRAPH WORKFLOW (PROMPT 12)")
print("=" * 60)

# Test 1: Create workflow
print("\n1. Creating workflow...")
try:
    app = create_trading_workflow()
    print(f"   [OK] Workflow created")
    print(f"   Type: {type(app)}")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: Run complete cycle
print("\n2. Running complete trading cycle...")
print("   [WARN]  This will:")
print("   - Fetch real BTC data from Binance")
print("   - Call OpenRouter API 4 times (for 4 agents)")
print("   - Take ~30-60 seconds")
print()

try:
    # Configuration
    config = {
        "dca_threshold": 3.0,
        "dca_amount": 100,
        "atr_multiplier": 1.5,
        "max_position_size": 0.20,
        "max_total_exposure": 0.80,
        "emergency_stop": 0.25
    }
    
    # Run async
    result = asyncio.run(run_trading_cycle(config))
    
    print("\n" + "=" * 60)
    print("WORKFLOW RESULTS")
    print("=" * 60)
    
    # Display results
    print(f"\n[DATA] Market Data:")
    if result.get("market_data"):
        md = result["market_data"]
        print(f"   Price: ${md.price:,.2f}")
        print(f"   Change 24h: {md.change_24h:+.2f}%")
        print(f"   Volume: ${md.volume:,.0f}")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[ANALYSIS] Indicators:")
    if result.get("indicators"):
        ind = result["indicators"]
        print(f"   RSI: {ind.rsi_14:.1f}")
        print(f"   MACD: {ind.macd:.1f}")
        print(f"   ATR: {ind.atr_14:.1f}")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[ANALYZING] Market Analysis:")
    if result.get("market_analysis"):
        ma = result["market_analysis"]
        print(f"   Trend: {ma['trend']}")
        print(f"   Confidence: {ma['confidence']:.2f}")
        print(f"   Risk Level: {ma['risk_level']}")
        print(f"   Reasoning: {ma['reasoning'][:60]}...")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[SENTIMENT] Sentiment Analysis:")
    if result.get("sentiment_analysis"):
        sa = result["sentiment_analysis"]
        print(f"   Sentiment: {sa['sentiment']}")
        print(f"   Confidence: {sa['confidence']:.2f}")
        print(f"   Psychology: {sa['crowd_psychology']}")
        print(f"   Reasoning: {sa['reasoning'][:60]}...")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[WARN] Risk Assessment:")
    if result.get("risk_assessment"):
        ra = result["risk_assessment"]
        print(f"   Position: ${ra['recommended_position_usd']:.2f}")
        print(f"   Stop-loss: ${ra['stop_loss_price']:.2f}")
        print(f"   Risk %: {ra['risk_percent']:.2f}%")
        print(f"   Approved: {ra['approved']}")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[FINANCIAL] Final Decision:")
    if result.get("trade_decision"):
        td = result["trade_decision"]
        print(f"   Action: {td.action.upper()}")
        print(f"   Amount: ${td.amount}")
        print(f"   Entry Price: ${td.entry_price:,.2f}")
        print(f"   Confidence: {td.confidence:.2f}")
        print(f"   Strategy: {td.strategy}")
        print(f"   Reasoning: {td.reasoning[:60]}...")
    else:
        print(f"   [FAIL] Not available")
    
    print(f"\n[WARN] Errors: {len(result.get('errors', []))}")
    if result.get('errors'):
        for error in result['errors']:
            print(f"   - {error}")
    
    print("\n" + "=" * 60)
    print("[OK] WORKFLOW TEST COMPLETE")
    print("=" * 60)
    
    # Validation
    print(f"\n[ANALYZING] Validation:")
    
    checks = [
        (result.get("market_data") is not None, "Market data fetched"),
        (result.get("indicators") is not None, "Indicators calculated"),
        (result.get("market_analysis") is not None, "Market analysis completed"),
        (result.get("sentiment_analysis") is not None, "Sentiment analysis completed"),
        (result.get("risk_assessment") is not None, "Risk assessment completed"),
        (result.get("trade_decision") is not None, "Trade decision made"),
    ]
    
    passed = sum(1 for check, _ in checks if check)
    total = len(checks)
    
    for check, description in checks:
        status = "[OK]" if check else "[FAIL]"
        print(f"   {status} {description}")
    
    print(f"\n   Score: {passed}/{total}")
    
    if passed == total:
        print(f"\n ALL CHECKS PASSED!")
        print(f"\n Ready for Prompt 13: Guardrails")
    else:
        print(f"\n[WARN] Some checks failed. Review errors above.")
    
except Exception as e:
    print(f"\n[FAIL] Workflow failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)