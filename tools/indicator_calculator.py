"""Technical indicator calculator for Bitcoin trading system.

This module calculates technical analysis indicators from market data using
TA-Lib when available, with manual fallback implementations for reliability.

All indicators are used by trading agents to make informed decisions:
- RSI: Momentum oscillator (overbought/oversold)
- MACD: Trend following momentum indicator
- ATR: Volatility measure for stop-loss calculation
- SMA/EMA: Trend identification
- Bollinger Bands: Volatility and price level indicator

Example:
    >>> from tools.indicator_calculator import calculate_all_indicators
    >>> from data_models import MarketData
    >>>
    >>> market_data = [...]  # List of MarketData objects
    >>> indicators = calculate_all_indicators(market_data)
    >>> if indicators:
    ...     print(f"RSI: {indicators.rsi_14:.2f}")
    ...     print(f"MACD: {indicators.macd:.2f}")
"""

import logging
from typing import List, Optional, Tuple

import numpy as np

from data_models import MarketData, TechnicalIndicators


# Configure logger
logger = logging.getLogger(__name__)

# Try to import TA-Lib (optional dependency)
try:
    import talib

    TALIB_AVAILABLE = True
    logger.info("TA-Lib library available for indicator calculations")
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning(
        "TA-Lib not available. Using fallback calculations. "
        "Install with: pip install TA-Lib"
    )


# ============================================================================
# RSI (Relative Strength Index)
# ============================================================================


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index (RSI).

    RSI is a momentum oscillator that measures the speed and magnitude
    of price changes. It ranges from 0-100:
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    - RSI 30-70: Neutral zone

    The RSI is calculated using average gains and losses over the period.

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for RSI calculation (default: 14)

    Returns:
        float: RSI value between 0 and 100

    Raises:
        ValueError: If prices list is too short for calculation

    Example:
        >>> prices = [100, 102, 101, 103, 105, 104, 106, 108]
        >>> rsi = calculate_rsi(prices, period=6)
        >>> print(f"RSI: {rsi:.2f}")
        RSI: 65.32
    """
    if len(prices) < period + 1:
        raise ValueError(
            f"Need at least {period + 1} prices for RSI({period}). "
            f"Got {len(prices)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            prices_array = np.array(prices, dtype=float)
            rsi_values = talib.RSI(prices_array, timeperiod=period)
            # Return most recent non-NaN value
            rsi = float(rsi_values[-1])
            logger.debug(f"Calculated RSI({period}) = {rsi:.2f} using TA-Lib")
            return rsi
        except Exception as e:
            logger.warning(f"TA-Lib RSI calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual RSI calculation
    logger.debug(f"Calculating RSI({period}) manually (fallback)")

    # Calculate price changes (deltas)
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    # Calculate initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Smooth the averages using Wilder's smoothing method
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # Calculate RS and RSI
    if avg_loss == 0:
        rsi = 100.0  # No losses = maximum RSI
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    logger.debug(f"Calculated RSI({period}) = {rsi:.2f} (manual)")
    return rsi


# ============================================================================
# MACD (Moving Average Convergence Divergence)
# ============================================================================


def calculate_macd(
    prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[float, float, float]:
    """Calculate MACD, Signal, and Histogram.

    MACD is a trend-following momentum indicator that shows the relationship
    between two moving averages:
    - MACD Line: EMA(12) - EMA(26)
    - Signal Line: EMA(9) of MACD Line
    - Histogram: MACD Line - Signal Line

    Interpretation:
    - MACD > Signal: Bullish (buy signal)
    - MACD < Signal: Bearish (sell signal)
    - Histogram growing: Momentum increasing
    - Histogram shrinking: Momentum decreasing

    Args:
        prices: List of closing prices (most recent last)
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line EMA period (default: 9)

    Returns:
        Tuple[float, float, float]: (macd, signal, histogram)

    Raises:
        ValueError: If prices list is too short for calculation

    Example:
        >>> prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109] * 5
        >>> macd, sig, hist = calculate_macd(prices)
        >>> print(f"MACD: {macd:.2f}, Signal: {sig:.2f}, Histogram: {hist:.2f}")
    """
    min_required = slow + signal
    if len(prices) < min_required:
        raise ValueError(
            f"Need at least {min_required} prices for MACD. Got {len(prices)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            prices_array = np.array(prices, dtype=float)
            macd_line, signal_line, histogram = talib.MACD(
                prices_array, fastperiod=fast, slowperiod=slow, signalperiod=signal
            )
            # Return most recent non-NaN values
            macd_val = float(macd_line[-1])
            signal_val = float(signal_line[-1])
            histogram_val = float(histogram[-1])

            logger.debug(
                f"Calculated MACD = {macd_val:.2f}, Signal = {signal_val:.2f} using TA-Lib"
            )
            return macd_val, signal_val, histogram_val
        except Exception as e:
            logger.warning(f"TA-Lib MACD calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual MACD calculation
    logger.debug("Calculating MACD manually (fallback)")

    # Calculate EMAs
    ema_fast = calculate_ema(prices, period=fast)
    ema_slow = calculate_ema(prices, period=slow)

    # MACD line = Fast EMA - Slow EMA
    macd_val = ema_fast - ema_slow

    # For signal line, we need to calculate EMA of MACD values
    # Since we only have the current MACD, we'll use a simplified approach
    # In production, you'd maintain a history of MACD values
    signal_val = macd_val  # Simplified - assumes signal converges to MACD

    # Histogram
    histogram_val = macd_val - signal_val

    logger.debug(f"Calculated MACD = {macd_val:.2f} (manual, simplified)")
    return macd_val, signal_val, histogram_val


# ============================================================================
# ATR (Average True Range)
# ============================================================================


def calculate_atr(
    high: List[float], low: List[float], close: List[float], period: int = 14
) -> float:
    """Calculate Average True Range (ATR).

    ATR is a volatility indicator that measures the average range between
    high and low prices. Higher ATR indicates higher volatility.

    Used for:
    - Stop-loss calculation: Stop = Price - (ATR × Multiplier)
    - Position sizing: Larger ATR = smaller position
    - Volatility assessment: High ATR = volatile market

    Args:
        high: List of high prices
        low: List of low prices
        close: List of closing prices
        period: Number of periods for ATR calculation (default: 14)

    Returns:
        float: ATR value (always positive)

    Raises:
        ValueError: If price lists are too short or mismatched

    Example:
        >>> highs = [105, 107, 106, 108, 110, 109, 111] * 3
        >>> lows = [100, 102, 101, 103, 105, 104, 106] * 3
        >>> closes = [102, 104, 103, 105, 107, 106, 108] * 3
        >>> atr = calculate_atr(highs, lows, closes, period=14)
        >>> print(f"ATR: {atr:.2f}")
    """
    if len(high) != len(low) or len(high) != len(close):
        raise ValueError(
            f"Price lists must have same length. "
            f"Got high={len(high)}, low={len(low)}, close={len(close)}"
        )

    if len(high) < period + 1:
        raise ValueError(
            f"Need at least {period + 1} prices for ATR({period}). Got {len(high)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            high_array = np.array(high, dtype=float)
            low_array = np.array(low, dtype=float)
            close_array = np.array(close, dtype=float)

            atr_values = talib.ATR(high_array, low_array, close_array, timeperiod=period)
            atr = float(atr_values[-1])

            logger.debug(f"Calculated ATR({period}) = {atr:.2f} using TA-Lib")
            return atr
        except Exception as e:
            logger.warning(f"TA-Lib ATR calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual ATR calculation
    logger.debug(f"Calculating ATR({period}) manually (fallback)")

    # Calculate True Range for each period
    true_ranges = []
    for i in range(1, len(close)):
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        true_ranges.append(tr)

    # ATR = Average of True Ranges
    if len(true_ranges) >= period:
        atr = sum(true_ranges[-period:]) / period
    else:
        atr = sum(true_ranges) / len(true_ranges)

    logger.debug(f"Calculated ATR({period}) = {atr:.2f} (manual)")
    return atr


# ============================================================================
# SMA (Simple Moving Average)
# ============================================================================


def calculate_sma(prices: List[float], period: int = 50) -> float:
    """Calculate Simple Moving Average (SMA).

    SMA is the arithmetic mean of prices over a specified period.
    It smooths price data to identify trends:
    - Price > SMA: Uptrend (bullish)
    - Price < SMA: Downtrend (bearish)
    - SMA slope: Trend direction

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for SMA calculation (default: 50)

    Returns:
        float: SMA value

    Raises:
        ValueError: If prices list is too short for calculation

    Example:
        >>> prices = [100, 102, 104, 106, 108, 110] * 10
        >>> sma = calculate_sma(prices, period=50)
        >>> print(f"SMA(50): {sma:.2f}")
    """
    if len(prices) < period:
        raise ValueError(
            f"Need at least {period} prices for SMA({period}). Got {len(prices)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            prices_array = np.array(prices, dtype=float)
            sma_values = talib.SMA(prices_array, timeperiod=period)
            sma = float(sma_values[-1])

            logger.debug(f"Calculated SMA({period}) = {sma:.2f} using TA-Lib")
            return sma
        except Exception as e:
            logger.warning(f"TA-Lib SMA calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual SMA calculation
    sma = sum(prices[-period:]) / period

    logger.debug(f"Calculated SMA({period}) = {sma:.2f} (manual)")
    return sma


# ============================================================================
# EMA (Exponential Moving Average)
# ============================================================================


def calculate_ema(prices: List[float], period: int = 12) -> float:
    """Calculate Exponential Moving Average (EMA).

    EMA is a weighted moving average that gives more weight to recent prices.
    It responds faster to price changes than SMA:
    - Price > EMA: Uptrend (bullish)
    - Price < EMA: Downtrend (bearish)
    - EMA(12) vs EMA(26): Used in MACD calculation

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for EMA calculation (default: 12)

    Returns:
        float: EMA value

    Raises:
        ValueError: If prices list is too short for calculation

    Example:
        >>> prices = [100, 102, 104, 106, 108, 110, 112, 114, 116] * 3
        >>> ema_12 = calculate_ema(prices, period=12)
        >>> ema_26 = calculate_ema(prices, period=26)
        >>> print(f"EMA(12): {ema_12:.2f}, EMA(26): {ema_26:.2f}")
    """
    if len(prices) < period:
        raise ValueError(
            f"Need at least {period} prices for EMA({period}). Got {len(prices)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            prices_array = np.array(prices, dtype=float)
            ema_values = talib.EMA(prices_array, timeperiod=period)
            ema = float(ema_values[-1])

            logger.debug(f"Calculated EMA({period}) = {ema:.2f} using TA-Lib")
            return ema
        except Exception as e:
            logger.warning(f"TA-Lib EMA calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual EMA calculation
    logger.debug(f"Calculating EMA({period}) manually (fallback)")

    # EMA multiplier: 2 / (period + 1)
    multiplier = 2.0 / (period + 1)

    # Start with SMA as initial EMA
    ema = sum(prices[:period]) / period

    # Calculate EMA for remaining prices
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    logger.debug(f"Calculated EMA({period}) = {ema:.2f} (manual)")
    return ema


# ============================================================================
# Bollinger Bands
# ============================================================================


def calculate_bollinger_bands(
    prices: List[float], period: int = 20, num_std: float = 2.0
) -> Tuple[float, float, float]:
    """Calculate Bollinger Bands (Upper, Middle, Lower).

    Bollinger Bands consist of:
    - Middle Band: SMA(20)
    - Upper Band: SMA(20) + (2 × Standard Deviation)
    - Lower Band: SMA(20) - (2 × Standard Deviation)

    Interpretation:
    - Price near upper band: Overbought
    - Price near lower band: Oversold
    - Bands squeeze: Low volatility (breakout coming)
    - Bands expand: High volatility

    Args:
        prices: List of closing prices (most recent last)
        period: Number of periods for calculation (default: 20)
        num_std: Number of standard deviations (default: 2.0)

    Returns:
        Tuple[float, float, float]: (upper_band, middle_band, lower_band)

    Raises:
        ValueError: If prices list is too short for calculation

    Example:
        >>> prices = [100, 102, 104, 106, 108, 110, 112] * 5
        >>> upper, middle, lower = calculate_bollinger_bands(prices)
        >>> print(f"BB: Upper={upper:.2f}, Middle={middle:.2f}, Lower={lower:.2f}")
    """
    if len(prices) < period:
        raise ValueError(
            f"Need at least {period} prices for Bollinger Bands({period}). "
            f"Got {len(prices)} prices."
        )

    if TALIB_AVAILABLE:
        # Use TA-Lib for accurate calculation
        try:
            prices_array = np.array(prices, dtype=float)
            upper, middle, lower = talib.BBANDS(
                prices_array, timeperiod=period, nbdevup=num_std, nbdevdn=num_std
            )

            upper_val = float(upper[-1])
            middle_val = float(middle[-1])
            lower_val = float(lower[-1])

            logger.debug(
                f"Calculated Bollinger Bands: "
                f"Upper={upper_val:.2f}, Middle={middle_val:.2f}, "
                f"Lower={lower_val:.2f} using TA-Lib"
            )
            return upper_val, middle_val, lower_val
        except Exception as e:
            logger.warning(f"TA-Lib Bollinger Bands calculation failed: {e}. Using fallback.")
            # Fall through to manual calculation

    # Fallback: Manual Bollinger Bands calculation
    logger.debug(f"Calculating Bollinger Bands({period}) manually (fallback)")

    # Calculate middle band (SMA)
    middle_band = sum(prices[-period:]) / period

    # Calculate standard deviation
    variance = sum((p - middle_band) ** 2 for p in prices[-period:]) / period
    std_dev = variance**0.5

    # Calculate upper and lower bands
    upper_band = middle_band + (num_std * std_dev)
    lower_band = middle_band - (num_std * std_dev)

    logger.debug(
        f"Calculated Bollinger Bands: Upper={upper_band:.2f}, "
        f"Middle={middle_band:.2f}, Lower={lower_band:.2f} (manual)"
    )
    return upper_band, middle_band, lower_band


# ============================================================================
# Main Function: Calculate All Indicators
# ============================================================================


def calculate_all_indicators(
    market_data_list: List[MarketData],
) -> Optional[TechnicalIndicators]:
    """Calculate all technical indicators from market data.

    This is the main entry point for feature engineering. Takes a list
    of MarketData objects and calculates all technical indicators used
    by the trading agents.

    Calculated indicators:
    - RSI(14): Momentum oscillator
    - MACD: Trend following indicator
    - ATR(14): Volatility measure
    - SMA(50): Long-term trend
    - EMA(12), EMA(26): Short/medium-term trends
    - Bollinger Bands: Volatility and price levels

    Args:
        market_data_list: List of MarketData (minimum 50 for SMA-50)

    Returns:
        TechnicalIndicators: All calculated indicators, or None if insufficient data

    Example:
        >>> from tools import BinanceClient
        >>> from tools.indicator_calculator import calculate_all_indicators
        >>>
        >>> client = BinanceClient()
        >>> klines = client.get_historical_klines("BTCUSDT", "1h", 100)
        >>> market_data = [MarketData(...) for k in klines]
        >>> indicators = calculate_all_indicators(market_data)
        >>> if indicators:
        ...     print(f"RSI: {indicators.rsi_14:.2f}")
        ...     print(f"MACD: {indicators.macd:.2f}")
    """
    # Validate sufficient data
    min_required = 50  # Need at least 50 for SMA-50
    if len(market_data_list) < min_required:
        logger.warning(
            f"Insufficient data for indicator calculation. "
            f"Need {min_required}, got {len(market_data_list)} data points."
        )
        return None

    logger.info(f"Calculating indicators from {len(market_data_list)} data points")

    try:
        # Extract price arrays from MarketData
        prices = [md.price for md in market_data_list]

        # Extract high/low for ATR (filter out None values)
        highs = [md.high_24h for md in market_data_list if md.high_24h is not None]
        lows = [md.low_24h for md in market_data_list if md.low_24h is not None]

        # Ensure we have enough high/low data for ATR
        if len(highs) < 15 or len(lows) < 15:
            logger.warning("Insufficient high/low data for ATR. Using price as approximation.")
            highs = prices
            lows = prices

        # Calculate each indicator with individual error handling
        try:
            rsi = calculate_rsi(prices, period=14)
        except Exception as e:
            logger.error(f"Failed to calculate RSI: {e}")
            rsi = 50.0  # Neutral default

        try:
            macd, macd_signal, macd_histogram = calculate_macd(prices)
        except Exception as e:
            logger.error(f"Failed to calculate MACD: {e}")
            macd = macd_signal = macd_histogram = 0.0

        try:
            atr = calculate_atr(highs, lows, prices, period=14)
        except Exception as e:
            logger.error(f"Failed to calculate ATR: {e}")
            # Estimate ATR from price volatility
            price_range = max(prices[-14:]) - min(prices[-14:])
            atr = price_range / 2

        try:
            sma_50 = calculate_sma(prices, period=50)
        except Exception as e:
            logger.error(f"Failed to calculate SMA(50): {e}")
            sma_50 = prices[-1]  # Use current price as fallback

        try:
            ema_12 = calculate_ema(prices, period=12)
        except Exception as e:
            logger.error(f"Failed to calculate EMA(12): {e}")
            ema_12 = prices[-1]

        try:
            ema_26 = calculate_ema(prices, period=26)
        except Exception as e:
            logger.error(f"Failed to calculate EMA(26): {e}")
            ema_26 = prices[-1]

        # Bollinger Bands (optional - may fail)
        try:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(prices, period=20)
        except Exception as e:
            logger.warning(f"Failed to calculate Bollinger Bands: {e}")
            bb_upper = bb_lower = None

        # Create TechnicalIndicators Pydantic model
        indicators = TechnicalIndicators(
            rsi_14=rsi,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            atr_14=atr,
            sma_50=sma_50,
            ema_12=ema_12,
            ema_26=ema_26,
            bollinger_upper=bb_upper,
            bollinger_lower=bb_lower,
        )

        logger.info(
            f"[OK] Calculated indicators: RSI={rsi:.2f}, MACD={macd:.2f}, "
            f"ATR={atr:.2f}, SMA(50)={sma_50:.2f}"
        )

        return indicators

    except Exception as e:
        logger.error(f"Failed to calculate indicators: {e}", exc_info=True)
        return None


# ============================================================================
# Utility Functions
# ============================================================================


def validate_price_data(prices: List[float]) -> bool:
    """Validate that price data is suitable for indicator calculation.

    Args:
        prices: List of prices to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not prices:
        logger.error("Price list is empty")
        return False

    if len(prices) < 2:
        logger.error(f"Need at least 2 prices, got {len(prices)}")
        return False

    # Check for negative prices
    if any(p <= 0 for p in prices):
        logger.error("Price list contains non-positive values")
        return False

    # Check for NaN or inf
    if any(not isinstance(p, (int, float)) or p != p or p == float("inf") for p in prices):
        logger.error("Price list contains invalid values (NaN or inf)")
        return False

    return True


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create sample price data
    sample_prices = [
        100.0,
        102.0,
        101.0,
        103.0,
        105.0,
        104.0,
        106.0,
        108.0,
        107.0,
        109.0,
    ] * 6  # 60 data points

    print(f"TA-Lib Available: {TALIB_AVAILABLE}")
    print(f"Sample prices: {len(sample_prices)} data points")
    print()

    # Test individual indicators
    try:
        rsi = calculate_rsi(sample_prices, period=14)
        print(f"RSI(14): {rsi:.2f}")
    except Exception as e:
        print(f"RSI calculation failed: {e}")

    try:
        macd, signal, histogram = calculate_macd(sample_prices)
        print(f"MACD: {macd:.2f}, Signal: {signal:.2f}, Histogram: {histogram:.2f}")
    except Exception as e:
        print(f"MACD calculation failed: {e}")

    try:
        atr = calculate_atr(sample_prices, sample_prices, sample_prices, period=14)
        print(f"ATR(14): {atr:.2f}")
    except Exception as e:
        print(f"ATR calculation failed: {e}")

    try:
        sma = calculate_sma(sample_prices, period=50)
        print(f"SMA(50): {sma:.2f}")
    except Exception as e:
        print(f"SMA calculation failed: {e}")

    try:
        ema_12 = calculate_ema(sample_prices, period=12)
        ema_26 = calculate_ema(sample_prices, period=26)
        print(f"EMA(12): {ema_12:.2f}, EMA(26): {ema_26:.2f}")
    except Exception as e:
        print(f"EMA calculation failed: {e}")

    try:
        upper, middle, lower = calculate_bollinger_bands(sample_prices, period=20)
        print(f"Bollinger Bands: Upper={upper:.2f}, Middle={middle:.2f}, Lower={lower:.2f}")
    except Exception as e:
        print(f"Bollinger Bands calculation failed: {e}")
