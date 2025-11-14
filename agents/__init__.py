"""Agent implementations for the Bitcoin trading system.

This module contains the core agent implementations for the multi-agent trading system.
Each agent has specific responsibilities in the trading decision pipeline.

Files in this directory:
- base_agent.py: Base agent class with LLM integration and shared functionality
- market_analyst.py: Analyzes market data, trends, indicators, and sentiment
- risk_manager.py: Evaluates risk, determines position sizing, and sets stop losses
- strategy_agent.py: Selects optimal trading strategy (DCA/Swing/Day/HOLD)
- execution_agent.py: Validates and executes trades via Binance API

LangChain Agents (function-based):
- market_analysis_agent.py: Market trend analysis using LangChain + OpenRouter
- sentiment_analysis_agent.py: Sentiment analysis using LangChain + OpenRouter
- dca_decision_agent.py: DCA buy decisions using LangChain + OpenRouter
- risk_assessment_agent.py: Risk assessment using LangChain + OpenRouter

Example (Class-based agents):
    >>> from agents import MarketAnalystAgent, RiskManagerAgent
    >>> from data_models import MarketData, TechnicalIndicators
    >>>
    >>> market_analyst = MarketAnalystAgent()
    >>> risk_manager = RiskManagerAgent()
    >>>
    >>> analysis = market_analyst.execute(market_data, indicators, sentiment)
    >>> print(f"Trend: {analysis['trend']}, Confidence: {analysis['confidence']}%")

Example (LangChain agents):
    >>> from agents import analyze_market, analyze_sentiment, make_dca_decision, assess_risk
    >>> from data_models import MarketData, TechnicalIndicators, SentimentData
    >>>
    >>> # Market analysis
    >>> result = analyze_market(market_data, indicators)
    >>> print(f"Trend: {result['trend']}, Confidence: {result['confidence']:.2%}")
    >>>
    >>> # Sentiment analysis
    >>> sentiment_result = analyze_sentiment(sentiment_data, market_data, indicators)
    >>> print(f"Sentiment: {sentiment_result['sentiment']}")
    >>>
    >>> # DCA decision
    >>> state = {"market_data": market_data, "indicators": indicators, ...}
    >>> decision = make_dca_decision(state)
    >>> print(f"Action: {decision.action}, Amount: ${decision.amount}")
    >>>
    >>> # Risk assessment
    >>> risk = assess_risk(portfolio, market_data, indicators, config)
    >>> print(f"Position: ${risk['recommended_position_usd']:.2f}")
"""

from typing import List

# Import base agent
from agents.base_agent import BaseAgent, AgentError

# Import specialized agents (class-based)
from agents.market_analyst import MarketAnalystAgent
from agents.risk_manager import RiskManagerAgent
from agents.strategy_agent import StrategyAgent
from agents.execution_agent import ExecutionAgent

# Import LangChain agents (function-based)
from agents.market_analysis_agent import analyze_market
from agents.sentiment_analysis_agent import analyze_sentiment
from agents.dca_decision_agent import make_dca_decision
from agents.risk_assessment_agent import assess_risk

__all__: List[str] = [
    # Base classes
    "BaseAgent",
    "AgentError",
    # Specialized agents (class-based)
    "MarketAnalystAgent",
    "RiskManagerAgent",
    "StrategyAgent",
    "ExecutionAgent",
    # LangChain agents (function-based)
    "analyze_market",
    "analyze_sentiment",
    "make_dca_decision",
    "assess_risk",
]
