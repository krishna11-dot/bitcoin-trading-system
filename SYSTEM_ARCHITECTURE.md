# Bitcoin Trading System - Complete Architecture

## Strategy Switcher Integration - How It Works

### Does It Automatically Integrate?

**NO, the Strategy Switcher is NOT automatically integrated yet.** You need to add it manually to the workflow. Here's how:

### Integration Points

The Strategy Switcher should be called BEFORE the DCA decision agent to select which strategy to use. Here's the integration flow:

```
Current Workflow:
parallel_data → calculate_indicators → analyze_market → analyze_sentiment → assess_risk → dca_decision → END

Proposed Workflow with Strategy Switcher:
parallel_data → calculate_indicators → SELECT_STRATEGY → analyze_market → analyze_sentiment → assess_risk → dca_decision → END
                                           ↑
                                Strategy Switcher determines: DCA / SWING / DAY
```

### How to Integrate (Step-by-Step)

1. **Add Strategy Selection Node** to [graph/trading_workflow.py](graph/trading_workflow.py):

```python
from tools.strategy_switcher import StrategySwitcher

def strategy_selection_node(state: TradingState) -> TradingState:
    """
    Select optimal trading strategy based on market conditions.

    Uses Strategy Switcher to analyze:
    - Market regime (crisis, high_volatility, trending_up, etc.)
    - Engineered features (8 custom indicators)
    - LLM-powered feature selection
    - Adaptive DCA triggers

    Returns updated state with selected strategy and parameters.
    """
    try:
        logger.info("Selecting trading strategy based on market conditions...")

        # Initialize Strategy Switcher
        switcher = StrategySwitcher()

        # Get recommendation
        recommendation = switcher.analyze_and_recommend(
            market_data=state["market_data"],
            indicators=state["indicators"],
            sentiment_data=state["sentiment_data"],
            onchain_data=state.get("onchain_data", {})
        )

        # Store strategy selection in state
        state["strategy_recommendation"] = {
            "strategy": recommendation["strategy"],  # "dca", "swing", or "day"
            "confidence": recommendation["confidence"],
            "position_size_pct": recommendation["position_size_pct"],
            "adaptive_dca_trigger": recommendation["adaptive_dca_trigger"],
            "market_regime": recommendation["market_regime"],
            "selected_features": recommendation["selected_features"],
            "reasoning": recommendation["switch_reason"]
        }

        logger.info(
            f"Strategy selected: {recommendation['strategy'].upper()} "
            f"(confidence: {recommendation['confidence']:.0%}, "
            f"regime: {recommendation['market_regime']})"
        )

        return state

    except Exception as e:
        logger.error(f"Strategy selection failed: {e}")
        state["errors"].append(f"Strategy selection error: {str(e)}")
        # Fallback to DCA
        state["strategy_recommendation"] = {
            "strategy": "dca",
            "confidence": 0.6,
            "position_size_pct": 2.0,
            "adaptive_dca_trigger": 3.0,
            "reasoning": "Fallback to conservative DCA due to error"
        }
        return state
```

2. **Add to LangGraph Workflow:**

```python
# In build_trading_workflow():
workflow.add_node("select_strategy", strategy_selection_node)

# Update edges:
workflow.add_edge("calculate_indicators", "select_strategy")  # NEW
workflow.add_edge("select_strategy", "analyze_market")
# ... rest of edges
```

3. **Update State Definition:**

```python
class TradingState(TypedDict, total=False):
    # ... existing fields

    # Strategy selection output
    strategy_recommendation: Optional[Dict]  # NEW FIELD
```

4. **Use Strategy in Position Manager:**

The selected strategy is then used in [main.py](main.py) when opening positions:

```python
# In main.py run_one_cycle():
if td.action.upper() == "BUY":
    # Get selected strategy from workflow result
    strategy_rec = result.get("strategy_recommendation", {})
    strategy = strategy_rec.get("strategy", "dca")
    position_size_pct = strategy_rec.get("position_size_pct", 2.0)
    adaptive_trigger = strategy_rec.get("adaptive_dca_trigger", 3.0)

    # Use adaptive DCA trigger instead of fixed config
    can_open, reason = position_manager.can_open_position(
        strategy=strategy,
        amount_usd=amount_usd,
        current_price=td.entry_price,
        drop_percentage=adaptive_trigger  # Dynamic trigger
    )
```

---

## Complete System Architecture

### Directory Structure (Current)

```
bitcoin-trading-system/
├── agents/                       # LangChain Agents (LLM-powered analysis)
│   ├── base_agent.py            # Base class for all agents
│   ├── market_analysis_agent.py # Market trend analysis (LLM)
│   ├── sentiment_analysis_agent.py  # Sentiment analysis (LLM)
│   ├── risk_assessment_agent.py # Risk evaluation (LLM)
│   ├── dca_decision_agent.py    # DCA buy/hold decision (LLM)
│   ├── market_analyst.py        # Legacy market analyzer
│   ├── rag_enhanced_market_analyst.py  # RAG-powered market analysis
│   ├── rag_enhanced_strategy_agent.py  # RAG-powered strategy
│   └── ...
│
├── graph/                        # LangGraph Workflow
│   ├── trading_workflow.py      # MAIN WORKFLOW (parallel + sequential)
│   └── __init__.py
│
├── tools/                        # Utility Tools & Data Clients
│   ├── binance_client.py        # Binance API (price, orders)
│   ├── coinmarketcap_client.py  # CoinMarketCap API (sentiment)
│   ├── yfinance_client.py       # Yahoo Finance (fallback data)
│   ├── bitcoin_onchain_analyzer.py  # Blockchain.com on-chain data
│   ├── indicator_calculator.py  # Technical indicators (RSI, MACD, ATR)
│   ├── csv_rag_pipeline.py      # RAG retrieval from historical data
│   ├── strategy_switcher.py     # Adaptive strategy selection (NEW)
│   ├── position_manager.py      # Position & budget management
│   ├── rate_limiter.py          # API rate limiting
│   ├── google_sheets_sync.py    # Dynamic config from Google Sheets
│   └── ...
│
├── guardrails/                   # Pre-execution Safety Checks
│   └── safety_checks.py         # Validate trade before execution
│
├── config/                       # Configuration
│   ├── settings.py              # API keys, environment variables
│   └── ...
│
├── data_models/                  # Pydantic Data Models
│   ├── __init__.py              # MarketData, TradeDecision, etc.
│   └── ...
│
├── data/                         # Historical Data for RAG
│   ├── Bitcoin_Historical_Data_Raw.csv  # CORRECT RAG data file
│   ├── investing_btc_history.csv  # FAKE FILE - TO BE REMOVED
│   └── positions.json           # Position Manager storage
│
├── prompts/                      # LLM Prompts
│   └── __init__.py              # Prompt templates for agents
│
├── monitoring/                   # System Monitoring
│   └── ...
│
├── main.py                       # MAIN ENTRY POINT (24/7 trading loop)
├── config_trading.py             # Trading parameters
└── ...
```

### Reorganized Structure (Proposed)

```
bitcoin-trading-system/
├── agents/                       # LangChain Agents
│   ├── core/                    # Core analysis agents
│   │   ├── base_agent.py
│   │   ├── market_analysis_agent.py
│   │   ├── sentiment_analysis_agent.py
│   │   ├── risk_assessment_agent.py
│   │   └── dca_decision_agent.py
│   │
│   ├── rag_enhanced/            # RAG-enhanced agents
│   │   ├── rag_enhanced_market_analyst.py
│   │   └── rag_enhanced_strategy_agent.py
│   │
│   └── legacy/                  # Old agents (for reference)
│       ├── market_analyst.py
│       ├── risk_manager.py
│       └── strategy_agent.py
│
├── graph/                        # LangGraph Workflows
│   ├── trading_workflow.py      # Main hybrid workflow
│   └── nodes/                   # Workflow nodes (optional organization)
│       ├── data_collection.py
│       ├── strategy_selection.py
│       ├── analysis.py
│       └── decision.py
│
├── tools/                        # Tools & Utilities
│   ├── data_clients/            # External API clients
│   │   ├── binance_client.py
│   │   ├── coinmarketcap_client.py
│   │   ├── yfinance_client.py
│   │   └── bitcoin_onchain_analyzer.py
│   │
│   ├── feature_engineering/     # Feature engineering & indicators
│   │   ├── indicator_calculator.py
│   │   ├── strategy_switcher.py
│   │   └── feature_extractors.py
│   │
│   ├── execution/               # Trade execution & management
│   │   ├── position_manager.py
│   │   └── order_executor.py (if needed)
│   │
│   ├── rag/                     # RAG pipeline
│   │   └── csv_rag_pipeline.py
│   │
│   └── utils/                   # Utility functions
│       ├── rate_limiter.py
│       ├── decorators.py
│       └── google_sheets_sync.py
│
├── guardrails/                   # Safety & Validation
│   └── safety_checks.py
│
├── config/                       # Configuration
│   ├── settings.py
│   └── trading_params.py
│
├── data_models/                  # Data Schemas
│   ├── __init__.py
│   └── ...
│
├── data/                         # Data Storage
│   ├── rag/                     # RAG training data
│   │   └── Bitcoin_Historical_Data_Raw.csv
│   │
│   ├── positions/               # Position tracking
│   │   └── positions.json
│   │
│   └── cache/                   # Cached API responses
│       └── .gitkeep
│
├── prompts/                      # LLM Prompts
│   ├── market_analysis.py
│   ├── sentiment_analysis.py
│   ├── risk_assessment.py
│   └── dca_decision.py
│
├── monitoring/                   # Monitoring & Logging
│   └── ...
│
├── tests/                        # Test Files
│   ├── test_strategy_switcher.py
│   ├── test_position_manager.py
│   ├── test_rag_pipeline.py
│   └── ...
│
├── main.py                       # Main entry point
└── ...
```

---

## Communication Flow

### 1. LangGraph Workflow (graph/trading_workflow.py)

```
START
  ↓
┌─────────────────────────────────────────────────────────────┐
│ PARALLEL DATA COLLECTION (Async - Runs Simultaneously)     │
├─────────────────────────────────────────────────────────────┤
│ • Binance Client → Market data (price, volume, change)     │
│ • CoinMarketCap → Fear & Greed Index, sentiment score      │
│ • BitcoinOnChain → Hash rate, mempool, block metrics       │
│                                                             │
│ Performance: 3 seconds (vs 6.5s sequential)                │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ INDICATOR CALCULATION (Sync)                               │
├─────────────────────────────────────────────────────────────┤
│ tools/indicator_calculator.py                              │
│ • Input: Market data (OHLCV)                               │
│ • Output: RSI, MACD, ATR, Bollinger Bands, SMA, ADX, OBV  │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STRATEGY SELECTION (NEW - To Be Added)                     │
├─────────────────────────────────────────────────────────────┤
│ tools/feature_engineering/strategy_switcher.py             │
│ • Detect market regime (crisis, trending, ranging)         │
│ • Engineer 8 custom features                               │
│ • LLM selects top 3 features                               │
│ • Select strategy: DCA / SWING / DAY                       │
│ • Calculate adaptive DCA trigger (1.5%-3.5%)               │
│ • Output: Strategy + confidence + position sizing          │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ SEQUENTIAL ANALYSIS PIPELINE (LLM Agents)                  │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. MARKET ANALYSIS AGENT                                   │
├─────────────────────────────────────────────────────────────┤
│ agents/core/market_analysis_agent.py                       │
│ • LLM: OpenRouter (Qwen 2.5 7B)                            │
│ • Input: Market data, indicators, on-chain data            │
│ • Output: Trend analysis, support/resistance, outlook      │
│ • Time: ~15-20 seconds                                     │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SENTIMENT ANALYSIS AGENT                                │
├─────────────────────────────────────────────────────────────┤
│ agents/core/sentiment_analysis_agent.py                    │
│ • LLM: OpenRouter (Qwen 2.5 7B)                            │
│ • Input: Fear & Greed Index, sentiment score               │
│ • Output: Market psychology, crowd behavior                │
│ • Time: ~15-20 seconds                                     │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. RISK ASSESSMENT AGENT                                   │
├─────────────────────────────────────────────────────────────┤
│ agents/core/risk_assessment_agent.py                       │
│ • LLM: OpenRouter (Qwen 2.5 7B)                            │
│ • Input: All previous analysis + portfolio state           │
│ • Output: Risk level, position sizing, approved/rejected   │
│ • Time: ~15-20 seconds                                     │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. DCA DECISION AGENT                                      │
├─────────────────────────────────────────────────────────────┤
│ agents/core/dca_decision_agent.py                          │
│ • LLM: OpenRouter (Qwen 2.5 7B)                            │
│ • Input: All analysis + config (DCA threshold, amount)     │
│ • Output: BUY / HOLD decision with reasoning               │
│ • Time: ~15-20 seconds                                     │
└─────────────────────────────────────────────────────────────┘
  ↓
END (Return TradingState)
```

### 2. Main Loop (main.py)

```
START main.py
  ↓
Initialize:
  • Position Manager (budget tracking, stop-losses)
  • Binance Client (price data, order execution)
  • Google Sheets Sync (optional dynamic config)
  ↓
┌─────────────────────────────────────────────────────────────┐
│ TRADING CYCLE (Every 30 minutes)                           │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Monitor Existing Positions                         │
├─────────────────────────────────────────────────────────────┤
│ • Update all position prices                               │
│ • Check stop-losses → Execute if triggered                 │
│ • Check emergency mode (-25% loss) → Close all            │
│ • Log large moves (>2%)                                    │
│ • Send Telegram notifications                              │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Load Configuration                                 │
├─────────────────────────────────────────────────────────────┤
│ • Try: Google Sheets (dynamic parameters)                  │
│ • Fallback: Local defaults                                 │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Run LangGraph Workflow                             │
├─────────────────────────────────────────────────────────────┤
│ await run_trading_cycle(config)                            │
│ → Returns TradingState with trade decision                 │
│ Time: 1-2 minutes                                          │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Apply Guardrails                                   │
├─────────────────────────────────────────────────────────────┤
│ guardrails/safety_checks.py                                │
│ • Validate trade decision                                  │
│ • Check position size limits                               │
│ • Verify risk thresholds                                   │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Execute Trade (if BUY approved)                    │
├─────────────────────────────────────────────────────────────┤
│ Position Manager:                                          │
│ • can_open_position() → Check budget, strategy limits      │
│ • open_position() → Execute trade, set stop-loss           │
│ • Store position with RAG context                          │
│                                                             │
│ Binance Client:                                            │
│ • place_market_order() → Execute on exchange               │
│ • (Currently simulated, not real execution)                │
└─────────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Log & Notify                                       │
├─────────────────────────────────────────────────────────────┤
│ • Log portfolio statistics                                 │
│ • Send Telegram notification                               │
│ • Update positions.json                                    │
└─────────────────────────────────────────────────────────────┘
  ↓
Wait 30 minutes → REPEAT
```

### 3. Tool Communication

```
LangGraph Workflow
       │
       ├──────→ tools/data_clients/binance_client.py
       │         └──→ Binance API (REST)
       │              └──→ Returns: MarketData
       │
       ├──────→ tools/data_clients/coinmarketcap_client.py
       │         └──→ CoinMarketCap API (REST)
       │              └──→ Returns: SentimentData
       │
       ├──────→ tools/data_clients/bitcoin_onchain_analyzer.py
       │         └──→ Blockchain.com API (REST)
       │              └──→ Returns: On-chain metrics
       │
       ├──────→ tools/feature_engineering/indicator_calculator.py
       │         └──→ Local calculation (TA-Lib or fallback)
       │              └──→ Returns: TechnicalIndicators
       │
       ├──────→ tools/feature_engineering/strategy_switcher.py
       │         ├──→ Feature engineering (local)
       │         ├──→ OpenRouter API (LLM feature selection)
       │         └──→ Returns: Strategy recommendation
       │
       └──────→ agents/core/*.py
                 └──→ OpenRouter API (LLM analysis)
                      └──→ Returns: Analysis results

Main Loop (main.py)
       │
       ├──────→ tools/execution/position_manager.py
       │         ├──→ Local JSON storage (positions.json)
       │         └──→ Returns: Position tracking
       │
       ├──────→ tools/data_clients/binance_client.py
       │         └──→ Binance API (order execution)
       │              └──→ Returns: Order status
       │
       ├──────→ tools/utils/google_sheets_sync.py
       │         └──→ Google Sheets API
       │              └──→ Returns: Dynamic config
       │
       └──────→ guardrails/safety_checks.py
                 └──→ Local validation
                      └──→ Returns: Approved/Rejected
```

---

## RAG Pipeline Integration

The RAG (Retrieval-Augmented Generation) pipeline is currently NOT integrated into the main workflow but is available for agents to use:

```
tools/rag/csv_rag_pipeline.py
  │
  ├──→ Reads: data/rag/Bitcoin_Historical_Data_Raw.csv
  │
  ├──→ Processes: Embeddings via FAISS
  │
  └──→ Provides: Similar historical patterns with outcomes

Usage in Agents:
  from tools.rag.csv_rag_pipeline import RAGRetriever

  rag = RAGRetriever("data/rag/Bitcoin_Historical_Data_Raw.csv")
  insights = rag.get_insights(current_conditions)

  # Returns:
  # - success_rate: 64%
  # - expected_outcome: +2.94%
  # - similar_patterns: 50 matches
  # - confidence: 82%
```

---

## Summary

1. **Strategy Switcher is NOT automatically integrated** - you need to add it as a new node in the workflow
2. **Current workflow has 5 sequential LLM agents** - market analysis, sentiment, risk, DCA decision
3. **Main loop runs every 30 minutes** - monitors positions, runs workflow, executes trades
4. **Tools are called by workflow nodes** - each node imports and uses specific tools
5. **Communication is direct function calls** - no message passing, just Python imports
6. **Folder reorganization recommended** - separate feature engineering, data clients, execution tools
7. **Remove fake CSV** - use Bitcoin_Historical_Data_Raw.csv instead of investing_btc_history.csv
