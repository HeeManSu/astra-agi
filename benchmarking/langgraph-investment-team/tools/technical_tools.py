"""
Technical Tools — Agno version.

Six yfinance-based tools for the Technical Analyst agent.
Same logic as Astra, plain functions.
"""

from __future__ import annotations

from langchain_core.tools import tool
from typing import Any, cast

import pandas as pd

try:
    import yfinance as yf
except ImportError as e:
    raise ImportError("`yfinance` not installed. pip install yfinance") from e


def _get_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch clean OHLCV history from yfinance."""
    ticker = yf.Ticker(symbol)
    df = cast(pd.DataFrame, ticker.history(period=period))
    if df.empty:
        raise ValueError(f"No price data for {symbol}")
    return df


def _as_series(value: Any, label: str) -> pd.Series:
    if isinstance(value, pd.Series):
        return value
    raise TypeError(f"Expected pandas Series for {label}, got {type(value).__name__}")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    return _as_series(df[name], f"column:{name}")


@tool
def get_price_history(symbol: str, days: int = 20) -> dict:
    """Get recent OHLCV price data for a stock. Returns last N trading days.

    Args:
        symbol (str): Stock ticker symbol (e.g. AAPL, NVDA).
        days (int): Number of recent trading days to return (default 20).
    """
    try:
        df = _get_history(symbol)
        recent = df.tail(days)
        open_series = _col(recent, "Open")
        high_series = _col(recent, "High")
        low_series = _col(recent, "Low")
        close_series = _col(recent, "Close")
        volume_series = _col(recent, "Volume")

        prices = []
        for idx, date in enumerate(recent.index):
            prices.append(
                {
                    "date": str(date)[:10],
                    "open": round(float(open_series.iloc[idx]), 2),
                    "high": round(float(high_series.iloc[idx]), 2),
                    "low": round(float(low_series.iloc[idx]), 2),
                    "close": round(float(close_series.iloc[idx]), 2),
                    "volume": int(float(volume_series.iloc[idx])),
                }
            )

        return {
            "symbol": symbol,
            "period": f"Last {days} trading days",
            "current_price": round(float(_col(df, "Close").iloc[-1]), 2),
            "prices": prices,
        }
    except Exception as e:
        return {"error": f"Error fetching price history for {symbol}: {e}"}


@tool
def calculate_rsi(symbol: str, period: int = 14) -> dict:
    """Calculate the Relative Strength Index (RSI) for a stock. Returns value and overbought/oversold signal.

    Args:
        symbol (str): Stock ticker symbol.
        period (int): RSI lookback period (default 14).
    """
    try:
        df = _get_history(symbol)
        close = _col(df, "Close")
        delta = _as_series(close.diff(), "delta")

        gain = _as_series(delta.where(delta > 0, 0.0), "gain")
        loss = _as_series((-delta).where(delta < 0, 0.0), "loss")

        avg_gain = _as_series(gain.rolling(window=period).mean(), "avg_gain")
        avg_loss = _as_series(loss.rolling(window=period).mean(), "avg_loss")

        rs = _as_series(avg_gain / avg_loss, "rs")
        rsi_series = _as_series(100 - (100 / (1 + rs)), "rsi")
        current_rsi = round(float(rsi_series.iloc[-1]), 1)

        if current_rsi >= 70:
            signal = "overbought"
        elif current_rsi <= 30:
            signal = "oversold"
        else:
            signal = "neutral"

        return {
            "symbol": symbol,
            "rsi": current_rsi,
            "period": period,
            "signal": signal,
        }
    except Exception as e:
        return {"error": f"Error calculating RSI for {symbol}: {e}"}


@tool
def calculate_macd(symbol: str) -> dict:
    """Calculate MACD (12/26/9) for a stock. Returns MACD line, signal line, histogram, and crossover direction.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = _get_history(symbol)
        close = _col(df, "Close")

        ema12 = _as_series(close.ewm(span=12, adjust=False).mean(), "ema12")
        ema26 = _as_series(close.ewm(span=26, adjust=False).mean(), "ema26")
        macd_line = _as_series(ema12 - ema26, "macd_line")
        signal_line = _as_series(macd_line.ewm(span=9, adjust=False).mean(), "signal_line")
        histogram = _as_series(macd_line - signal_line, "histogram")

        current_macd = round(float(macd_line.iloc[-1]), 4)
        current_signal = round(float(signal_line.iloc[-1]), 4)
        current_hist = round(float(histogram.iloc[-1]), 4)
        prev_hist = round(float(histogram.iloc[-2]), 4)

        if current_hist > 0 and prev_hist <= 0:
            crossover = "bullish crossover"
        elif current_hist < 0 and prev_hist >= 0:
            crossover = "bearish crossover"
        elif current_hist > 0:
            crossover = "bullish"
        else:
            crossover = "bearish"

        return {
            "symbol": symbol,
            "macd": current_macd,
            "signal_line": current_signal,
            "histogram": current_hist,
            "crossover": crossover,
        }
    except Exception as e:
        return {"error": f"Error calculating MACD for {symbol}: {e}"}


@tool
def calculate_moving_averages(symbol: str) -> dict:
    """Calculate 20/50/200-day SMAs and classify trend based on price position relative to MAs.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = _get_history(symbol)
        close = _col(df, "Close")
        price = round(float(close.iloc[-1]), 2)

        sma20_series = _as_series(close.rolling(20).mean(), "sma20")
        sma50_series = _as_series(close.rolling(50).mean(), "sma50")
        sma200_series = (
            _as_series(close.rolling(200).mean(), "sma200") if len(close) >= 200 else None
        )

        sma20 = round(float(sma20_series.iloc[-1]), 2)
        sma50 = round(float(sma50_series.iloc[-1]), 2)
        sma200: float | str = (
            round(float(sma200_series.iloc[-1]), 2) if sma200_series is not None else "N/A"
        )

        # Trend classification
        above_20 = price > sma20
        above_50 = price > sma50
        above_200 = price > sma200 if isinstance(sma200, float) else True

        if above_20 and above_50 and above_200:
            trend = "strong uptrend"
        elif above_50 and above_200:
            trend = "uptrend"
        elif not above_20 and not above_50 and not above_200:
            trend = "strong downtrend"
        elif not above_50 and not above_200:
            trend = "downtrend"
        else:
            trend = "sideways"

        # Golden/Death cross check
        cross = "none"
        if isinstance(sma200, float) and sma200_series is not None:
            sma50_prev = round(float(sma50_series.iloc[-5]), 2)
            sma200_prev = round(float(sma200_series.iloc[-5]), 2)
            if sma50 > sma200 and sma50_prev <= sma200_prev:
                cross = "golden cross (bullish)"
            elif sma50 < sma200 and sma50_prev >= sma200_prev:
                cross = "death cross (bearish)"

        return {
            "symbol": symbol,
            "current_price": price,
            "sma_20": sma20,
            "sma_50": sma50,
            "sma_200": sma200,
            "trend": trend,
            "ma_cross": cross,
        }
    except Exception as e:
        return {"error": f"Error calculating moving averages for {symbol}: {e}"}


@tool
def detect_trend(symbol: str) -> dict:
    """Detect the current price trend using SMA slopes, higher-highs/lows analysis. Returns direction and strength.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = _get_history(symbol)
        close = _col(df, "Close")
        price = float(close.iloc[-1])

        # SMA slope (20-day)
        sma20_series = _as_series(close.rolling(20).mean(), "sma20")
        slope_20 = (float(sma20_series.iloc[-1]) - float(sma20_series.iloc[-10])) / 10

        # SMA slope (50-day)
        sma50_series = _as_series(close.rolling(50).mean(), "sma50")
        slope_50 = (float(sma50_series.iloc[-1]) - float(sma50_series.iloc[-10])) / 10

        # Higher highs / lower lows (last 60 days, split into 3 segments)
        recent = close.tail(60)
        seg_len = len(recent) // 3
        seg1_high = float(recent.iloc[:seg_len].max())
        seg2_high = float(recent.iloc[seg_len : 2 * seg_len].max())
        seg3_high = float(recent.iloc[2 * seg_len :].max())
        seg1_low = float(recent.iloc[:seg_len].min())
        seg2_low = float(recent.iloc[seg_len : 2 * seg_len].min())
        seg3_low = float(recent.iloc[2 * seg_len :].min())

        higher_highs = seg3_high > seg2_high > seg1_high
        lower_lows = seg3_low < seg2_low < seg1_low

        if slope_20 > 0 and slope_50 > 0 and higher_highs:
            direction = "uptrend"
            strength = "strong"
        elif slope_20 > 0 and slope_50 > 0:
            direction = "uptrend"
            strength = "moderate"
        elif slope_20 < 0 and slope_50 < 0 and lower_lows:
            direction = "downtrend"
            strength = "strong"
        elif slope_20 < 0 and slope_50 < 0:
            direction = "downtrend"
            strength = "moderate"
        else:
            direction = "sideways"
            strength = "weak"

        # 52-week range position
        high_52w = float(close.max())
        low_52w = float(close.min())
        range_pct = (
            round((price - low_52w) / (high_52w - low_52w) * 100, 1)
            if high_52w != low_52w
            else 50.0
        )

        return {
            "symbol": symbol,
            "trend": direction,
            "strength": strength,
            "sma20_slope": round(slope_20, 4),
            "sma50_slope": round(slope_50, 4),
            "higher_highs": higher_highs,
            "lower_lows": lower_lows,
            "52w_range_position": f"{range_pct}%",
            "52w_high": round(high_52w, 2),
            "52w_low": round(low_52w, 2),
        }
    except Exception as e:
        return {"error": f"Error detecting trend for {symbol}: {e}"}


@tool
def detect_support_resistance(symbol: str) -> dict:
    """Detect key support and resistance levels from recent price action using pivot highs/lows.

    Args:
        symbol (str): Stock ticker symbol.
    """
    try:
        df = _get_history(symbol)
        close = _col(df, "Close")
        high_series = _col(df, "High")
        low_series = _col(df, "Low")
        price = round(float(close.iloc[-1]), 2)

        # Find local maxima and minima using a 5-day window
        resistance_levels: list[float] = []
        support_levels: list[float] = []

        highs = high_series.to_list()
        lows = low_series.to_list()

        for i in range(5, len(highs) - 5):
            window_h = highs[i - 5 : i + 6]
            window_l = lows[i - 5 : i + 6]
            if highs[i] == max(window_h):
                resistance_levels.append(round(float(highs[i]), 2))
            if lows[i] == min(window_l):
                support_levels.append(round(float(lows[i]), 2))

        # Cluster nearby levels (within 2%)
        def cluster(levels: list[float]) -> list[float]:
            if not levels:
                return []
            sorted_levels = sorted(set(levels))
            clustered = [sorted_levels[0]]
            for lvl in sorted_levels[1:]:
                if abs(lvl - clustered[-1]) / clustered[-1] > 0.02:
                    clustered.append(lvl)
                else:
                    clustered[-1] = round((clustered[-1] + lvl) / 2, 2)
            return clustered

        resistance = (
            [r for r in cluster(resistance_levels) if r > price][-3:] if resistance_levels else []
        )
        support = [s for s in cluster(support_levels) if s < price][:3] if support_levels else []

        nearest_support: float | str = max(support) if support else "N/A"
        nearest_resistance: float | str = min(resistance) if resistance else "N/A"

        return {
            "symbol": symbol,
            "current_price": price,
            "support_levels": support,
            "resistance_levels": resistance,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }
    except Exception as e:
        return {"error": f"Error detecting S/R for {symbol}: {e}"}


# Export
TECHNICAL_ALL_TOOLS = [
    get_price_history,
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    detect_trend,
    detect_support_resistance,
]
