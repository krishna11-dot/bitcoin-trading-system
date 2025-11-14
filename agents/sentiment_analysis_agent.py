"""Sentiment Analysis Agent using LangChain and OpenRouter.

This agent analyzes market sentiment from Fear/Greed Index, social volume, and
news sentiment, returning structured assessments via LLM reasoning. Uses external
prompt templates for easy prompt engineering without code changes.

Example:
    >>> from agents.sentiment_analysis_agent import analyze_sentiment
    >>> from data_models import SentimentData, MarketData, TechnicalIndicators
    >>>
    >>> sentiment_data = SentimentData(
    ...     fear_greed_index=35,
    ...     social_volume="high",
    ...     news_sentiment=0.25,
    ...     timestamp="2025-01-10T12:00:00Z"
    ... )
    >>> market_data = MarketData(price=106000.0, ...)
    >>> indicators = TechnicalIndicators(rsi_14=65.3, ...)
    >>> result = analyze_sentiment(sentiment_data, market_data, indicators)
    >>> print(f"Sentiment: {result['sentiment']} (confidence: {result['confidence']:.2f})")
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from config.settings import Settings
from data_models.indicators import TechnicalIndicators
from data_models.market_data import MarketData
from data_models.sentiment import SentimentData

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
        >>> template = load_prompt("sentiment_analysis_agent.txt")
        >>> print(len(template))
        250
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


def analyze_sentiment(
    sentiment_data: SentimentData,
    market_data: MarketData,
    indicators: TechnicalIndicators,
) -> Dict:
    """Analyze market sentiment using LangChain + OpenRouter.

    This function orchestrates the sentiment analysis workflow:
    1. Loads external prompt template
    2. Creates OpenRouter LLM endpoint
    3. Formats prompt with sentiment and market data
    4. Calls LLM for analysis
    5. Parses and validates JSON response
    6. Returns structured result

    Args:
        sentiment_data: Fear/Greed Index, social volume, news sentiment
        market_data: Current BTC price for context
        indicators: RSI for technical context

    Returns:
        dict: Sentiment analysis with structure:
            {
                "sentiment": "bullish"|"bearish"|"neutral",
                "confidence": 0.0-1.0,
                "reasoning": str,
                "crowd_psychology": "fear"|"greed"|"neutral"
            }

    Example:
        >>> sentiment_data = SentimentData(fear_greed_index=35, ...)
        >>> market_data = MarketData(price=106000.0, ...)
        >>> indicators = TechnicalIndicators(rsi_14=65.3, ...)
        >>> result = analyze_sentiment(sentiment_data, market_data, indicators)
        >>> print(result['sentiment'])
        'bearish'
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
                "X-Title": "Bitcoin Trading System - Sentiment Analysis",
            },
        )
        logger.info("OpenRouter LLM initialized: mistralai/mistral-7b-instruct:free")
    except Exception as e:
        logger.error(f" LLM initialization failed: {e}")
        return _get_default_response(f"LLM init failed: {e}")

    # Step 2: Load external prompt template
    try:
        prompt_template_str = load_prompt("sentiment_analysis_agent.txt")
        prompt = PromptTemplate(
            input_variables=[
                "fear_greed",
                "social_volume",
                "news_sentiment",
                "price",
                "rsi",
            ],
            template=prompt_template_str,
        )
    except FileNotFoundError as e:
        logger.error(f" Prompt template not found: {e}")
        return _get_default_response("Prompt template missing")

    # Step 3: Format prompt with current sentiment and market data
    filled_prompt = prompt.format(
        fear_greed=sentiment_data.fear_greed_index,
        social_volume=sentiment_data.social_volume,
        news_sentiment=sentiment_data.news_sentiment,
        price=market_data.price,
        rsi=indicators.rsi_14,
    )

    logger.debug(f" Prompt length: {len(filled_prompt)} chars")

    # Step 4-6: Call LLM with retry logic (3 attempts)
    for attempt in range(3):
        try:
            logger.info(f" Sentiment analysis attempt {attempt + 1}/3")

            # Call LLM
            response = llm.invoke(filled_prompt)

            # Parse and validate response
            result = _parse_and_validate_response(response)

            logger.info(
                f" Sentiment analysis complete: {result['sentiment']} "
                f"(confidence: {result['confidence']:.2f}, "
                f"psychology: {result['crowd_psychology']})"
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
    - LangChain AIMessage objects

    Args:
        response: Raw LLM response (string or AIMessage)

    Returns:
        dict: Validated sentiment analysis

    Raises:
        ValueError: If response is invalid or missing required fields
        json.JSONDecodeError: If JSON parsing fails

    Example:
        >>> response = '{"sentiment": "bullish", "confidence": 0.85, ...}'
        >>> result = _parse_and_validate_response(response)
        >>> result['sentiment']
        'bullish'
    """
    # Step 1: Extract text content from response (handle AIMessage)
    if hasattr(response, "content"):
        response_text = response.content
    else:
        response_text = str(response)

    # Step 2: Clean response (remove markdown code blocks)
    response_clean = response_text.replace("```json", "").replace("```", "").strip()

    # Step 3: Try to extract JSON if wrapped in text
    json_match = re.search(r"\{.*\}", response_clean, re.DOTALL)
    if json_match:
        response_clean = json_match.group()
    else:
        raise ValueError(f"No JSON found in response: {response_clean[:200]}")

    # Step 4: Parse JSON
    try:
        result = json.loads(response_clean)
    except json.JSONDecodeError as e:
        logger.error(f" JSON parse error: {e}")
        logger.error(f"Response text: {response_clean[:300]}")
        raise

    # Step 5: Validate required fields
    required_fields = ["sentiment", "confidence", "reasoning"]
    missing_fields = [f for f in required_fields if f not in result]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {missing_fields}. " f"Response: {result}"
        )

    # Step 6: Validate sentiment value
    valid_sentiments = ["bullish", "bearish", "neutral"]
    if result["sentiment"] not in valid_sentiments:
        raise ValueError(
            f"Invalid sentiment '{result['sentiment']}'. "
            f"Must be one of: {valid_sentiments}"
        )

    # Step 7: Validate confidence range
    confidence = result["confidence"]
    if not (0 <= confidence <= 1):
        raise ValueError(
            f"Invalid confidence {confidence}. " f"Must be between 0.0 and 1.0"
        )

    # Step 8: Add crowd_psychology if missing (optional field)
    if "crowd_psychology" not in result:
        # Infer from sentiment
        if result["sentiment"] == "bearish":
            result["crowd_psychology"] = "fear"
        elif result["sentiment"] == "bullish":
            result["crowd_psychology"] = "greed"
        else:
            result["crowd_psychology"] = "neutral"

        logger.debug(f" Inferred crowd_psychology: {result['crowd_psychology']}")

    # Validate crowd_psychology
    valid_psychology = ["fear", "greed", "neutral"]
    if result["crowd_psychology"] not in valid_psychology:
        raise ValueError(
            f"Invalid crowd_psychology '{result['crowd_psychology']}'. "
            f"Must be one of: {valid_psychology}"
        )

    return result


def _get_default_response(error: str) -> Dict:
    """Generate safe default response when analysis fails.

    This ensures the system always returns a valid response structure,
    even when LLM calls fail. The default is conservative (neutral sentiment,
    medium confidence).

    Args:
        error: Error message describing the failure

    Returns:
        dict: Safe default sentiment analysis

    Example:
        >>> result = _get_default_response("API timeout")
        >>> result['sentiment']
        'neutral'
        >>> result['crowd_psychology']
        'neutral'
    """
    logger.warning(f" Using default response due to: {error}")

    return {
        "sentiment": "neutral",
        "confidence": 0.5,
        "reasoning": f"Sentiment analysis failed: {error}. Using conservative neutral assessment.",
        "crowd_psychology": "neutral",
    }


# For testing
if __name__ == "__main__":
    # Configure detailed logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("Sentiment Analysis Agent - Test")
    print("=" * 60)

    # Create sample sentiment data (fear scenario)
    sentiment_data = SentimentData(
        fear_greed_index=35,  # Fear
        social_volume="high",
        news_sentiment=-0.2,  # Slightly negative news
        timestamp="2025-01-10T12:00:00Z",
    )

    # Create sample market data
    market_data = MarketData(
        price=102000.0,
        volume=32000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=-4.2,
        high_24h=107000.0,
        low_24h=101500.0,
    )

    # Create sample technical indicators
    indicators = TechnicalIndicators(
        rsi_14=32.5,  # Oversold
        macd=-850.5,
        macd_signal=-780.2,
        macd_histogram=-70.3,
        atr_14=2100.0,
        sma_50=105500.0,
        ema_12=103200.0,
        ema_26=104800.0,
    )

    print("\n Sentiment Data:")
    print(f"  Fear/Greed Index: {sentiment_data.fear_greed_index}")
    print(f"  Social Volume: {sentiment_data.social_volume}")
    print(f"  News Sentiment: {sentiment_data.news_sentiment:+.2f}")

    print("\n Market Context:")
    print(f"  Price: ${market_data.price:,.2f} ({market_data.change_24h:+.2f}%)")
    print(f"  RSI: {indicators.rsi_14:.1f}")

    print("\n Calling LangChain Sentiment Analysis Agent...")
    print("-" * 60)

    try:
        result = analyze_sentiment(sentiment_data, market_data, indicators)

        print("\n Sentiment Analysis Result:")
        print(f"  Sentiment: {result['sentiment'].upper()}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Crowd Psychology: {result['crowd_psychology'].upper()}")
        print(f"  Reasoning: {result['reasoning']}")

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
