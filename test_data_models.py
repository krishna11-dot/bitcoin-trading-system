from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from data_models.decisions import TradeDecision
from data_models.portfolio import PortfolioState
from data_models.sentiment import SentimentData
from datetime import datetime

print("Testing Pydantic Models...")

# Test MarketData
try:
    data = MarketData(price=61000, volume=1000000, timestamp=datetime.now().isoformat(), change_24h=-3.2)
    print(f"[OK] MarketData: ${data.price}")
except Exception as e:
    print(f"[FAIL] MarketData failed: {e}")

# Test Indicators
try:
    ind = TechnicalIndicators(rsi_14=28.5, macd=-150, macd_signal=-120, macd_histogram=-30, atr_14=1200, sma_50=60000, ema_12=60500, ema_26=60200)
    print(f"[OK] Indicators: RSI={ind.rsi_14}")
except Exception as e:
    print(f"[FAIL] Indicators failed: {e}")

# Test TradeDecision
try:
    dec = TradeDecision(action="buy", amount=500, entry_price=61000, stop_loss=59000, confidence=0.85, reasoning="RSI oversold", timestamp=datetime.now().isoformat(), strategy="dca")
    print(f"[OK] Decision: {dec.action}")
except Exception as e:
    print(f"[FAIL] Decision failed: {e}")

# Test validation (should fail)
try:
    bad = MarketData(price=-1000, volume=0, timestamp="", change_24h=0)
    print("[FAIL] Validation broken!")
except Exception:
    print("[OK] Validation working")

print("Tests complete!")