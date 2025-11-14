# Autonomous Bitcoin Trading System

An intelligent multi-agent LLM (Large Language Model) system for autonomous Bitcoin trading with **adaptive strategy selection** (DCA/SWING/DAY), combining real-time market analysis, historical pattern matching, on-chain analytics, and AI-powered decision making with comprehensive safety guardrails and automated position management.

> **🔒 Safe Paper Trading by Default**: This system uses **Binance Testnet** (https://testnet.binance.vision) for safe paper trading with zero financial risk. Test strategies thoroughly before considering production deployment.

## Description

This system uses a **7-node LangGraph workflow** with specialized AI agents to analyze Bitcoin market conditions from multiple perspectives (technical indicators, sentiment analysis, risk assessment, historical patterns, market regime detection) and **automatically selects optimal trading strategies** based on real-time conditions. The entire system operates at $0/month using free APIs and open-source LLMs, with FAISS-accelerated RAG (Retrieval-Augmented Generation) for 10x faster historical pattern matching.

**Key Innovations**:
1. **Adaptive Strategy Selection**: Automatically switches between DCA (conservative), SWING (moderate), and DAY (aggressive) strategies based on detected market regime (crisis, trending, ranging, high volatility)
2. **Position Manager**: ATR (Average True Range) based stop-losses, budget allocation limits per strategy, emergency safeguards at -25% portfolio loss
3. **RAG + On-Chain Fusion**: Combines traditional technical analysis with RAG over historical market data and real-time blockchain metrics to provide data-driven trading decisions that learn from past market conditions

## Tech Stack

### Core Framework
- **Python 3.10+**: Core programming language
- **LangChain 0.3.0**: Agent framework and LLM orchestration
- **LangGraph**: Multi-agent workflow orchestration (6-node state machine)
- **Pydantic v2**: Type-safe data validation and schemas
- **UV**: Fast Python package management

### AI & LLM (Large Language Models)
- **HuggingFace API**: Free LLM inference (Qwen/Qwen2.5-Coder-32B-Instruct for market analysis)
- **OpenRouter API**: Free LLM inference (mistralai/mistral-7b-instruct:free for sentiment, risk, DCA, strategy selection)
- **FAISS 1.12.0**: Facebook's vector search library for 10x faster RAG (Retrieval-Augmented Generation) queries

### Data Sources (All FREE)
- **Binance Testnet API**: Real-time Bitcoin price, volume, 24h change (FREE, testnet for safe testing, 1200 req/min)
  - Uses https://testnet.binance.vision by default (paper trading environment)
  - Can be switched to production Binance API by setting `TESTNET_MODE=False` in config
- **CoinMarketCap API**: Market sentiment, Fear & Greed Index (FREE, 10,000 req/month)
- **Blockchain.com API**: On-chain metrics (hash rate, mempool, network health) (FREE, unlimited)
- **Yahoo Finance**: Historical price data fallback (FREE, unlimited)

### Cloud Integration & Notifications (FREE)
- **Google Sheets API**: Dynamic configuration management in the cloud (FREE, 60 reads/min)
  - Live parameter updates without code changes
  - Synchronized caching with local fallback
  - Smart rate limiting (1 call/min, 0.03% of quota)
- **Telegram Bot API**: Real-time trade notifications and alerts (FREE, unlimited)
  - Instant alerts for trade executions
  - System status updates
  - Error notifications

### Data Processing
- **Pandas**: CSV processing and historical data analysis
- **NumPy 1.26.4**: Technical indicator calculations
- **RAG Pipeline**: Custom CSV-based retrieval-augmented generation with FAISS indexing

## Key Features

### Multi-Agent Intelligence
- **7-Node LangGraph Workflow**: Coordinated state machine for parallel and sequential agent execution
- **5 Specialized AI Agents**:
  - **Strategy Switcher**: Detects market regime and selects optimal strategy (DCA/SWING/DAY)
  - **Market Analysis**: Analyzes technical indicators with RAG-enhanced historical pattern matching
  - **Sentiment Analysis**: Evaluates market psychology and Fear & Greed Index
  - **Risk Assessment**: Analyzes on-chain metrics and volatility for position sizing
  - **DCA Decision**: Makes final buy/hold decisions based on all inputs
- **RAG-Enhanced Analysis**: FAISS-accelerated similarity search over 1000+ historical patterns (10x faster)
- **Multi-Source Data Fusion**: Combines technical indicators, sentiment, on-chain metrics, historical patterns, and market regime detection
- **External Prompts**: All agent prompts in `prompts/*.txt` for easy iteration without code changes

### Trading Strategies (Adaptive Selection)
The system **automatically selects** the optimal strategy every cycle based on detected market conditions:

- **DCA (Dollar-Cost Averaging)** - Conservative accumulation:
  - **When**: Crisis markets, extreme fear, major price crashes
  - **Stop-Loss**: 2.0x ATR (Average True Range) - wide buffer for volatility
  - **Budget**: 50% of available capital per trade
  - **Why**: Accumulate BTC during crashes without trying to time exact bottoms

- **SWING Trading** - Moderate trend-following:
  - **When**: Clear trending markets (up or down), moderate volatility
  - **Stop-Loss**: 1.5x ATR - balanced risk management
  - **Budget**: 40% of available capital per trade
  - **Why**: Ride medium-term trends (days to weeks) with defined exits

- **DAY Trading** - Aggressive volatility capture:
  - **When**: Ranging/consolidating markets, high intraday volatility
  - **Stop-Loss**: 1.0x ATR - tight risk management
  - **Budget**: 30% of available capital per trade
  - **Why**: Capture short-term price swings (hours to days) with quick exits

**Adaptive DCA Triggers**: System calculates dynamic entry thresholds (1.5%-3.5% price drop) based on current volatility instead of fixed 3% threshold

### Data & Analysis
- **Real-Time Market Data**: Live Bitcoin price, volume, 24h changes from Binance Testnet (safe testing environment)
- **Technical Indicators**: RSI, MACD, ATR, SMA, EMA, Bollinger Bands calculated from price history
- **On-Chain Metrics**: Network hash rate, mempool size, block data from Blockchain.com
- **Sentiment Analysis**: Fear & Greed Index, market sentiment from CoinMarketCap
- **CSV RAG Pipeline**: 1000+ historical patterns with FAISS vector indexing for fast similarity search

### Safety & Reliability
- **Type-Safe Validation**: Comprehensive Pydantic v2 models prevent invalid data propagation
- **Multi-Layer Guardrails**: Amount limits, position limits, balance checks, sanity validation
- **Rate Limiting**: Smart rate limiters with circuit breakers for all external APIs
- **Error Handling**: Retry logic with exponential backoff for transient failures
- **Logging**: Structured logging with clear status markers ([OK], [FAIL], [WARN])
- **Telegram Notifications**: Real-time alerts for trades, errors, and system status
- **Google Sheets Configuration**: Live parameter updates without restarting the system
  - Change DCA thresholds, position sizes, risk limits on-the-fly
  - Synchronized caching for offline operation
  - Fallback to local config if Google Sheets unavailable

### Cost Optimization
- **100% FREE Operation**: $0/month - all APIs and LLMs are free tier
- **No CryptoQuant**: Replaced $99-399/month paid service with free Blockchain.com API
- **No Paid Vector DB**: FAISS (open-source) replaces paid alternatives like Pinecone
- **Free LLM Inference**: HuggingFace and OpenRouter free tiers (sufficient for DCA trading)

## Architecture Overview

The system operates as a **LangGraph state machine** with 7 nodes orchestrating the adaptive trading workflow:

```
TRADING CYCLE (Every 30 minutes)
    |
    +-- CONFIGURATION SYNC (Google Sheets API - Optional)
    |       |-- Load trading parameters from cloud (DCA threshold, position limits, etc.)
    |       |-- Synchronized caching with local fallback
    |       └─> Output: Trading configuration
    |
    +-- NODE 1: PARALLEL DATA COLLECTION (Concurrent API calls)
    |       |-- Binance Testnet API: Current BTC price, volume, 24h change (paper trading)
    |       |-- CoinMarketCap: Sentiment, Fear & Greed Index
    |       +-- Blockchain.com: On-chain metrics (hash rate, mempool)
    |       └─> Output: Real-time market snapshot
    |
    +-- NODE 2: TECHNICAL INDICATORS (NumPy calculations)
    |       |-- Calculate RSI (Relative Strength Index, 14-period, 0-100 scale)
    |       |-- Calculate MACD (Moving Average Convergence Divergence, 12/26/9)
    |       |-- Calculate ATR (Average True Range, 14-period volatility measure)
    |       +-- Calculate SMAs, EMAs, Bollinger Bands
    |       └─> Output: Full technical indicator suite
    |
    +-- NODE 3: STRATEGY SELECTION (NEW - OpenRouter LLM)
    |       |-- Detect Market Regime (crisis, trending_up/down, ranging, high_volatility)
    |       |-- Engineer 8 Custom Features (price momentum, volatility ratio, RSI strength, etc.)
    |       |-- LLM Selects Top 3 Most Relevant Features
    |       |-- Select Optimal Strategy: DCA (conservative) / SWING (moderate) / DAY (aggressive)
    |       +-- Calculate Adaptive DCA Trigger (1.5%-3.5% based on volatility)
    |       └─> Output: strategy="dca/swing/day", regime, confidence, adaptive_trigger
    |
    +-- NODE 4: MARKET ANALYSIS AGENT (HuggingFace LLM)
    |       |-- Analyzes technical indicators with context
    |       |-- RAG: Queries 50 similar historical patterns (FAISS vector search)
    |       +-- Output: Market trend, recommended action, confidence
    |       └─> Feeds into final decision
    |
    +-- NODE 5: SENTIMENT ANALYSIS AGENT (OpenRouter LLM)
    |       |-- Analyzes Fear & Greed Index (0-100 scale)
    |       |-- Interprets market psychology and sentiment signals
    |       +-- Output: Sentiment assessment (bullish/bearish/fear/greed), trading bias
    |       └─> Feeds into final decision
    |
    +-- NODE 6: RISK ASSESSMENT AGENT (OpenRouter LLM)
    |       |-- Analyzes on-chain network health (hash rate, mempool, block data)
    |       |-- Evaluates volatility (ATR) and market stability
    |       +-- Output: Risk level (low/medium/high), position sizing recommendation
    |       └─> Feeds into final decision
    |
    +-- NODE 7: DCA DECISION AGENT (OpenRouter LLM)
            |-- Combines ALL inputs: market, sentiment, risk, RAG patterns, selected strategy
            |-- Applies strategy-specific rules (DCA: price drop + RSI, SWING: trend, DAY: volatility)
            |-- Checks balance and multi-layer guardrails
            +-- Output: BUY $X USD or HOLD decision with full reasoning
            └─> Execution via Position Manager
                    |
                    +-- TRADE EXECUTION
                    |       |-- Position Manager: ATR-based stop-losses, budget tracking
                    |       +-- Telegram Notifications (Optional): Real-time trade alerts
                    |       └─> Output: Position opened/closed, notifications sent
```

**Data Flow**:
1. **Parallel Collection**: Market data fetched simultaneously from 3 sources
2. **Indicators**: Technical indicators calculated from price history
3. **Strategy Selection**: NEW node detects regime and selects optimal strategy
4. **Agent Analysis**: 3 specialized agents (Market, Sentiment, Risk) analyze concurrently
5. **Decision**: Final agent synthesizes all inputs and makes buy/hold decision
6. **Execution**: Position Manager executes with ATR-based stop-losses

**Why 7 Nodes**: Adding Strategy Switcher (Node 3) enables adaptive trading instead of fixed DCA, automatically adjusting to market conditions.

**Full Architecture**: See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) and [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) for complete system diagrams, agent details, and integration guide.

## Installation

### Quick Start

```bash
# Prerequisites: Python 3.10+, UV package manager

# 1. Clone the repository
git clone <repository-url>
cd bitcoin-trading-system

# 2. Create virtual environment and install dependencies
uv venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# 3. Install all packages (includes FAISS for fast RAG)
uv pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (all FREE tiers):
#   - BINANCE_API_KEY (optional - Binance Testnet key from https://testnet.binance.vision/)
#   - BINANCE_API_SECRET (optional - Binance Testnet secret)
#   - TESTNET_MODE=True (default - uses Binance Testnet for safe paper trading)
#   - COINMARKETCAP_API_KEY (free tier: 10k req/month)
#   - HUGGINGFACE_API_KEY (free tier)
#   - OPENROUTER_API_KEY (free tier)
#   - TELEGRAM_BOT_TOKEN (optional - for real-time notifications)
#   - TELEGRAM_CHAT_ID (optional - your Telegram chat ID)
#   - GOOGLE_SHEET_URL (optional - for cloud configuration)
#   - No Blockchain.com key needed (public API)

# 5. Prepare historical data
# Download Bitcoin_Historical_Data_Raw.csv and place in data/ directory
# This is used for RAG (Retrieval-Augmented Generation) historical pattern matching
# See INSTALLATION.md for data source instructions

# 6. Run the system
uv run python main.py
```

### Detailed Installation

See [INSTALLATION.md](INSTALLATION.md) for:
- Complete step-by-step setup guide
- API key registration instructions (all free)
- Historical data preparation
- Configuration file setup
- Troubleshooting common issues

### Non-Technical User Guide

See [NON_TECHNICAL_USER_GUIDE.md](NON_TECHNICAL_USER_GUIDE.md) for:
- Plain English explanation of how the system works
- What DCA, RSI, MACD, ATR mean
- Step-by-step trading cycle breakdown
- Understanding system output
- Common questions answered

## Project Structure

**Why This Structure?** The codebase is organized into logical layers: configuration, data models, AI agents, tools/utilities, safety guardrails, and workflow orchestration. Each folder has a specific purpose in the trading pipeline.

```
bitcoin-trading-system/
├── config/                      # CONFIGURATION: System settings and parameters
│   ├── __init__.py             # Why: Centralized configuration management
│   ├── api_config.py           # API keys, endpoints, rate limits for all external services
│   ├── settings.py             # Global settings singleton (LLM models, trading params)
│   └── trading_config.py       # DCA settings, thresholds, position limits, strategy budgets
│
├── prompts/                     # LLM PROMPTS: External prompt templates (no code changes needed)
│   ├── __init__.py             # Why: Separate prompts from code for easy A/B testing
│   ├── market_analysis_agent.txt    # Technical analysis prompt with RAG context
│   ├── sentiment_analysis_agent.txt # Sentiment analysis prompt (Fear & Greed)
│   ├── risk_assessment_agent.txt    # Risk evaluation prompt (on-chain + volatility)
│   ├── dca_decision_agent.txt       # DCA strategy prompt (CRITICAL: USD amounts!)
│   └── strategy_switcher.txt        # Feature selection prompt for regime detection
│
├── data_models/                 # DATA MODELS: Type-safe Pydantic v2 schemas
│   ├── __init__.py             # Why: Enforce data contracts, catch errors early
│   ├── market_data.py          # MarketData, TechnicalIndicators (RSI, MACD, ATR)
│   ├── decisions.py            # TradeDecision (buy/sell/hold with validation)
│   ├── portfolio.py            # PortfolioState (BTC/USD balances, positions)
│   └── positions.py            # Position (open trades with stop-losses, P&L tracking)
│
├── agents/                      # AI AGENTS: LangChain-powered decision makers
│   ├── __init__.py             # Why: 5 specialized agents for divide-and-conquer analysis
│   ├── market_analysis_agent.py      # Analyzes technicals + RAG (HuggingFace)
│   ├── sentiment_analysis_agent.py   # Analyzes market psychology (OpenRouter)
│   ├── risk_assessment_agent.py      # Evaluates on-chain + volatility (OpenRouter)
│   ├── dca_decision_agent.py         # Final buy/hold decision (OpenRouter)
│   ├── rag_enhanced_market_analyst.py # Market agent with FAISS RAG integration
│   └── rag_enhanced_strategy_agent.py # Strategy recommendations with RAG
│
├── tools/                       # TOOLS: External integrations and utilities
│   ├── __init__.py             # Why: Reusable components for data, calculations, APIs
│   ├── strategy_switcher.py    # [NEW] Adaptive strategy selection (DCA/SWING/DAY)
│   ├── position_manager.py     # [NEW] Trade execution with ATR stop-losses
│   ├── rate_limiter.py         # Smart rate limiting with circuit breakers
│   ├── binance_client.py       # Binance API (price, volume, 24h change)
│   ├── coinmarketcap_client.py # CoinMarketCap API (sentiment, Fear & Greed)
│   ├── yfinance_client.py      # Yahoo Finance (historical price data fallback)
│   ├── bitcoin_onchain_analyzer.py  # FREE on-chain analytics (Blockchain.com)
│   ├── huggingface_client.py   # HuggingFace LLM client (free tier)
│   ├── openrouter_client.py    # OpenRouter LLM client (free tier)
│   ├── indicator_calculator.py # Technical indicator calculations (RSI, MACD, ATR)
│   ├── csv_rag_pipeline.py     # FAISS-accelerated RAG retriever (historical patterns)
│   └── google_sheets_sync.py   # Dynamic config from Google Sheets (optional)
│
├── guardrails/                  # SAFETY: Multi-layer validation before execution
│   ├── __init__.py             # Why: Prevent catastrophic trades, validate all decisions
│   ├── position_limits.py      # Max position size checks (10 BTC, $10k per trade)
│   ├── balance_validation.py   # Sufficient balance checks (prevent overdraft)
│   ├── sanity_checks.py        # Trade reasonableness validation (detect outliers)
│   └── amount_validator.py     # USD/BTC amount validation (prevent unit errors)
│
├── monitoring/                  # MONITORING: Position tracking and performance
│   ├── __init__.py             # Why: Track portfolio state, manage open positions
│   └── position_manager.py     # Portfolio state, position tracking, P&L calculations
│
├── graph/                       # WORKFLOW: LangGraph orchestration (state machine)
│   ├── __init__.py             # Why: Coordinate 7-node workflow with state management
│   ├── trading_workflow.py     # 7-node state machine definition (data → strategy → decision)
│   └── state_models.py         # TradingState (workflow state passed between nodes)
│
├── data/                        # DATA: Historical data and caches (gitignored)
│   ├── .gitkeep
│   ├── Bitcoin_Historical_Data_Raw.csv  # 1000+ historical patterns for RAG
│   ├── positions/              # Position tracking files (JSON)
│   └── rag/                    # FAISS index and embeddings cache
│
├── docs/                        # DOCUMENTATION: Technical guides
│   ├── ONCHAIN_ANALYZER_USAGE.md
│   ├── ONCHAIN_INTEGRATION_SUMMARY.md
│   └── API_INTEGRATION_PATTERNS.md
│
├── main.py                      # ENTRY POINT: Main application loop (30-minute cycles)
├── requirements.txt             # Python dependencies (LangChain, FAISS, NumPy, etc.)
├── pyproject.toml              # Project metadata for UV package manager
├── .env.example                # Environment variables template (API keys)
├── .gitignore
├── README.md                   # This file - System overview
├── SYSTEM_ARCHITECTURE.md      # Complete architecture documentation
├── INTEGRATION_COMPLETE.md     # Strategy Switcher + Position Manager integration guide
└── NON_TECHNICAL_USER_GUIDE.md # Plain English user guide
```

**Key Files Explained**:
- **[main.py](main.py)**: Entry point - orchestrates 30-minute trading cycles, monitors positions, executes trades
- **[graph/trading_workflow.py](graph/trading_workflow.py)**: LangGraph state machine - defines 7-node workflow (data → indicators → strategy → analysis → decision)
- **[tools/strategy_switcher.py](tools/strategy_switcher.py)**: [NEW] Adaptive strategy selection - detects market regime, engineers features, selects DCA/SWING/DAY
- **[tools/position_manager.py](tools/position_manager.py)**: [NEW] Trade execution - opens positions with ATR-based stop-losses, tracks P&L
- **[prompts/dca_decision_agent.txt](prompts/dca_decision_agent.txt)**: CRITICAL prompt - defines DCA strategy logic (must return USD amounts!)
- **[tools/csv_rag_pipeline.py](tools/csv_rag_pipeline.py)**: FAISS-accelerated RAG - queries historical patterns for similar market conditions
- **[config/trading_config.py](config/trading_config.py)**: Trading parameters - DCA threshold, amounts, position limits, strategy budgets

## Configuration

### Trading Parameters (config/trading_config.py)

```python
# DCA Strategy Configuration
DCA_AMOUNT = 100.0           # USD amount to invest per buy ($100)
DCA_THRESHOLD = -3.0         # Price drop % to trigger buy (-3%)
RSI_OVERSOLD = 40            # RSI threshold for oversold (0-100)

# Position Limits
MAX_POSITION_SIZE = 10.0     # Max BTC per trade
MAX_USD_PER_TRADE = 10000    # Max USD per trade

# Trading Cycle
TRADING_INTERVAL = 900       # 15 minutes (in seconds)
```

### API Keys (.env)

```bash
# LLM Providers (both FREE tier)
HUGGINGFACE_API_KEY=hf_xxxxx     # Get from: https://huggingface.co/settings/tokens
OPENROUTER_API_KEY=sk-or-xxxxx   # Get from: https://openrouter.ai/keys

# Market Data (optional but recommended)
BINANCE_API_KEY=xxxxx            # Optional - Binance Testnet: https://testnet.binance.vision/
BINANCE_API_SECRET=xxxxx         # Optional - Binance Testnet secret
TESTNET_MODE=True                # Default: True (uses testnet for safe paper trading)
COINMARKETCAP_API_KEY=xxxxx      # FREE tier: https://coinmarketcap.com/api/

# Cloud Integration (optional)
TELEGRAM_BOT_TOKEN=xxxxx         # Optional - for real-time notifications
TELEGRAM_CHAT_ID=xxxxx           # Optional - your Telegram chat ID
GOOGLE_SHEET_URL=xxxxx           # Optional - for cloud configuration sync

# No Blockchain.com key needed - public API is free
```

## Usage

### Running the System

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Run the trading system
uv run python main.py
```

### What It Does

The system runs continuously with 15-minute cycles:

1. **Fetches Data** (5 seconds):
   - Current Bitcoin price from Binance Testnet (paper trading environment)
   - Sentiment from CoinMarketCap
   - On-chain metrics from Blockchain.com

2. **Calculates Indicators** (1 second):
   - RSI, MACD, ATR from 100 historical candles

3. **AI Analysis** (15 seconds):
   - Market Agent: Analyzes technicals + queries 50 similar historical patterns
   - Sentiment Agent: Interprets Fear & Greed Index
   - Risk Agent: Evaluates on-chain health and volatility

4. **DCA Decision** (3 seconds):
   - Combines all analyses
   - Applies DCA rules: Buy if price dropped 3%+ AND RSI < 40
   - Validates guardrails (balance, limits, sanity)

5. **Logs Result**:
   ```
   [OK] Decision: HOLD - Price dropped only 1.2% (need 3%)
   [OK] Next check in 15 minutes
   ```

### Example Output

```
[STARTING] Bitcoin DCA Trading System
[OK] Loaded configuration: DCA $100 on -3% drops
[OK] Loaded RAG data: 1000 historical patterns (FAISS accelerated)

[PROCESSING] Cycle 1/∞
  [OK] Price: $98,543 (-2.1% 24h)
  [OK] RSI: 38 (oversold signal)
  [OK] MACD: Bearish crossover
  [OK] RAG: Found 50 similar patterns, 65% success rate
  [OK] Sentiment: Fear & Greed 32 (Fear)
  [OK] On-Chain: Hash rate stable, mempool normal

  [DECISION] BUY $100.00 USD
  [OK] Reasoning: Price dropped 2.1% close to threshold, RSI oversold (38), historical patterns show 65% success rate in similar conditions
  [OK] Confidence: 78%

  [WARN] Execution skipped (paper trading mode)

[OK] Cycle completed in 24 seconds
[OK] Next cycle in 15 minutes
```

### Understanding the Output

See [NON_TECHNICAL_USER_GUIDE.md](NON_TECHNICAL_USER_GUIDE.md) for detailed explanations of:
- What each indicator means (RSI, MACD, ATR)
- How RAG historical pattern matching works
- What confidence scores represent
- When the system buys vs holds

## Trading Strategy

### DCA (Dollar-Cost Averaging)

This system implements a **smart DCA strategy** - not blind periodic buying, but intelligent triggered buying:

**Traditional DCA**: Buy $100 every week regardless of price
**Smart DCA (this system)**: Buy $100 only when conditions are favorable

**Trigger Conditions (BOTH must be true)**:
1. **Price Drop**: Bitcoin price must have dropped 3% or more in 24 hours
2. **Oversold Signal**: RSI must be below 40 (indicating oversold conditions)

**Why This Works**:
- Buys the dip (price drops)
- Confirms oversold conditions (RSI < 40)
- Uses historical patterns (RAG) to validate similar past conditions
- Risk-adjusted: Lower confidence = smaller position size

**Example Decision Logic**:
```
Price: $100,000 → $97,000 (-3.0% drop) ✓ Meets threshold
RSI: 35 ✓ Below 40 (oversold)
RAG: 50 similar patterns found, 70% led to profit
→ DECISION: BUY $100 USD (confidence: 85%)

Price: $100,000 → $99,500 (-0.5% drop) ✗ Only 0.5% drop
RSI: 65 ✗ Above 40 (overbought)
→ DECISION: HOLD (wait for better entry)
```

**Advantages Over Blind DCA**:
- Lower average entry price (buys dips, not peaks)
- Historical validation (RAG confirms similar conditions worked before)
- Risk management (guardrails prevent excessive position sizes)
- Adaptive (confidence-based position sizing)

## Safety Features

### Multi-Layer Guardrails

1. **Amount Validation** (guardrails/amount_validator.py):
   - Ensures LLM returns USD amounts, not BTC quantities
   - Max single trade: $10,000 USD or 10 BTC (whichever is less)
   - Min trade: $10 USD to avoid dust

2. **Balance Checks** (guardrails/balance_validation.py):
   - Verifies sufficient USD balance before buy orders
   - Prevents overdraft situations

3. **Position Limits** (guardrails/position_limits.py):
   - Max BTC per trade: 10 BTC
   - Max USD per trade: $10,000
   - Prevents catastrophic large positions

4. **Sanity Checks** (guardrails/sanity_checks.py):
   - Validates price reasonableness (not extreme outliers)
   - Checks indicator validity (RSI 0-100, etc.)
   - Ensures data freshness (not stale prices)

5. **Rate Limiting** (tools/rate_limiter.py):
   - Smart rate limiters for all external APIs
   - Circuit breakers on repeated failures
   - Prevents API ban from over-requesting

6. **LLM Validation**:
   - Pydantic v2 schemas enforce correct JSON structure
   - Type checking on all agent responses
   - Retry logic (3 attempts) on invalid responses

### What Gets Rejected

```
[FAIL] Trade amount 100.0000 BTC exceeds limit (10 BTC)
→ LLM returned BTC instead of USD - REJECTED

[FAIL] Insufficient balance: Need $100, have $50
→ Not enough cash - REJECTED

[FAIL] RSI value 150 invalid (must be 0-100)
→ Bad indicator data - REJECTED

[FAIL] Price $1,000,000 is 10x above recent average
→ Extreme outlier - REJECTED
```

## Monitoring & Performance

### Logging

All output uses clear text markers (no emojis):
- `[OK]`: Successful operation
- `[FAIL]`: Error occurred
- `[WARN]`: Warning (non-critical)
- `[STARTING]`: Process beginning
- `[PROCESSING]`: Operation in progress
- `[DECISION]`: Trading decision made

### Performance Tracking (monitoring/performance_tracker.py)

Tracks key metrics:
- **Total trades executed**: Count of buy orders
- **Win rate**: % of profitable trades
- **Average return**: Mean return per trade
- **Max drawdown**: Largest peak-to-trough decline
- **Sharpe ratio**: Risk-adjusted return

### Position Management (monitoring/position_manager.py)

Maintains portfolio state:
- Current BTC holdings
- Current USD balance
- Average entry price
- Unrealized P&L
- Realized P&L

### Rate Limit Dashboard

Real-time API usage stats:
```bash
uv run python -c "from tools import print_rate_limit_dashboard; print_rate_limit_dashboard()"
```

Output:
```
Rate Limit Dashboard
====================
Binance: 45/1200 requests (last hour)
CoinMarketCap: 12/333 requests (last hour)
HuggingFace: 8/60 requests (last hour)
OpenRouter: 24/200 requests (last hour)
```

## System Requirements

### Minimum Requirements
- **Python**: 3.10 or higher
- **RAM**: 2 GB (FAISS indexing uses ~500 MB)
- **Disk**: 500 MB (includes dependencies and historical data)
- **Internet**: Stable connection for API calls

### Recommended
- **Python**: 3.11+ (better performance)
- **RAM**: 4 GB (comfortable for concurrent API calls)
- **CPU**: 2+ cores (parallel data collection)

## Cost Breakdown

| Component | Service | Cost | Rate Limit |
|-----------|---------|------|------------|
| **LLM Inference** | HuggingFace (free tier) | $0/month | 60 req/hour |
| **LLM Inference** | OpenRouter (free tier) | $0/month | 200 req/day |
| **Market Data** | Binance Testnet (paper trading) | $0/month | 1200 req/min |
| **Sentiment** | CoinMarketCap (free) | $0/month | 10,000 req/month |
| **On-Chain** | Blockchain.com (free) | $0/month | Unlimited |
| **Historical** | Yahoo Finance (free) | $0/month | Unlimited |
| **RAG Search** | FAISS (open-source) | $0/month | N/A |
| **Total** | - | **$0/month** | - |

**Previous system**: $99-399/month (CryptoQuant) + $50-200/month (paid vector DB) = **$149-599/month**
**Savings**: **$1,788 - $7,188/year**

## Testing

### Test Individual Components

```bash
# Test RAG pipeline with FAISS
uv run python test_faiss_working.py

# Test all agents
uv run python test_all_langchain_agents.py

# Test guardrails
uv run python test_guardrails.py

# Test API clients
uv run python test_api_clients.py

# Test indicators
uv run python test_indicators.py
```

### Test Full Workflow

```bash
# Dry run (no actual trades)
uv run python test_trading_workflow.py

# Live system (paper trading mode)
uv run python main.py
```

## Documentation

### User Documentation
- **[NON_TECHNICAL_USER_GUIDE.md](NON_TECHNICAL_USER_GUIDE.md)**: Plain English guide for beginners
- **[INSTALLATION.md](INSTALLATION.md)**: Step-by-step setup instructions
- **[QUICKSTART.md](QUICKSTART.md)**: Get running in 5 minutes

### Technical Documentation
- **[CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)**: Complete system architecture
- **[FAISS_INSTALLATION_SUCCESS.md](FAISS_INSTALLATION_SUCCESS.md)**: FAISS integration details
- **[LANGCHAIN_AGENTS_COMPLETE.md](LANGCHAIN_AGENTS_COMPLETE.md)**: LangChain agent implementation
- **[LANGGRAPH_WORKFLOW_COMPLETE.md](LANGGRAPH_WORKFLOW_COMPLETE.md)**: LangGraph workflow details
- **[docs/ONCHAIN_ANALYZER_USAGE.md](docs/ONCHAIN_ANALYZER_USAGE.md)**: On-chain analytics guide
- **[docs/API_INTEGRATION_PATTERNS.md](docs/API_INTEGRATION_PATTERNS.md)**: API client patterns

## Troubleshooting

### Common Issues

**Issue**: "FAISS not available" warning
```bash
# Solution: Reinstall FAISS
pip uninstall faiss-cpu -y
pip install faiss-cpu
```

**Issue**: "HuggingFace API rate limit exceeded"
```bash
# Solution: System will automatically retry after cooldown
# Or use OpenRouter as fallback (configured automatically)
```

**Issue**: "Telegram failed: 400"
```bash
# Solution: Telegram is optional - system works without it
# Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env if needed
```

**Issue**: "Trade amount 100 BTC exceeds limit"
```bash
# Solution: This was fixed - LLM now returns USD amounts
# If still occurring, check prompts/dca_decision_agent.txt is updated
```

**Issue**: System suggests unreasonable trades
```bash
# Solution: Guardrails will reject invalid trades
# Check logs for [FAIL] messages explaining why trade was rejected
```

### Getting Help

1. Check [NON_TECHNICAL_USER_GUIDE.md](NON_TECHNICAL_USER_GUIDE.md) for explanations
2. Review [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) for system details
3. Check logs for [FAIL] and [WARN] messages
4. Verify API keys are valid in .env file
5. Ensure historical data file exists: `data/investing_btc_history.csv`

## License

*(To be determined)*

## Roadmap

### Completed Features
- [x] Multi-agent LangGraph workflow
- [x] FAISS-accelerated RAG for historical patterns
- [x] Free on-chain analytics (Blockchain.com)
- [x] Smart DCA strategy with RSI triggers
- [x] Multi-layer safety guardrails
- [x] Comprehensive documentation
- [x] $0/month operation cost

### Planned Enhancements
- [ ] Backtesting framework with historical data
- [ ] Portfolio rebalancing strategies
- [ ] Multi-exchange support (Coinbase, Kraken)
- [ ] Advanced risk metrics (VaR, CVaR)
- [ ] Web dashboard for monitoring
- [ ] Mobile alerts (Push notifications)
- [ ] Machine learning for adaptive thresholds
- [ ] Multi-asset support (ETH, altcoins)

## Contributing

Contributions are welcome! Areas for improvement:
- **Backtesting**: Framework for historical performance testing
- **Additional Strategies**: Beyond DCA (swing, momentum, mean reversion)
- **Enhanced RAG**: More sophisticated pattern matching algorithms
- **Exchange Integration**: More exchange APIs
- **Documentation**: Tutorials, videos, case studies

## License

MIT License - See LICENSE file for details

## Disclaimer

**IMPORTANT: READ BEFORE USING**

This software is provided for educational and research purposes only. Cryptocurrency trading carries substantial financial risk and may not be suitable for all investors.

**Risk Warnings**:
- **Financial Loss**: You can lose all invested capital
- **Volatility**: Cryptocurrency prices are extremely volatile
- **No Guarantees**: Past performance does not guarantee future results
- **Experimental**: This system is experimental and may contain bugs
- **LLM Limitations**: AI agents can make incorrect decisions
- **API Failures**: External services can fail or be unreliable

**Recommendations**:
1. **Paper Trade First**: Test extensively in simulation mode
2. **Start Small**: Use only funds you can afford to lose
3. **Understand The Code**: Review all logic before deploying
4. **Monitor Actively**: Don't leave system unattended initially
5. **Have Stop Losses**: Implement your own additional safety measures
6. **Tax Implications**: Consult tax professional about reporting requirements
7. **Regulatory Compliance**: Ensure compliance with local laws

**No Liability**: The authors and contributors are not responsible for any financial losses, damages, or consequences arising from the use of this software. Use entirely at your own risk.

**Not Financial Advice**: Nothing in this documentation constitutes financial, investment, legal, or tax advice. Consult qualified professionals before making investment decisions.

---

**Built with**: LangChain • LangGraph • FAISS • HuggingFace • OpenRouter

**Status**: Production-ready (paper trading) | Test thoroughly before live deployment

**Last Updated**: 2025-01-15
