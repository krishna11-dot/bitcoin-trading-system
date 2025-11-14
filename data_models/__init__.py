"""Pydantic data models for type-safe data validation.

This module contains all Pydantic schemas used throughout the system
for data validation, serialization, and type safety.

Files in this directory:
- market_data.py: Market data models (price, volume, 24h stats)
- indicators.py: Technical analysis indicators (RSI, MACD, ATR, MAs, Bollinger)
- decisions.py: Trading decision models (buy/sell/hold with risk management)
- portfolio.py: Portfolio state tracking (balances, positions, P/L)
- sentiment.py: Market sentiment data (fear/greed, news, social volume)

Example:
    >>> from data_models import MarketData, TechnicalIndicators, TradeDecision
    >>> market = MarketData(price=45000.0, volume=1000000.0, ...)
    >>> indicators = TechnicalIndicators(rsi_14=65.5, macd=120.5, ...)
    >>> decision = TradeDecision(action="buy", amount=0.05, ...)
"""

from typing import List

# Import all models for easy access
from data_models.market_data import MarketData
from data_models.indicators import TechnicalIndicators
from data_models.decisions import TradeDecision
from data_models.portfolio import PortfolioState
from data_models.sentiment import SentimentData
from data_models.positions import Position

__all__: List[str] = [
    # Market data
    "MarketData",
    # Technical indicators
    "TechnicalIndicators",
    # Trading decisions
    "TradeDecision",
    # Portfolio state
    "PortfolioState",
    # Sentiment data
    "SentimentData",
    # Position tracking
    "Position",
]
