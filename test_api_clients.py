from tools.binance_client import BinanceClient
from tools.coinmarketcap_client import CoinMarketCapClient
from tools.huggingface_client import HuggingFaceClient

print("Testing API Clients...")

# Test Binance
try:
    binance = BinanceClient()
    price = binance.get_current_price()
    print(f"[OK] Binance: BTC = ${price.price}")
except Exception as e:
    print(f"[FAIL] Binance failed: {e}")

# Test CMC
try:
    cmc = CoinMarketCapClient()
    fg = cmc.get_fear_greed_index()
    print(f"[OK] CMC: Fear/Greed = {fg}")
except Exception as e:
    print(f"[FAIL] CMC failed: {e}")

# Test Hugging Face
try:
    hf = HuggingFaceClient()
    response = hf.generate_text("Is Bitcoin bullish?", max_tokens=20)
    print(f"[OK] HuggingFace: '{response[:50]}...'")
except Exception as e:
    print(f"[FAIL] HuggingFace failed: {e}")

print("\nAPI client tests complete!")