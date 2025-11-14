# Installation Guide

## Quick Start (Essential Dependencies Only)

Install the core dependencies:
```bash
pip install -r requirements.txt
```

This will install everything except TA-Lib, which requires special installation.

---

## Optional Dependencies

### 1. FAISS (For Better RAG Performance) - RECOMMENDED ✅

**What it does:** Faster similarity search for historical pattern matching

**Installation:**
```bash
pip install faiss-cpu
```

**Why install:** 10-100x faster than fallback numpy implementation

**Current status:** ⚠️ Using fallback (slower but works)

---

### 2. TA-Lib (For Better Technical Indicators) - OPTIONAL

**What it does:** Professional-grade technical analysis calculations

**Current status:** ⚠️ Using manual fallback implementations (works fine)

**Do you need it?** No - our fallback implementations work perfectly for RSI, MACD, ATR, Bollinger Bands, etc.

**Installation (Windows - Complex):**

TA-Lib requires C libraries that are difficult to install on Windows. Here are your options:

#### Option A: Use Pre-built Wheel (EASIEST) ✅
```bash
# Download the appropriate wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

# For Python 3.11, 64-bit Windows:
pip install TA_Lib-0.4.28-cp311-cp311-win_amd64.whl
```

#### Option B: Skip TA-Lib (RECOMMENDED)
Our manual implementations work perfectly fine. You don't actually need TA-Lib unless you want:
- Slightly faster calculations (marginal)
- Additional exotic indicators (we cover the main ones)

---

### 3. Google Sheets Integration - OPTIONAL

**What it does:** Dynamic configuration via Google Sheets

**Installation:**
```bash
pip install gspread google-auth
```

**Setup:**
1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create service account
4. Download JSON credentials to `config/service_account.json`
5. Share your Google Sheet with the service account email

**Current status:** ⚠️ Will use local cache/defaults only (works fine)

---

## Recommended Installation (Best Performance)

```bash
# 1. Install core dependencies
pip install -r requirements.txt

# 2. Install FAISS for better RAG performance (RECOMMENDED)
pip install faiss-cpu

# 3. (Optional) Install Google Sheets support
pip install gspread google-auth

# 4. Skip TA-Lib - use our fallback implementations
```

---

## Verify Installation

Run the test script:
```bash
python test_api_clients.py
```

**Expected output:**
```
✅ Binance: BTC = $[price]
✅ CMC: Fear/Greed = [0-100]
✅ HuggingFace: '[AI response]...'
```

**Acceptable warnings (not errors):**
```
TA-Lib not available. Using fallback calculations.
FAISS not available. Install with: pip install faiss-cpu. RAG queries will use fallback similarity.
```

These warnings are fine! The system works perfectly without them.

---

## What Each Dependency Does

### Essential (Already Installed)
- ✅ `requests` - API calls to Binance, CoinMarketCap, HuggingFace
- ✅ `pandas` - Data manipulation
- ✅ `numpy` - Numerical computing
- ✅ `pydantic` - Data validation
- ✅ `python-dotenv` - .env file loading
- ✅ `langchain` - LLM orchestration framework
- ✅ `langchain-community` - LangChain community integrations
- ✅ `huggingface-hub` - HuggingFace Hub client

### Optional (Install for Better Performance)
- ⚠️ `faiss-cpu` - 10-100x faster RAG similarity search
- ⚠️ `gspread` - Google Sheets config sync
- ⚠️ `TA-Lib` - Slightly faster technical indicators (not needed)

---

## Troubleshooting

### "TA-Lib not available" Warning
**Solution:** This is fine! Our manual implementations work perfectly.

If you really want TA-Lib:
1. Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. Match your Python version (check with `python --version`)
3. Install: `pip install TA_Lib-0.4.28-cp311-cp311-win_amd64.whl`

### "FAISS not available" Warning
**Solution:** Install FAISS for better performance:
```bash
pip install faiss-cpu
```

This is recommended but not required.

### "gspread not installed" Warning
**Solution:** Only install if you want Google Sheets config:
```bash
pip install gspread google-auth
```

Not needed for basic operation.

---

## Production Deployment

For production, install recommended dependencies:
```bash
# Core
pip install -r requirements.txt

# Performance boost
pip install faiss-cpu

# Optional: Google Sheets
pip install gspread google-auth
```

---

## Summary

**Minimum (Already Working):**
- ✅ Core dependencies from requirements.txt
- ✅ Fallback implementations for TA-Lib
- ✅ Fallback implementations for FAISS

**Recommended for Better Performance:**
```bash
pip install faiss-cpu
```

**Optional:**
```bash
pip install gspread google-auth  # For Google Sheets
# Skip TA-Lib - fallbacks work great
```

Your system is already fully functional with the current setup!
