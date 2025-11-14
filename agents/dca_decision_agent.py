"""DCA Decision Agent using LangChain and OpenRouter.

This agent makes Dollar-Cost Averaging (DCA) buy decisions based on market
conditions, sentiment, technical indicators, and historical patterns from RAG.
Uses external prompt templates for easy prompt engineering without code changes.

Example:
    >>> from agents.dca_decision_agent import make_dca_decision
    >>> state = {
    ...     "market_data": market_data,
    ...     "indicators": indicators,
    ...     "portfolio_state": portfolio,
    ...     "config": {"dca_threshold": 3.0, "dca_amount": 100},
    ...     "market_analysis": {"trend": "bearish"},
    ...     "sentiment_analysis": {"sentiment": "fear"},
    ...     "rag_patterns": {"similar_patterns": 5, "success_rate": 0.75}
    ... }
    >>> decision = make_dca_decision(state)
    >>> print(f"Action: {decision.action} ${decision.amount}")
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from config.settings import Settings
from data_models.decisions import TradeDecision

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
        >>> template = load_prompt("dca_decision_agent.txt")
        >>> print(len(template))
        450
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


def make_dca_decision(state: Dict) -> TradeDecision:
    """Make DCA buy decision using LangChain + OpenRouter.

    This function orchestrates the DCA decision workflow:
    1. Extracts all context from state
    2. Loads external prompt template
    3. Creates OpenRouter LLM endpoint
    4. Formats prompt with full trading context
    5. Calls LLM for decision
    6. Parses and validates JSON response
    7. Returns TradeDecision object

    Args:
        state: Trading state dict containing:
            - market_data: Current market conditions
            - indicators: Technical indicators
            - portfolio_state: Portfolio balances
            - config: DCA configuration (threshold, amount)
            - market_analysis: Market trend analysis
            - sentiment_analysis: Sentiment assessment
            - rag_patterns: Historical pattern matches

    Returns:
        TradeDecision: DCA buy or hold decision with full context

    Example:
        >>> state = {"market_data": market_data, "indicators": indicators, ...}
        >>> decision = make_dca_decision(state)
        >>> if decision.action == "buy":
        ...     print(f"Buy ${decision.amount} at ${decision.entry_price}")
    """
    settings = Settings.get_instance()

    # Extract from state
    market_data = state.get("market_data")
    indicators = state.get("indicators")
    config = state.get("config", {})
    portfolio = state.get("portfolio_state")
    market_analysis = state.get("market_analysis", {})
    sentiment_analysis = state.get("sentiment_analysis", {})
    rag_results = state.get("rag_patterns", {})

    if not market_data or not indicators or not portfolio:
        logger.error(" Missing required state data")
        return _hold_decision(
            price=market_data.price if market_data else 0.0,
            reason="Missing required state data",
        )

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
                "X-Title": "Bitcoin Trading System - DCA Decision",
            },
        )
        logger.info("OpenRouter LLM initialized: mistralai/mistral-7b-instruct:free")
    except Exception as e:
        logger.error(f" LLM initialization failed: {e}")
        return _hold_decision(market_data.price, f"LLM init failed: {e}")

    # Step 2: Load external prompt template
    try:
        prompt_template_str = load_prompt("dca_decision_agent.txt")
        prompt = PromptTemplate(
            input_variables=[
                "price",
                "change_24h",
                "dca_threshold",
                "usd_balance",
                "market_trend",
                "sentiment",
                "rsi",
                "rag_patterns",
                "success_rate",
                "avg_outcome",
                "dca_amount",
            ],
            template=prompt_template_str,
        )
    except FileNotFoundError as e:
        logger.error(f" Prompt template not found: {e}")
        return _hold_decision(market_data.price, "Prompt template missing")

    # Step 3: Format prompt with full trading context
    filled_prompt = prompt.format(
        price=market_data.price,
        change_24h=market_data.change_24h,
        dca_threshold=config.get("dca_threshold", 3.0),
        usd_balance=portfolio.usd_balance,
        market_trend=market_analysis.get("trend", "neutral"),
        sentiment=sentiment_analysis.get("sentiment", "neutral"),
        rsi=indicators.rsi_14,
        rag_patterns=rag_results.get("similar_patterns", 0),
        success_rate=rag_results.get("success_rate", 0.5) * 100,
        avg_outcome=rag_results.get("avg_outcome", 0),
        dca_amount=config.get("dca_amount", 100),
    )

    logger.debug(f" Prompt length: {len(filled_prompt)} chars")

    # Step 4-7: Call LLM with retry logic (3 attempts)
    for attempt in range(3):
        try:
            logger.info(f" DCA decision attempt {attempt + 1}/3")

            # Call LLM
            response = llm.invoke(filled_prompt)

            # Parse and validate response
            result = _parse_and_validate_response(response)

            # Create TradeDecision object
            decision = _create_trade_decision(result, market_data.price)

            logger.info(
                f" DCA decision complete: {decision.action.upper()} "
                f"${decision.amount:.2f} at ${decision.entry_price:,.2f}"
            )

            return decision

        except Exception as e:
            logger.warning(f" Attempt {attempt + 1}/3 failed: {e}")

            if attempt == 2:  # Last attempt
                logger.error(f" All attempts failed")
                return _hold_decision(
                    market_data.price, f"Decision failed after 3 attempts: {e}"
                )

            # Exponential backoff: 2^attempt seconds
            backoff_time = 2**attempt
            logger.info(f" Retrying in {backoff_time}s...")
            time.sleep(backoff_time)

    # Fallback (should never reach here)
    return _hold_decision(market_data.price, "Unexpected failure")


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
        dict: Validated DCA decision

    Raises:
        ValueError: If response is invalid or missing required fields
        json.JSONDecodeError: If JSON parsing fails

    Example:
        >>> response = '{"action": "buy", "amount": 100, ...}'
        >>> result = _parse_and_validate_response(response)
        >>> result['action']
        'buy'
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
        logger.debug(f" LLM response parsed: {result}")
    except json.JSONDecodeError as e:
        logger.error(f" JSON parse error: {e}")
        logger.error(f"Response text: {response_clean[:300]}")
        raise

    # Step 5: Validate required fields
    required_fields = ["action", "amount", "reasoning"]
    missing_fields = [f for f in required_fields if f not in result]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {missing_fields}. " f"Response: {result}"
        )

    # Step 6: Validate action value
    valid_actions = ["buy", "hold"]
    if result["action"] not in valid_actions:
        raise ValueError(
            f"Invalid action '{result['action']}'. " f"Must be one of: {valid_actions}"
        )

    # Step 7: Validate amount
    amount = float(result["amount"])
    if amount < 0:
        raise ValueError(f"Invalid amount {amount}. Must be non-negative")

    # Step 8: Add confidence if missing
    if "confidence" not in result:
        result["confidence"] = 0.7 if result["action"] == "buy" else 1.0

    # Validate confidence
    if not (0 <= result["confidence"] <= 1):
        raise ValueError(f"Invalid confidence: {result['confidence']}")

    return result


def _create_trade_decision(result: Dict, entry_price: float) -> TradeDecision:
    """Create TradeDecision Pydantic model from LLM result.

    CRITICAL FUNCTION - USD to BTC Conversion:
    This function fixes a critical bug where the LLM (Large Language Model)
    returns amounts in USD (United States Dollars), but the TradeDecision
    model expects amounts in BTC (Bitcoin).

    THE BUG:
    - LLM prompt asks: "Buy $100 USD worth of Bitcoin"
    - LLM responds: {"action": "buy", "amount": 100}
    - Old code treated 100 as BTC → tried to buy 100 BTC ($10 million!)
    - Guardrails caught this: "Trade amount 100 BTC exceeds limit (10 BTC)"

    THE FIX:
    - Convert LLM's USD amount to BTC: amount_btc = amount_usd / entry_price
    - Example: $100 USD ÷ $102,000/BTC = 0.000980 BTC
    - Now system correctly buys $100 worth of BTC, not 100 BTC

    WHY THIS MATTERS:
    - Without this fix: System would try to buy millions of dollars of BTC
    - With this fix: System correctly buys $100 worth (as intended)
    - This is a UNIT CONVERSION issue, not a calculation error

    Args:
        result: Parsed and validated LLM response (amount in USD dollars)
        entry_price: Current market price in USD per BTC

    Returns:
        TradeDecision: Validated trade decision object (amount in BTC)

    Example:
        >>> result = {"action": "buy", "amount": 100, "confidence": 0.8, ...}
        >>> entry_price = 102000.0  # BTC price: $102,000
        >>> decision = _create_trade_decision(result, entry_price)
        >>> decision.action
        'buy'
        >>> decision.amount  # Converted to BTC
        0.000980  # $100 / $102,000 = 0.000980 BTC
    """
    # =========================================================================
    # CRITICAL: LLM returns amount in USD, but TradeDecision expects BTC
    # =========================================================================
    amount_usd = float(result["amount"])  # LLM says: "amount": 100 (means $100 USD)

    logger.info(f" LLM returned: action={result['action']}, amount_usd=${amount_usd:.2f}")

    # Convert USD to BTC based on current entry price
    if result["action"] == "buy":
        if amount_usd > 0:
            # BUY with valid amount: Convert USD to BTC
            # Example: $100 USD ÷ $102,000/BTC = 0.000980 BTC
            amount_btc = amount_usd / entry_price
            logger.info(f" Converted ${amount_usd:.2f} USD → {amount_btc:.8f} BTC at ${entry_price:,.2f}/BTC")
        else:
            # BUY with $0 amount - this is an ERROR from LLM
            logger.error(f" LLM returned BUY with amount=$0! This violates the prompt rules.")
            logger.error(f" Using minimum valid amount (0.0001 BTC) and changing action to HOLD")
            amount_btc = 0.0001
            result["action"] = "hold"  # Override to hold
            result["reasoning"] = f"LLM error: returned BUY with $0 amount. Changed to HOLD. Original reasoning: {result.get('reasoning', 'N/A')}"

    elif result["action"] == "hold":
        # HOLD: Use minimum valid amount for Pydantic validation (not used for trading)
        # TradeDecision model requires amount > 0, so we use 0.0001 BTC as placeholder
        amount_btc = 0.0001
        logger.info(f" HOLD decision: using placeholder amount (0.0001 BTC)")

    else:
        # FALLBACK: Minimum valid amount (should never reach here)
        logger.warning(f" Unknown action '{result['action']}', using minimum valid amount")
        amount_btc = 0.0001

    return TradeDecision(
        action=result["action"],
        amount=amount_btc,  # Now in BTC
        entry_price=entry_price,
        confidence=float(result.get("confidence", 0.7)),
        reasoning=result.get("reasoning", "DCA decision based on market conditions"),
        timestamp=datetime.now().isoformat(),
        strategy="dca",
    )


def _hold_decision(price: float, reason: str) -> TradeDecision:
    """Generate safe hold decision when analysis fails.

    This ensures the system always returns a valid decision,
    even when LLM calls fail. The default is conservative (hold).

    Args:
        price: Current market price
        reason: Error message describing the failure

    Returns:
        TradeDecision: Hold decision with error context

    Example:
        >>> decision = _hold_decision(106000.0, "API timeout")
        >>> decision.action
        'hold'
        >>> decision.amount
        0.0
    """
    logger.warning(f"Using hold decision due to: {reason}")

    return TradeDecision(
        action="hold",
        amount=0.0001,  # Minimum valid amount for validation
        entry_price=price if price > 100 else 100.0,  # Ensure valid price
        confidence=1.0,
        reasoning=f"DCA decision failed: {reason}. Defaulting to hold for safety.",
        timestamp=datetime.now().isoformat(),
        strategy="dca",
    )


# For testing
if __name__ == "__main__":
    # Configure detailed logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    from data_models import (
        MarketData,
        PortfolioState,
        TechnicalIndicators,
    )

    print("=" * 60)
    print("DCA Decision Agent - Test")
    print("=" * 60)

    # Create sample market data (DCA opportunity - price drop)
    market_data = MarketData(
        price=102000.0,
        volume=32000000000.0,
        timestamp="2025-01-10T14:00:00Z",
        change_24h=-4.2,  # Strong drop (triggers DCA threshold)
        high_24h=107000.0,
        low_24h=101500.0,
    )

    # Create sample technical indicators (oversold)
    indicators = TechnicalIndicators(
        rsi_14=32.5,  # Oversold (good for DCA)
        macd=-850.5,
        macd_signal=-780.2,
        macd_histogram=-70.3,
        atr_14=2100.0,
        sma_50=105500.0,
        ema_12=103200.0,
        ema_26=104800.0,
    )

    # Create sample portfolio
    portfolio = PortfolioState(
        btc_balance=0.5,
        usd_balance=5000.0,  # Sufficient for DCA
        active_positions=[],
        last_updated="2025-01-10T14:00:00Z",
    )

    # Create trading state
    state = {
        "market_data": market_data,
        "indicators": indicators,
        "portfolio_state": portfolio,
        "config": {"dca_threshold": 3.0, "dca_amount": 100},
        "market_analysis": {"trend": "bearish"},
        "sentiment_analysis": {"sentiment": "fear"},
        "rag_patterns": {"similar_patterns": 5, "success_rate": 0.75, "avg_outcome": 5.2},
    }

    print("\n Market Conditions:")
    print(f"  Price: ${market_data.price:,.2f} ({market_data.change_24h:+.2f}%)")
    print(f"  RSI: {indicators.rsi_14:.1f} (oversold)")
    print(f"  USD Balance: ${portfolio.usd_balance:,.2f}")

    print("\n DCA Configuration:")
    print(f"  Threshold: {state['config']['dca_threshold']}% drop")
    print(f"  Amount: ${state['config']['dca_amount']}")

    print("\n Calling LangChain DCA Decision Agent...")
    print("-" * 60)

    try:
        decision = make_dca_decision(state)

        print("\n DCA Decision Result:")
        print(f"  Action: {decision.action.upper()}")
        print(f"  Amount: ${decision.amount:.2f}")
        print(f"  Entry Price: ${decision.entry_price:,.2f}")
        print(f"  Confidence: {decision.confidence:.2%}")
        print(f"  Strategy: {decision.strategy.upper()}")
        print(f"  Reasoning: {decision.reasoning}")

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
