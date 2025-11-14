"""Market Analysis Agent using LangChain and HuggingFace.

This agent analyzes Bitcoin market conditions using technical indicators and
returns structured assessments via LLM reasoning. Uses external prompt templates
for easy prompt engineering without code changes.

Example:
    >>> from agents.market_analysis_agent import analyze_market
    >>> from data_models import MarketData, TechnicalIndicators
    >>>
    >>> market_data = MarketData(
    ...     price=106000.0,
    ...     volume=25000000000.0,
    ...     timestamp="2025-01-10T12:00:00Z",
    ...     change_24h=2.5
    ... )
    >>> indicators = TechnicalIndicators(
    ...     rsi_14=65.3,
    ...     macd=1250.5,
    ...     macd_signal=1180.2,
    ...     macd_histogram=70.3,
    ...     atr_14=1500.0,
    ...     sma_50=104500.0,
    ...     ema_12=105800.0,
    ...     ema_26=104200.0
    ... )
    >>> result = analyze_market(market_data, indicators)
    >>> print(f"Trend: {result['trend']} (confidence: {result['confidence']:.2f})")
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict

from langchain_core.prompts import PromptTemplate

# Use ChatOpenAI with OpenRouter for reliable free LLM access
from langchain_openai import ChatOpenAI

from config.settings import Settings
from data_models.indicators import TechnicalIndicators
from data_models.market_data import MarketData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_prompt(filename: str) -> str:
    """Load external prompt template from prompts/ directory.

    Args:
        filename: Name of prompt file in prompts/ directory

    Returns:
        str: Prompt template text

    Raises:
        FileNotFoundError: If prompt file doesn't exist

    Example:
        >>> template = load_prompt("market_analysis_agent.txt")
        >>> print(len(template))
        350
    """
    prompt_path = Path("prompts") / filename

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Ensure prompt templates are in prompts/ directory."
        )

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    logger.info(f" Loaded prompt template: {filename}")
    return template


def analyze_market(
    market_data: MarketData, indicators: TechnicalIndicators
) -> Dict:
    """Analyze Bitcoin market using LangChain + HuggingFace LLM.

    This function orchestrates the market analysis workflow:
    1. Loads external prompt template
    2. Creates HuggingFace LLM endpoint
    3. Formats prompt with current market data
    4. Calls LLM for analysis
    5. Parses and validates JSON response
    6. Returns structured result

    Args:
        market_data: Current BTC price, volume, and 24h change data
        indicators: Technical indicators (RSI, MACD, ATR, moving averages)

    Returns:
        dict: Market analysis with structure:
            {
                "trend": "bullish"|"bearish"|"neutral",
                "confidence": 0.0-1.0,
                "reasoning": str,
                "risk_level": "low"|"medium"|"high"
            }

    Example:
        >>> market_data = MarketData(price=106000.0, volume=25e9, ...)
        >>> indicators = TechnicalIndicators(rsi_14=65.3, macd=1250.5, ...)
        >>> result = analyze_market(market_data, indicators)
        >>> print(result['trend'])
        'bullish'
    """
    settings = Settings.get_instance()

    # Step 1: Create OpenRouter LLM endpoint
    try:
        llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            model="mistralai/mistral-7b-instruct:free",
            temperature=0.1,
            max_tokens=500,
            timeout=30,
            default_headers={
                "HTTP-Referer": "https://github.com/your-repo/bitcoin-trading-system",
                "X-Title": "Bitcoin Trading System - Market Analysis",
            },
        )
        logger.info("OpenRouter LLM initialized: mistralai/mistral-7b-instruct:free")
    except Exception as e:
        logger.error(f"LLM initialization failed: {e}")
        return _get_default_response(f"LLM init failed: {e}")

    # Step 2: Load external prompt template
    try:
        prompt_template_str = load_prompt("market_analysis_agent.txt")
        prompt = PromptTemplate(
            input_variables=[
                "price",
                "change_24h",
                "volume",
                "timestamp",
                "rsi",
                "macd",
                "macd_signal",
                "atr",
                "sma_50",
            ],
            template=prompt_template_str,
        )
    except FileNotFoundError as e:
        logger.error(f" Prompt template not found: {e}")
        return _get_default_response("Prompt template missing")

    # Step 3: Format prompt with current market data
    filled_prompt = prompt.format(
        price=market_data.price,
        change_24h=market_data.change_24h,
        volume=f"{market_data.volume / 1e9:.1f}B",  # Format volume in billions
        timestamp=market_data.timestamp,
        rsi=indicators.rsi_14,
        macd=indicators.macd,
        macd_signal=indicators.macd_signal,
        atr=indicators.atr_14,
        sma_50=indicators.sma_50,
    )

    logger.debug(f" Prompt length: {len(filled_prompt)} chars")

    # Step 4-6: Call LLM with retry logic (3 attempts)
    for attempt in range(3):
        try:
            logger.info(f" Market analysis attempt {attempt + 1}/3")

            # Call LLM
            response = llm.invoke(filled_prompt)

            # Parse and validate response
            result = _parse_and_validate_response(response)

            logger.info(
                f" Analysis complete: {result['trend']} "
                f"(confidence: {result['confidence']:.2f}, "
                f"risk: {result['risk_level']})"
            )

            return result

        except Exception as e:
            logger.warning(f" Attempt {attempt + 1}/3 failed: {e}")

            if attempt == 2:  # Last attempt
                logger.error(f" All attempts failed")
                return _get_default_response(f"Analysis failed after 3 attempts: {e}")

            # Exponential backoff: 2^attempt seconds
            backoff_time = 2**attempt
            logger.info(f" Retrying in {backoff_time}s...")
            time.sleep(backoff_time)

    # Fallback (should never reach here)
    return _get_default_response("Unexpected failure")


def _parse_and_validate_response(response) -> Dict:
    """Parse LLM response and validate JSON structure.

    Handles various response formats:
    - Clean JSON
    - JSON wrapped in markdown code blocks
    - JSON embedded in text
    - AIMessage objects from ChatOpenAI

    Args:
        response: Raw LLM response (string or AIMessage)

    Returns:
        dict: Validated market analysis

    Raises:
        ValueError: If response is invalid or missing required fields
        json.JSONDecodeError: If JSON parsing fails

    Example:
        >>> response = '{"trend": "bullish", "confidence": 0.85, ...}'
        >>> result = _parse_and_validate_response(response)
        >>> result['trend']
        'bullish'
    """
    # Step 1: Extract text content from response (handle AIMessage objects)
    if hasattr(response, 'content'):
        response_text = response.content
    else:
        response_text = str(response)

    # Step 2: Clean response (remove markdown code blocks)
    response_clean = response_text.replace("```json", "").replace("```", "").strip()

    # Step 2: Try to extract JSON if wrapped in text
    json_match = re.search(r"\{.*\}", response_clean, re.DOTALL)
    if json_match:
        response_clean = json_match.group()
    else:
        raise ValueError(f"No JSON found in response: {response_clean[:200]}")

    # Step 3: Parse JSON
    try:
        result = json.loads(response_clean)
    except json.JSONDecodeError as e:
        logger.error(f" JSON parse error: {e}")
        logger.error(f"Response text: {response_clean[:300]}")
        raise

    # Step 4: Validate required fields
    required_fields = ["trend", "confidence", "reasoning"]
    missing_fields = [f for f in required_fields if f not in result]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {missing_fields}. "
            f"Response: {result}"
        )

    # Step 5: Validate trend value
    valid_trends = ["bullish", "bearish", "neutral"]
    if result["trend"] not in valid_trends:
        raise ValueError(
            f"Invalid trend '{result['trend']}'. "
            f"Must be one of: {valid_trends}"
        )

    # Step 6: Validate confidence range
    confidence = result["confidence"]
    if not (0 <= confidence <= 1):
        raise ValueError(
            f"Invalid confidence {confidence}. "
            f"Must be between 0.0 and 1.0"
        )

    # Step 7: Add risk_level if missing (optional field)
    if "risk_level" not in result:
        # Infer risk level from confidence
        if confidence >= 0.8:
            result["risk_level"] = "low"
        elif confidence >= 0.5:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "high"

        logger.debug(f" Inferred risk_level: {result['risk_level']}")

    # Validate risk_level
    valid_risk_levels = ["low", "medium", "high"]
    if result["risk_level"] not in valid_risk_levels:
        raise ValueError(
            f"Invalid risk_level '{result['risk_level']}'. "
            f"Must be one of: {valid_risk_levels}"
        )

    return result


def _get_default_response(error: str) -> Dict:
    """Generate safe default response when analysis fails.

    This ensures the system always returns a valid response structure,
    even when LLM calls fail. The default is conservative (neutral trend,
    medium confidence, high risk).

    Args:
        error: Error message describing the failure

    Returns:
        dict: Safe default market analysis

    Example:
        >>> result = _get_default_response("API timeout")
        >>> result['trend']
        'neutral'
        >>> result['risk_level']
        'high'
    """
    logger.warning(f" Using default response due to: {error}")

    return {
        "trend": "neutral",
        "confidence": 0.5,
        "reasoning": f"Analysis failed: {error}. Using conservative default assessment.",
        "risk_level": "high",
    }


# For testing
if __name__ == "__main__":
    # Configure detailed logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("Market Analysis Agent - Test")
    print("=" * 60)

    # Create sample market data
    market_data = MarketData(
        price=106000.0,
        volume=25000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=2.5,
        high_24h=107000.0,
        low_24h=105000.0,
    )

    # Create sample technical indicators
    indicators = TechnicalIndicators(
        rsi_14=65.3,
        macd=1250.5,
        macd_signal=1180.2,
        macd_histogram=70.3,
        atr_14=1500.0,
        sma_50=104500.0,
        ema_12=105800.0,
        ema_26=104200.0,
    )

    print("\n Market Data:")
    print(f"  Price: ${market_data.price:,.2f}")
    print(f"  24h Change: {market_data.change_24h:+.2f}%")
    print(f"  Volume: ${market_data.volume / 1e9:.1f}B")

    print("\n Technical Indicators:")
    print(f"  RSI (14): {indicators.rsi_14:.1f}")
    print(f"  MACD: {indicators.macd:.1f} / {indicators.macd_signal:.1f}")
    print(f"  ATR (14): ${indicators.atr_14:.1f}")
    print(f"  SMA (50): ${indicators.sma_50:,.2f}")

    print("\n Calling LangChain Market Analysis Agent...")
    print("-" * 60)

    try:
        result = analyze_market(market_data, indicators)

        print("\n Analysis Result:")
        print(f"  Trend: {result['trend'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Risk Level: {result['risk_level'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
