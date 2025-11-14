"""Market sentiment models for Bitcoin trading system.

This module defines Pydantic models for market sentiment data including
fear & greed index, social volume, news sentiment, and trending scores.

Example:
    >>> from data_models.sentiment import SentimentData
    >>> sentiment = SentimentData(
    ...     fear_greed_index=35,
    ...     social_volume="high",
    ...     news_sentiment=0.25,
    ...     trending_score=75,
    ...     timestamp="2025-01-15T10:30:00Z"
    ... )
    >>> print(f"Market sentiment: {sentiment.get_fear_greed_label()}")
    Market sentiment: Fear
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SentimentData(BaseModel):
    """Market sentiment indicators for Bitcoin.

    This model captures various sentiment metrics that help gauge market
    psychology and crowd behavior. Sentiment data is a contrarian indicator
    often used to identify market extremes.

    Attributes:
        fear_greed_index: Fear & Greed Index (0-100, lower = fear, higher = greed)
        social_volume: Social media activity level (low, medium, high)
        news_sentiment: News sentiment score (-1.0 = very negative, +1.0 = very positive)
        trending_score: Trending score on social media (optional, 0-100)
        timestamp: ISO 8601 timestamp of sentiment data

    Example:
        >>> sentiment = SentimentData(
        ...     fear_greed_index=35,
        ...     social_volume="high",
        ...     news_sentiment=0.25,
        ...     timestamp="2025-01-15T10:30:00Z"
        ... )
    """

    # Fear & Greed Index (0-100)
    # 0-24: Extreme Fear
    # 25-44: Fear
    # 45-55: Neutral
    # 56-75: Greed
    # 76-100: Extreme Greed
    fear_greed_index: int = Field(
        ...,
        description="Fear & Greed Index (0-100)",
        ge=0,
        le=100,
        examples=[15, 35, 50, 70, 85],
    )

    # Social media activity level
    social_volume: Literal["low", "medium", "high"] = Field(
        ...,
        description="Social media activity level",
        examples=["low", "medium", "high"],
    )

    # News sentiment score (-1.0 to +1.0)
    # -1.0 = Very negative news
    # 0.0 = Neutral news
    # +1.0 = Very positive news
    news_sentiment: float = Field(
        ...,
        description="News sentiment score (-1.0 to +1.0)",
        ge=-1.0,
        le=1.0,
        examples=[-0.75, -0.25, 0.0, 0.25, 0.75],
    )

    # Trending score (optional, 0-100)
    trending_score: Optional[int] = Field(
        default=None,
        description="Trending score on social media (0-100)",
        ge=0,
        le=100,
        examples=[25, 50, 75, 100],
    )

    # Metadata
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of sentiment data",
        examples=["2025-01-15T10:30:00Z", "2025-01-15T14:45:30Z"],
    )

    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "fear_greed_index": 35,
                    "social_volume": "high",
                    "news_sentiment": 0.25,
                    "trending_score": 75,
                    "timestamp": "2025-01-15T10:30:00Z",
                },
                {
                    "fear_greed_index": 85,
                    "social_volume": "low",
                    "news_sentiment": -0.50,
                    "trending_score": 30,
                    "timestamp": "2025-01-15T14:45:30Z",
                },
                {
                    "fear_greed_index": 15,
                    "social_volume": "medium",
                    "news_sentiment": -0.75,
                    "timestamp": "2025-01-16T08:00:00Z",
                },
            ]
        },
    )

    @field_validator("fear_greed_index")
    @classmethod
    def validate_fear_greed_index(cls, v: int) -> int:
        """Validate Fear & Greed Index is within 0-100 range.

        Args:
            v: Fear & Greed Index value

        Returns:
            int: Validated index value

        Raises:
            ValueError: If index is outside 0-100 range
        """
        if not 0 <= v <= 100:
            raise ValueError(
                f"Fear & Greed Index must be between 0 and 100 (got {v}). "
                f"This indicates a data error."
            )
        return v

    @field_validator("news_sentiment")
    @classmethod
    def validate_news_sentiment(cls, v: float) -> float:
        """Validate news sentiment is within -1.0 to +1.0 range.

        Args:
            v: News sentiment score

        Returns:
            float: Validated sentiment score

        Raises:
            ValueError: If sentiment is outside valid range
        """
        if not -1.0 <= v <= 1.0:
            raise ValueError(
                f"News sentiment must be between -1.0 and +1.0 (got {v:.2f}). "
                f"This indicates a calculation error."
            )
        return v

    @field_validator("trending_score")
    @classmethod
    def validate_trending_score(cls, v: Optional[int]) -> Optional[int]:
        """Validate trending score is within 0-100 range.

        Args:
            v: Trending score value

        Returns:
            Optional[int]: Validated trending score or None

        Raises:
            ValueError: If score is outside valid range
        """
        if v is not None:
            if not 0 <= v <= 100:
                raise ValueError(
                    f"Trending score must be between 0 and 100 (got {v})"
                )
        return v

    def get_fear_greed_label(self) -> str:
        """Get human-readable label for Fear & Greed Index.

        Returns:
            str: Label describing current sentiment level

        Example:
            >>> sentiment = SentimentData(fear_greed_index=35, ...)
            >>> sentiment.get_fear_greed_label()
            'Fear'
        """
        if self.fear_greed_index <= 24:
            return "Extreme Fear"
        elif self.fear_greed_index <= 44:
            return "Fear"
        elif self.fear_greed_index <= 55:
            return "Neutral"
        elif self.fear_greed_index <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    def is_extreme_fear(self) -> bool:
        """Check if market is in extreme fear (potential buying opportunity).

        Returns:
            bool: True if Fear & Greed Index <= 24

        Example:
            >>> sentiment = SentimentData(fear_greed_index=15, ...)
            >>> sentiment.is_extreme_fear()
            True
        """
        return self.fear_greed_index <= 24

    def is_extreme_greed(self) -> bool:
        """Check if market is in extreme greed (potential selling opportunity).

        Returns:
            bool: True if Fear & Greed Index >= 76

        Example:
            >>> sentiment = SentimentData(fear_greed_index=85, ...)
            >>> sentiment.is_extreme_greed()
            True
        """
        return self.fear_greed_index >= 76

    def is_fear(self) -> bool:
        """Check if market is in fear zone (0-44).

        Returns:
            bool: True if Fear & Greed Index <= 44

        Example:
            >>> sentiment = SentimentData(fear_greed_index=35, ...)
            >>> sentiment.is_fear()
            True
        """
        return self.fear_greed_index <= 44

    def is_greed(self) -> bool:
        """Check if market is in greed zone (56-100).

        Returns:
            bool: True if Fear & Greed Index >= 56

        Example:
            >>> sentiment = SentimentData(fear_greed_index=70, ...)
            >>> sentiment.is_greed()
            True
        """
        return self.fear_greed_index >= 56

    def get_news_sentiment_label(self) -> str:
        """Get human-readable label for news sentiment.

        Returns:
            str: Label describing news sentiment

        Example:
            >>> sentiment = SentimentData(news_sentiment=0.25, ...)
            >>> sentiment.get_news_sentiment_label()
            'Slightly Positive'
        """
        if self.news_sentiment <= -0.6:
            return "Very Negative"
        elif self.news_sentiment <= -0.2:
            return "Negative"
        elif self.news_sentiment <= 0.2:
            return "Neutral"
        elif self.news_sentiment <= 0.6:
            return "Positive"
        else:
            return "Very Positive"

    def is_news_bullish(self) -> bool:
        """Check if news sentiment is bullish (positive).

        Returns:
            bool: True if news sentiment > 0.2

        Example:
            >>> sentiment = SentimentData(news_sentiment=0.50, ...)
            >>> sentiment.is_news_bullish()
            True
        """
        return self.news_sentiment > 0.2

    def is_news_bearish(self) -> bool:
        """Check if news sentiment is bearish (negative).

        Returns:
            bool: True if news sentiment < -0.2

        Example:
            >>> sentiment = SentimentData(news_sentiment=-0.50, ...)
            >>> sentiment.is_news_bearish()
            True
        """
        return self.news_sentiment < -0.2

    def is_high_social_activity(self) -> bool:
        """Check if social media activity is high.

        Returns:
            bool: True if social volume is 'high'

        Example:
            >>> sentiment = SentimentData(social_volume="high", ...)
            >>> sentiment.is_high_social_activity()
            True
        """
        return self.social_volume == "high"

    def is_low_social_activity(self) -> bool:
        """Check if social media activity is low.

        Returns:
            bool: True if social volume is 'low'

        Example:
            >>> sentiment = SentimentData(social_volume="low", ...)
            >>> sentiment.is_low_social_activity()
            True
        """
        return self.social_volume == "low"

    def get_contrarian_signal(self) -> str:
        """Get contrarian trading signal based on sentiment extremes.

        Contrarian strategy: Buy when others are fearful, sell when greedy.

        Returns:
            str: 'buy', 'sell', or 'neutral'

        Example:
            >>> sentiment = SentimentData(fear_greed_index=15, ...)
            >>> sentiment.get_contrarian_signal()
            'buy'
        """
        if self.is_extreme_fear():
            return "buy"  # Buy when extreme fear
        elif self.is_extreme_greed():
            return "sell"  # Sell when extreme greed
        else:
            return "neutral"

    def get_composite_sentiment_score(self) -> float:
        """Calculate composite sentiment score combining multiple indicators.

        Combines Fear & Greed Index, news sentiment, and social volume
        into a single normalized score (-1.0 to +1.0).

        Returns:
            float: Composite sentiment score (-1.0 = bearish, +1.0 = bullish)

        Example:
            >>> sentiment = SentimentData(
            ...     fear_greed_index=70,
            ...     news_sentiment=0.5,
            ...     social_volume="high",
            ...     ...
            ... )
            >>> sentiment.get_composite_sentiment_score()
            0.55
        """
        # Normalize Fear & Greed Index to -1.0 to +1.0
        fg_normalized = (self.fear_greed_index - 50) / 50.0

        # Social volume modifier (high = +0.1, medium = 0, low = -0.1)
        social_modifier = {
            "high": 0.1,
            "medium": 0.0,
            "low": -0.1,
        }[self.social_volume]

        # Weighted average: FG (50%), News (40%), Social (10%)
        composite = (fg_normalized * 0.5) + (self.news_sentiment * 0.4) + (social_modifier * 1.0)

        # Clamp to -1.0 to +1.0 range
        return max(-1.0, min(1.0, composite))

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            str: Formatted sentiment string
        """
        return (
            f"SentimentData("
            f"FG={self.fear_greed_index} [{self.get_fear_greed_label()}], "
            f"news={self.news_sentiment:+.2f} [{self.get_news_sentiment_label()}], "
            f"social={self.social_volume})"
        )
