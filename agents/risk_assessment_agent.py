"""Risk Assessment Agent using LangChain and OpenRouter.

This agent evaluates trading risk and determines position sizing based on
portfolio state, market volatility (ATR), and risk management parameters.
Uses external prompt templates for easy prompt engineering without code changes.

Example:
    >>> from agents.risk_assessment_agent import assess_risk
    >>> from data_models import PortfolioState, MarketData, TechnicalIndicators
    >>>
    >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
    >>> market_data = MarketData(price=106000.0, ...)
    >>> indicators = TechnicalIndicators(rsi_14=65.3, atr_14=1500.0, ...)
    >>> config = {"atr_multiplier": 1.5, "max_position_size": 0.20, ...}
    >>> result = assess_risk(portfolio, market_data, indicators, config)
    >>> print(f"Position: ${result['recommended_position_usd']:.2f}")
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
from data_models.portfolio import PortfolioState

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
        >>> template = load_prompt("risk_assessment_agent.txt")
        >>> print(len(template))
        500
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


def assess_risk(
    portfolio: PortfolioState,
    market_data: MarketData,
    indicators: TechnicalIndicators,
    config: Dict,
    market_analysis: Dict = None,
) -> Dict:
    """Assess trading risk using LangChain + OpenRouter.

    This function orchestrates the risk assessment workflow:
    1. Calculates portfolio metrics
    2. Loads external prompt template
    3. Creates OpenRouter LLM endpoint
    4. Formats prompt with portfolio and risk parameters
    5. Calls LLM for assessment
    6. Parses and validates JSON response
    7. Returns structured risk assessment

    Args:
        portfolio: Current portfolio balances and positions
        market_data: Current BTC price
        indicators: Technical indicators (ATR for volatility, RSI)
        config: Risk management configuration
        market_analysis: Optional market trend analysis

    Returns:
        dict: Risk assessment with structure:
            {
                "recommended_position_usd": float,
                "stop_loss_price": float,
                "risk_percent": float,
                "reasoning": str,
                "approved": bool
            }

    Example:
        >>> portfolio = PortfolioState(btc_balance=0.5, usd_balance=10000.0, ...)
        >>> result = assess_risk(portfolio, market_data, indicators, config)
        >>> if result['approved']:
        ...     print(f"Approved: ${result['recommended_position_usd']:.2f}")
    """
    settings = Settings.get_instance()

    # Calculate portfolio metrics
    btc_value = portfolio.btc_balance * market_data.price
    total_value = btc_value + portfolio.usd_balance

    # Extract market analysis if provided
    if market_analysis is None:
        market_analysis = {}

    # Step 1: Create OpenRouter LLM endpoint
    try:
        llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            model="mistralai/mistral-7b-instruct:free",
            temperature=0.1,
            max_tokens=600,  # Slightly more for detailed risk analysis
            timeout=30,
            default_headers={
                "HTTP-Referer": "https://github.com/your-repo/bitcoin-trading-system",
                "X-Title": "Bitcoin Trading System - Risk Assessment",
            },
        )
        logger.info("OpenRouter LLM initialized: mistralai/mistral-7b-instruct:free")
    except Exception as e:
        logger.error(f" LLM initialization failed: {e}")
        return _get_default_response(f"LLM init failed: {e}")

    # Step 2: Load external prompt template
    try:
        prompt_template_str = load_prompt("risk_assessment_agent.txt")
        prompt = PromptTemplate(
            input_variables=[
                "btc_balance",
                "usd_balance",
                "btc_price",
                "total_value",
                "atr",
                "rsi",
                "trend",
                "confidence",
                "atr_multiplier",
                "max_position_size",
                "max_total_exposure",
                "emergency_stop",
            ],
            template=prompt_template_str,
        )
    except FileNotFoundError as e:
        logger.error(f" Prompt template not found: {e}")
        return _get_default_response("Prompt template missing")

    # Step 3: Format prompt with portfolio and risk parameters
    filled_prompt = prompt.format(
        btc_balance=portfolio.btc_balance,
        usd_balance=portfolio.usd_balance,
        btc_price=market_data.price,
        total_value=total_value,
        atr=indicators.atr_14,
        rsi=indicators.rsi_14,
        trend=market_analysis.get("trend", "neutral"),
        confidence=market_analysis.get("confidence", 0.5),
        atr_multiplier=config.get("atr_multiplier", 1.5),
        max_position_size=config.get("max_position_size", 0.20) * 100,  # Convert to %
        max_total_exposure=config.get("max_total_exposure", 0.80) * 100,
        emergency_stop=config.get("emergency_stop", 0.25) * 100,
    )

    logger.debug(f" Prompt length: {len(filled_prompt)} chars")

    # Step 4-7: Call LLM with retry logic (3 attempts)
    for attempt in range(3):
        try:
            logger.info(f" Risk assessment attempt {attempt + 1}/3")

            # Call LLM
            response = llm.invoke(filled_prompt)

            # Parse and validate response
            result = _parse_and_validate_response(response)

            # Apply hard safety constraints
            result = _apply_safety_constraints(result, portfolio, total_value, config)

            logger.info(
                f" Risk assessment complete: "
                f"${result['recommended_position_usd']:.2f} "
                f"(approved: {result['approved']}, "
                f"risk: {result['risk_percent']:.2f}%)"
            )

            return result

        except Exception as e:
            logger.warning(f" Attempt {attempt + 1}/3 failed: {e}")

            if attempt == 2:  # Last attempt
                logger.error(f" All attempts failed")
                return _get_default_response(f"Assessment failed after 3 attempts: {e}")

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
        dict: Validated risk assessment

    Raises:
        ValueError: If response is invalid or missing required fields
        json.JSONDecodeError: If JSON parsing fails

    Example:
        >>> response = '{"recommended_position_usd": 1000, "approved": true, ...}'
        >>> result = _parse_and_validate_response(response)
        >>> result['approved']
        True
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
    required_fields = [
        "recommended_position_usd",
        "stop_loss_price",
        "risk_percent",
        "reasoning",
    ]
    missing_fields = [f for f in required_fields if f not in result]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {missing_fields}. " f"Response: {result}"
        )

    # Step 6: Validate numeric values
    if result["recommended_position_usd"] < 0:
        raise ValueError(
            f"Invalid position size: {result['recommended_position_usd']}"
        )

    if result["stop_loss_price"] < 0:
        raise ValueError(f"Invalid stop loss: {result['stop_loss_price']}")

    if not (0 <= result["risk_percent"] <= 100):
        raise ValueError(f"Invalid risk percent: {result['risk_percent']}")

    # Step 7: Add approved field if missing
    if "approved" not in result:
        # Auto-approve if risk is reasonable
        result["approved"] = result["risk_percent"] <= 5.0

    return result


def _apply_safety_constraints(
    result: Dict, portfolio: PortfolioState, total_value: float, config: Dict
) -> Dict:
    """Apply hard safety constraints to risk assessment.

    This ensures LLM recommendations never exceed system-defined safety limits,
    even if the LLM suggests higher risk positions.

    Args:
        result: LLM risk assessment
        portfolio: Current portfolio state
        total_value: Total portfolio value in USD
        config: Risk management configuration

    Returns:
        dict: Risk assessment with safety constraints applied

    Example:
        >>> result = {"recommended_position_usd": 5000, "risk_percent": 10, ...}
        >>> safe_result = _apply_safety_constraints(result, portfolio, 10000, config)
        >>> # Position may be reduced if it exceeds max_position_size
    """
    max_position_size = config.get("max_position_size", 0.20)
    max_position_usd = total_value * max_position_size

    # Constraint 1: Never exceed max position size
    if result["recommended_position_usd"] > max_position_usd:
        logger.warning(
            f" Position ${result['recommended_position_usd']:.2f} "
            f"exceeds max ${max_position_usd:.2f}, adjusting"
        )
        result["recommended_position_usd"] = max_position_usd
        result["reasoning"] += f" (Reduced to max position size: {max_position_size:.0%})"

    # Constraint 2: Never exceed available USD balance
    if result["recommended_position_usd"] > portfolio.usd_balance:
        logger.warning(
            f" Position ${result['recommended_position_usd']:.2f} "
            f"exceeds available ${portfolio.usd_balance:.2f}, adjusting"
        )
        result["recommended_position_usd"] = portfolio.usd_balance
        result["reasoning"] += " (Reduced to available USD balance)"

    # Constraint 3: Reject if risk is too high
    max_risk_percent = 5.0  # Hard limit: 5% of portfolio at risk
    if result["risk_percent"] > max_risk_percent:
        logger.warning(
            f" Risk {result['risk_percent']:.2f}% exceeds max {max_risk_percent}%, rejecting"
        )
        result["approved"] = False
        result["reasoning"] += f" (Rejected: Risk exceeds {max_risk_percent}% limit)"

    # Constraint 4: Reject if position is too small to be worth fees
    min_position_usd = 10.0  # Minimum $10 position
    if 0 < result["recommended_position_usd"] < min_position_usd:
        logger.warning(
            f" Position ${result['recommended_position_usd']:.2f} "
            f"below minimum ${min_position_usd}, rejecting"
        )
        result["approved"] = False
        result["reasoning"] += f" (Rejected: Position below ${min_position_usd} minimum)"

    return result


def _get_default_response(error: str) -> Dict:
    """Generate safe default response when assessment fails.

    This ensures the system always returns a valid response structure,
    even when LLM calls fail. The default is conservative (no position,
    not approved).

    Args:
        error: Error message describing the failure

    Returns:
        dict: Safe default risk assessment

    Example:
        >>> result = _get_default_response("API timeout")
        >>> result['approved']
        False
        >>> result['recommended_position_usd']
        0.0
    """
    logger.warning(f" Using default response due to: {error}")

    return {
        "recommended_position_usd": 0.0,
        "stop_loss_price": 0.0,
        "risk_percent": 0.0,
        "reasoning": f"Risk assessment failed: {error}. Rejecting trade for safety.",
        "approved": False,
    }


# For testing
if __name__ == "__main__":
    # Configure detailed logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    from data_models import MarketData, PortfolioState, TechnicalIndicators

    print("=" * 60)
    print("Risk Assessment Agent - Test")
    print("=" * 60)

    # Create sample portfolio
    portfolio = PortfolioState(
        btc_balance=0.5,
        usd_balance=10000.0,
        active_positions=[],
        last_updated="2025-01-10T14:00:00Z",
    )

    # Create sample market data
    market_data = MarketData(
        price=106000.0,
        volume=28000000000.0,
        timestamp="2025-01-10T12:00:00Z",
        change_24h=3.5,
        high_24h=107000.0,
        low_24h=102000.0,
    )

    # Create sample technical indicators
    indicators = TechnicalIndicators(
        rsi_14=68.5,
        macd=1250.5,
        macd_signal=1180.2,
        macd_histogram=70.3,
        atr_14=1500.0,  # ATR for volatility
        sma_50=103500.0,
        ema_12=105800.0,
        ema_26=104200.0,
    )

    # Risk management configuration
    config = {
        "atr_multiplier": 1.5,
        "max_position_size": 0.20,  # 20% of portfolio
        "max_total_exposure": 0.80,  # 80% of portfolio
        "emergency_stop": 0.25,  # 25% emergency stop
    }

    # Market analysis context
    market_analysis = {"trend": "bullish", "confidence": 0.85}

    # Calculate portfolio value
    btc_value = portfolio.btc_balance * market_data.price
    total_value = btc_value + portfolio.usd_balance

    print("\n Portfolio State:")
    print(f"  BTC Balance: {portfolio.btc_balance} BTC (${btc_value:,.2f})")
    print(f"  USD Balance: ${portfolio.usd_balance:,.2f}")
    print(f"  Total Value: ${total_value:,.2f}")

    print("\n Market Conditions:")
    print(f"  Price: ${market_data.price:,.2f}")
    print(f"  ATR (14): ${indicators.atr_14:.2f}")
    print(f"  RSI: {indicators.rsi_14:.1f}")

    print("\n Risk Parameters:")
    print(f"  ATR Multiplier: {config['atr_multiplier']}x")
    print(f"  Max Position: {config['max_position_size']:.0%}")
    print(f"  Max Exposure: {config['max_total_exposure']:.0%}")

    print("\n Calling LangChain Risk Assessment Agent...")
    print("-" * 60)

    try:
        result = assess_risk(portfolio, market_data, indicators, config, market_analysis)

        print("\n Risk Assessment Result:")
        print(f"  Recommended Position: ${result['recommended_position_usd']:,.2f}")
        print(f"  Stop-Loss Price: ${result['stop_loss_price']:,.2f}")
        print(f"  Risk Percentage: {result['risk_percent']:.2f}%")
        print(f"  Approved: {result['approved']}")
        print(f"  Reasoning: {result['reasoning']}")

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
