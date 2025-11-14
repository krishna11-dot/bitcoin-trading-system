# .env File Setup Guide

## ✅ YES - Put Testnet Keys in .env!

You use the **SAME .env file** for both Testnet and Real trading. The system automatically knows which to use based on `TESTNET_MODE=true/false`.

---

## 📝 Step-by-Step .env Setup

### STEP 1: Copy the Example File

```bash
cd c:\Users\krish\bitcoin-trading-system
copy config\.env.example .env
```

### STEP 2: Get FREE Binance Testnet Keys

1. Go to: **https://testnet.binance.vision/**
2. Login with **GitHub account**
3. Click "Generate HMAC_SHA256 Key"
4. **SAVE BOTH KEYS** (shown only once!):
   - API Key: `abc123def456...`
   - Secret Key: `xyz789uvw012...`
5. Click "Get Test Funds" → Receive free test BTC!

### STEP 3: Edit .env File

Open `.env` in Notepad and fill in:

```bash
# ============================================================================
# TESTNET CONFIGURATION (FREE - Use this first!)
# ============================================================================

# Your Binance TESTNET Keys (from testnet.binance.vision)
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here

# This tells the system to use TESTNET (not real money!)
TESTNET_MODE=true
TRADING_MODE=PAPER

# ============================================================================
# Optional: Telegram Alerts
# ============================================================================
# Get from @BotFather on Telegram (optional but recommended)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# ============================================================================
# Optional: Free LLM API Keys (for AI analysis)
# ============================================================================
# HuggingFace (get free key at https://huggingface.co/settings/tokens)
HUGGINGFACE_API_KEY=your_huggingface_key

# OpenRouter (get free key at https://openrouter.ai/keys)
OPENROUTER_API_KEY=your_openrouter_key

# ============================================================================
# Optional: Market Data APIs (Free Tier)
# ============================================================================
# CoinMarketCap (1 call per 5 minutes free)
COINMARKETCAP_API_KEY=your_cmc_key

# CryptoQuant (1 call per day free)
CRYPTOQUANT_API_KEY=your_cryptoquant_key

# ============================================================================
# System Settings (Leave as default)
# ============================================================================
LOG_LEVEL=INFO
MARKET_DATA_REFRESH_INTERVAL=60
PORTFOLIO_REFRESH_INTERVAL=300
```

---

## 🔄 How It Works

### When TESTNET_MODE=true (Recommended First):

```bash
TESTNET_MODE=true
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
```

✅ System connects to: `https://testnet.binance.vision`
✅ Uses: Testnet API keys
✅ Trades: Fake test Bitcoin (FREE)
✅ Risk: ZERO - No real money involved!

### When TESTNET_MODE=false (Only after testing!):

```bash
TESTNET_MODE=false
BINANCE_API_KEY=your_REAL_binance_key
BINANCE_API_SECRET=your_REAL_binance_secret
```

⚠️ System connects to: `https://api.binance.com`
⚠️ Uses: Real Binance API keys
⚠️ Trades: REAL Bitcoin with REAL money!
⚠️ Risk: REAL financial risk!

---

## 🎯 Your Complete .env File Should Look Like This:

```bash
# Binance Testnet (FREE)
BINANCE_API_KEY=GhJ8K2LmN9PqR5sT
BINANCE_API_SECRET=uV3wX6yZ4aB1cD7eF9gH2iJ5kL8mN0oP
TESTNET_MODE=true
TRADING_MODE=PAPER

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ
TELEGRAM_CHAT_ID=123456789

# LLMs (Optional)
HUGGINGFACE_API_KEY=hf_AbCdEfGhIjKlMnOpQrStUvWxYz
OPENROUTER_API_KEY=sk-or-v1-AbCdEfGhIjKlMnOpQrStUvWxYz

# Other APIs (Optional)
COINMARKETCAP_API_KEY=12345678-1234-1234-1234-123456789abc
CRYPTOQUANT_API_KEY=abcd1234efgh5678ijkl

# System
LOG_LEVEL=INFO
```

---

## ✅ Testing Your Setup

### Test 1: Verify .env Loads

```bash
python -c "from config import get_settings; s = get_settings(); print(f'Testnet: {s.TESTNET_MODE}')"
```

Expected output:
```
Testnet: True
```

### Test 2: Verify Binance Connection

```bash
python -c "from tools.binance_client import BinanceClient; c = BinanceClient(); print(f'Connected to: {c.base_url}')"
```

Expected output:
```
Connected to: https://testnet.binance.vision
```

### Test 3: Get Test BTC Price

```bash
python -c "from tools.binance_client import BinanceClient; c = BinanceClient(); print(f'BTC: ${c.get_current_price(\"BTCUSDT\").price:,.2f}')"
```

Expected output:
```
BTC: $62,450.00
```

---

## 🚀 When to Switch to Real Trading

**ONLY after:**

1. ✅ Testing on testnet for 1-2 weeks
2. ✅ Verifying stop-losses work correctly
3. ✅ Confirming emergency mode triggers at -25%
4. ✅ Understanding all system behaviors
5. ✅ Comfortable with the risk

**To switch:**

1. Get **REAL** Binance API keys from https://www.binance.com
2. In `.env`, update:
   ```bash
   BINANCE_API_KEY=your_REAL_key
   BINANCE_API_SECRET=your_REAL_secret
   TESTNET_MODE=false
   TRADING_MODE=LIVE
   ```
3. Start with **small budget** ($100-$500)
4. **Enable only "Spot Trading"** permissions
5. **Disable withdrawals** for safety!

---

## 🔒 Security Best Practices

### DO:
✅ Keep .env file private (already in .gitignore)
✅ Use testnet first
✅ Enable only "Spot Trading" permissions on Binance
✅ Disable withdrawal permissions
✅ Start with small amounts
✅ Monitor daily

### DON'T:
❌ Share API keys with anyone
❌ Commit .env to git
❌ Enable withdrawal permissions
❌ Start with large amounts
❌ Skip testnet testing

---

## 📞 Need Help?

### If testnet connection fails:
1. Verify keys are correct (no extra spaces)
2. Check `TESTNET_MODE=true` in .env
3. Ensure you generated keys from testnet.binance.vision (not regular Binance!)

### If can't get test funds:
- Testnet resets monthly
- Just regenerate keys and request funds again

### If system doesn't recognize testnet mode:
```bash
# Check your .env file has:
TESTNET_MODE=true

# NOT:
TESTNET_MODE=True  # Wrong capitalization
TESTNET_MODE=1     # Wrong format
```

---

## ✅ Summary

**To answer your question:** YES, you put testnet API keys in `.env`!

The system automatically knows which Binance server to use:
- `TESTNET_MODE=true` → Uses testnet.binance.vision (FREE)
- `TESTNET_MODE=false` → Uses api.binance.com (REAL MONEY)

**Same `.env` file, different keys for testnet vs real trading!**

Start with testnet, test thoroughly, then switch when ready! 🚀
