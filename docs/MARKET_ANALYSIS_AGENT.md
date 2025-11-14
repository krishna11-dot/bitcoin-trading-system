# Market Analysis Agent - LangChain Integration

## Overview

The Market Analysis Agent is a LangChain-powered component that analyzes Bitcoin market conditions using technical indicators and returns structured assessments via LLM reasoning.

## Key Features

- **External Prompt Templates**: Prompts stored in `prompts/` for easy iteration
- **LangChain Integration**: Uses LangChain for LLM orchestration
- **HuggingFace LLM**: Powered by `google/gemma-2-2b-it` (free tier)
- **Structured Output**: Returns validated JSON with trend, confidence, reasoning
- **Robust Error Handling**: 3 retries with exponential backoff
- **Safe Defaults**: Always returns valid response even on failure

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Market Analysis Workflow                   │
└─────────────────────────────────────────────────────────────┘

1. Load External Prompt
   └── prompts/market_analysis_agent.txt

2. Create HuggingFace LLM
   └── google/gemma-2-2b-it (temperature=0.1, max_tokens=500)

3. Format Prompt
   └── Fill template with market data & indicators

4. Call LLM (with retry)
   └── 3 attempts with exponential backoff

5. Parse & Validate
   └── Extract JSON, validate structure & values

6. Return Result
   └── {trend, confidence, reasoning, risk_level}
```

## Usage

### Basic Usage

```python
from agents.market_analysis_agent import analyze_market
from data_models import MarketData, TechnicalIndicators

# Create market data
market_data = MarketData(
    price=106000.0,
    volume=25000000000.0,
    timestamp="2025-01-10T12:00:00Z",
    change_24h=2.5,
    high_24h=107000.0,
    low_24h=105000.0
)

# Create technical indicators
indicators = TechnicalIndicators(
    rsi_14=65.3,
    macd=1250.5,
    macd_signal=1180.2,
    macd_histogram=70.3,
    atr_14=1500.0,
    sma_50=104500.0,
    ema_12=105800.0,
    ema_26=104200.0
)

# Analyze market
result = analyze_market(market_data, indicators)

print(f"Trend: {result['trend']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Risk: {result['risk_level']}")
print(f"Reasoning: {result['reasoning']}")
```

### Output Format

```json
{
    "trend": "bullish",
    "confidence": 0.85,
    "reasoning": "Strong bullish momentum with RSI at 65.3 and MACD above signal line. Price trading above 50-period SMA indicates upward trend continuation.",
    "risk_level": "medium"
}
```

### Field Descriptions

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `trend` | string | `"bullish"` \| `"bearish"` \| `"neutral"` | Market trend direction |
| `confidence` | float | 0.0 - 1.0 | Confidence in the assessment |
| `reasoning` | string | - | Brief explanation (1-2 sentences) |
| `risk_level` | string | `"low"` \| `"medium"` \| `"high"` | Risk assessment |

## Testing

### Run the Test Script

```bash
python test_market_analysis_agent.py
```

### Run Module Directly

```bash
python -m agents.market_analysis_agent
```

### Expected Output

```
======================================================================
Testing LangChain Market Analysis Agent
======================================================================

📊 Test Scenario: Bullish Market
----------------------------------------------------------------------
Price: $106,000.00 (+3.50%)
Volume: $28.0B
RSI: 68.5
MACD: 1250.5 (Signal: 1180.2)

🤖 Analyzing market with LangChain agent...

✅ Analysis Result:
  Trend: BULLISH
  Confidence: 85.00%
  Risk Level: MEDIUM
  Reasoning: Strong bullish momentum with RSI at 68.5 and MACD crossover...

✅ All validations passed!
```

## Prompt Engineering

### Customizing the Prompt

Edit `prompts/market_analysis_agent.txt` to customize the analysis behavior:

```text
You are an expert Bitcoin market analyst...

CURRENT MARKET DATA:
- Price: ${price}
- RSI (14): {rsi}
...

TASK:
Analyze these conditions...
```

**Key Points:**
- Use `{variable}` for Python `.format()` substitution
- Keep prompts under 1000 tokens
- Emphasize "JSON only" output (no markdown)
- Include clear examples of valid output

### Variables Available

| Variable | Source | Description |
|----------|--------|-------------|
| `price` | MarketData | Current BTC price |
| `change_24h` | MarketData | 24h percentage change |
| `volume` | MarketData | 24h trading volume |
| `timestamp` | MarketData | ISO 8601 timestamp |
| `rsi` | TechnicalIndicators | RSI (14-period) |
| `macd` | TechnicalIndicators | MACD line value |
| `macd_signal` | TechnicalIndicators | MACD signal line |
| `atr` | TechnicalIndicators | ATR (14-period) |
| `sma_50` | TechnicalIndicators | 50-period SMA |

## Error Handling

### Retry Logic

The agent retries failed requests 3 times with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds

### Safe Defaults

If all retries fail, returns conservative default:

```json
{
    "trend": "neutral",
    "confidence": 0.5,
    "reasoning": "Analysis failed: [error]. Using conservative default.",
    "risk_level": "high"
}
```

This ensures the trading system never crashes due to LLM failures.

## Configuration

### LLM Settings

Edit `agents/market_analysis_agent.py` to adjust LLM parameters:

```python
llm = HuggingFaceEndpoint(
    repo_id="google/gemma-2-2b-it",  # Model ID
    temperature=0.1,                  # Low = deterministic
    max_new_tokens=500,               # Response length
    timeout=30,                       # Request timeout
)
```

### Model Options

| Model | Size | Speed | Quality | Free Tier |
|-------|------|-------|---------|-----------|
| google/gemma-2-2b-it | 2B | Fast | Good | ✅ Yes |
| meta-llama/Meta-Llama-3-8B-Instruct | 8B | Medium | Better | ✅ Yes |
| mistralai/Mistral-7B-Instruct-v0.3 | 7B | Medium | Better | ✅ Yes |

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

result = analyze_market(market_data, indicators)
```

### Debug Output

```
DEBUG - 📊 Prompt length: 487 chars
DEBUG - 🔄 Market analysis attempt 1/3
DEBUG - 🤖 LLM response: {"trend": "bullish", ...}
DEBUG - 📊 Inferred risk_level: medium
INFO  - ✅ Analysis complete: bullish (confidence: 0.85, risk: medium)
```

## Integration with Trading System

### Example: Full Trading Pipeline

```python
from agents.market_analysis_agent import analyze_market
from tools.binance_client import BinanceClient
from tools.technical_indicators import TechnicalIndicatorCalculator

# Fetch market data
binance = BinanceClient()
market_data = binance.get_ticker("BTCUSDT")

# Calculate indicators
calculator = TechnicalIndicatorCalculator()
indicators = calculator.calculate_all(market_data)

# Analyze market
analysis = analyze_market(market_data, indicators)

# Make trading decision based on analysis
if analysis['trend'] == 'bullish' and analysis['confidence'] > 0.7:
    print("✅ Strong bullish signal - consider buying")
elif analysis['trend'] == 'bearish' and analysis['confidence'] > 0.7:
    print("⚠️ Strong bearish signal - consider selling")
else:
    print("⏸️ Neutral or low confidence - hold position")
```

## Dependencies

### Required

```bash
pip install langchain>=0.1.0
pip install langchain-community>=0.0.20
pip install huggingface-hub>=0.20.0
```

### Environment Variables

```bash
# .env file
HUGGINGFACE_API_KEY=your_api_key_here
```

Get your free API key: https://huggingface.co/settings/tokens

## Performance

### Response Times

- **Average**: 2-4 seconds
- **With retry**: 6-12 seconds (if first attempt fails)
- **Timeout**: 30 seconds per attempt

### Rate Limits

HuggingFace Inference API (Free Tier):
- **Requests**: 150 per minute
- **Daily quota**: Generous (no hard limit for gemma-2-2b-it)

### Optimization Tips

1. **Cache results**: Don't call for every tick (use 1-5 minute intervals)
2. **Batch analysis**: Analyze once, use result for multiple strategies
3. **Fallback to simpler logic**: If LLM fails, use rule-based analysis

## Troubleshooting

### Common Issues

#### 1. Prompt File Not Found

```
FileNotFoundError: Prompt file not found: prompts/market_analysis_agent.txt
```

**Solution**: Ensure `prompts/market_analysis_agent.txt` exists

#### 2. Invalid JSON Response

```
ValueError: No JSON found in response
```

**Solution**: LLM returned non-JSON text. The retry logic will attempt again with backoff.

#### 3. HuggingFace API Error

```
HuggingFaceAPIError: 429 Too Many Requests
```

**Solution**: Rate limit exceeded. Reduce request frequency or add delays.

#### 4. Model Unavailable

```
Error: Model google/gemma-2-2b-it is not available
```

**Solution**: Switch to alternative model:
```python
repo_id="meta-llama/Meta-Llama-3-8B-Instruct"
```

## Advanced Usage

### Custom Validation

Add custom validation rules:

```python
def validate_custom_rules(result: Dict) -> Dict:
    """Add custom business logic validation."""

    # Rule: Bearish + low confidence = neutral
    if result['trend'] == 'bearish' and result['confidence'] < 0.6:
        result['trend'] = 'neutral'
        result['reasoning'] += " (Adjusted to neutral due to low confidence)"

    return result

# Use in analysis
result = analyze_market(market_data, indicators)
result = validate_custom_rules(result)
```

### Multi-Model Ensemble

Get consensus from multiple models:

```python
from langchain_community.llms import HuggingFaceEndpoint

models = [
    "google/gemma-2-2b-it",
    "meta-llama/Meta-Llama-3-8B-Instruct",
]

results = []
for model_id in models:
    llm = HuggingFaceEndpoint(repo_id=model_id, ...)
    result = analyze_market(market_data, indicators)
    results.append(result)

# Aggregate results (majority voting)
trends = [r['trend'] for r in results]
consensus_trend = max(set(trends), key=trends.count)
```

## Roadmap

### Planned Features

- [ ] Multi-model fallback chain
- [ ] Sentiment integration (Fear/Greed Index)
- [ ] RAG integration (historical patterns)
- [ ] Caching layer for repeated analyses
- [ ] A/B testing framework for prompt optimization
- [ ] Real-time streaming analysis

## Contributing

To add new analysis features:

1. Update prompt template in `prompts/market_analysis_agent.txt`
2. Add new variables to `PromptTemplate` input_variables
3. Pass new data in `prompt.format()`
4. Update response validation in `_parse_and_validate_response()`
5. Add tests in `test_market_analysis_agent.py`

## License

Part of the Bitcoin Trading System - see main LICENSE file.

---

**Status**: ✅ Production-Ready
**Last Updated**: 2025-01-10
**Maintainer**: Bitcoin Trading System Team
