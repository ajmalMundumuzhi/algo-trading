
import pandas as pd

from app.agents.technical.indicators import (
    calculate_rsi,
    calculate_macd,
)
from app.agents.technical.config import INDICATOR_CONFIG


def analyze_momentum(
    candles: pd.DataFrame,
    rsi_period: int | None = None,
) -> dict:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    config = INDICATOR_CONFIG
    rsi_period = rsi_period or config.rsi_period

    if len(candles) < max(35, rsi_period + 1):
        return {
            "status": "insufficient_data",
            "rsi": None,
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "momentum": "insufficient_data",
        }

    rsi = calculate_rsi(candles, rsi_period)

    macd = calculate_macd(
        candles,
        fast_period=config.macd_fast,
        slow_period=config.macd_slow,
        signal_period=config.macd_signal,
    )

    latest_rsi = rsi.iloc[-1]
    latest_macd = macd["macd"].iloc[-1]
    latest_signal = macd["signal"].iloc[-1]
    latest_histogram = macd["histogram"].iloc[-1]

    values = [
        latest_rsi,
        latest_macd,
        latest_signal,
        latest_histogram,
    ]

    if any(pd.isna(value) for value in values):
        return {
            "status": "insufficient_data",
            "rsi": None,
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "momentum": "insufficient_data",
        }

    if latest_rsi > 50 and latest_macd > latest_signal:
        momentum = "bullish"
    elif latest_rsi < 50 and latest_macd < latest_signal:
        momentum = "bearish"
    else:
        momentum = "neutral"

    return {
        "status": "ok",
        "rsi": float(latest_rsi),
        "macd": float(latest_macd),
        "macd_signal": float(latest_signal),
        "macd_histogram": float(latest_histogram),
        "momentum": momentum,
    }


def analyze_volume(
    candles: pd.DataFrame,
    average_period: int | None = None,
    confirmation_multiplier: float | None = None,
) -> dict:
    if "volume" not in candles.columns or "close" not in candles.columns:
        raise ValueError("Candles must contain close and volume columns")

    config = INDICATOR_CONFIG

    average_period = average_period or config.volume_average_period
    confirmation_multiplier = (
        confirmation_multiplier
        if confirmation_multiplier is not None
        else config.volume_confirmation_multiplier
    )

    if average_period <= 0 or confirmation_multiplier <= 0:
        raise ValueError("Invalid volume analysis parameters")

    if len(candles) < average_period + 1:
        return {
            "status": "insufficient_data",
            "current_volume": None,
            "average_volume": None,
            "volume_ratio": None,
            "confirmation": "insufficient_data",
        }

    if not pd.api.types.is_numeric_dtype(candles["volume"]):
        raise ValueError("Volume must contain numeric values")

    if not pd.api.types.is_numeric_dtype(candles["close"]):
        raise ValueError("Close must contain numeric values")

    current_volume = candles["volume"].iloc[-1]
    previous_volumes = candles["volume"].iloc[-(average_period + 1):-1]

    average_volume = previous_volumes.mean()
    previous_close = candles["close"].iloc[-2]
    current_close = candles["close"].iloc[-1]

    values = [
        current_volume,
        average_volume,
        previous_close,
        current_close,
    ]

    if any(pd.isna(value) for value in values):
        return {
            "status": "insufficient_data",
            "current_volume": None,
            "average_volume": None,
            "volume_ratio": None,
            "confirmation": "insufficient_data",
        }

    if current_volume < 0 or average_volume < 0:
        raise ValueError("Volume cannot be negative")

    if average_volume == 0:
        return {
            "status": "insufficient_data",
            "current_volume": float(current_volume),
            "average_volume": float(average_volume),
            "volume_ratio": None,
            "confirmation": "insufficient_data",
        }

    volume_ratio = current_volume / average_volume

    if volume_ratio >= confirmation_multiplier:
        if current_close > previous_close:
            confirmation = "bullish"
        elif current_close < previous_close:
            confirmation = "bearish"
        else:
            confirmation = "neutral"
    else:
        confirmation = "weak"

    return {
        "status": "ok",
        "current_volume": float(current_volume),
        "average_volume": float(average_volume),
        "volume_ratio": float(volume_ratio),
        "confirmation": confirmation,
    }
