
import pandas as pd

from app.agents.technical.indicators import calculate_ema


def detect_trend(
    candles: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
    min_separation_pct: float = 0.1,
) -> dict:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    if not 0 < fast_period < slow_period:
        raise ValueError("Fast EMA must be smaller than slow EMA")

    if min_separation_pct < 0:
        raise ValueError("Minimum separation cannot be negative")

    if len(candles) < slow_period:
        return {
            "trend": "insufficient_data",
            "ema_fast": None,
            "ema_slow": None,
            "separation_pct": None,
        }

    ema_fast = calculate_ema(candles, fast_period)
    ema_slow = calculate_ema(candles, slow_period)

    close = candles["close"].iloc[-1]
    fast = ema_fast.iloc[-1]
    slow = ema_slow.iloc[-1]

    if pd.isna(close) or pd.isna(fast) or pd.isna(slow):
        return {
            "trend": "insufficient_data",
            "ema_fast": None,
            "ema_slow": None,
            "separation_pct": None,
        }

    separation_pct = abs(fast - slow) / abs(slow) * 100

    if separation_pct < min_separation_pct:
        trend = "sideways"

    elif close > fast > slow:
        trend = "bullish"

    elif close < fast < slow:
        trend = "bearish"

    else:
        trend = "sideways"

    return {
        "trend": trend,
        "ema_fast": float(fast),
        "ema_slow": float(slow),
        "separation_pct": float(separation_pct),
    }


def detect_ema_crossover(
    candles: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
) -> dict:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    if not 0 < fast_period < slow_period:
        raise ValueError("Fast EMA must be smaller than slow EMA")

    if len(candles) < slow_period + 1:
        return {
            "crossover": "insufficient_data",
            "previous_difference": None,
            "current_difference": None,
        }

    fast_ema = calculate_ema(candles, fast_period)
    slow_ema = calculate_ema(candles, slow_period)

    previous_difference = (
        fast_ema.iloc[-2] - slow_ema.iloc[-2]
    )

    current_difference = (
        fast_ema.iloc[-1] - slow_ema.iloc[-1]
    )

    if pd.isna(previous_difference) or pd.isna(current_difference):
        crossover = "insufficient_data"

    elif previous_difference <= 0 and current_difference > 0:
        crossover = "bullish"

    elif previous_difference >= 0 and current_difference < 0:
        crossover = "bearish"

    else:
        crossover = "none"

    return {
        "crossover": crossover,
        "previous_difference": float(previous_difference),
        "current_difference": float(current_difference),
    }
