
from datetime import datetime, timezone

import pandas as pd

from app.agents.technical.config import INDICATOR_CONFIG
from app.agents.technical.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
)
from app.agents.technical.trend import (
    detect_trend,
    detect_ema_crossover,
)
from app.agents.technical.analyzer import (
    analyze_momentum,
    analyze_volume,
)
from app.agents.technical.scorer import calculate_technical_score
from app.agents.technical.data_validation import (
    validate_technical_candles,
)


def build_technical_report(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
) -> dict:

    candles = validate_technical_candles(candles)

    minimum_candles = max(
        INDICATOR_CONFIG.minimum_candles,
        INDICATOR_CONFIG.slow_ema + 1,
        INDICATOR_CONFIG.macd_slow + INDICATOR_CONFIG.macd_signal,
        INDICATOR_CONFIG.volume_average_period + 1,
    )

    if len(candles) < minimum_candles:
        return {
            "status": "insufficient_data",
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_available": len(candles),
            "required_candles": minimum_candles,
            "score": None,
        }

    config = INDICATOR_CONFIG

    ema_fast = calculate_ema(candles, config.fast_ema)
    ema_slow = calculate_ema(candles, config.slow_ema)

    rsi = calculate_rsi(candles, config.rsi_period)

    macd = calculate_macd(
        candles,
        fast_period=config.macd_fast,
        slow_period=config.macd_slow,
        signal_period=config.macd_signal,
    )

    trend = detect_trend(candles)
    crossover = detect_ema_crossover(candles)

    momentum = analyze_momentum(candles)
    volume = analyze_volume(candles)

    technical_score = calculate_technical_score(
        trend,
        crossover,
        momentum,
        volume,
    )

    latest = candles.iloc[-1]

    return {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "latest_candle_timestamp": latest["timestamp"].isoformat(),
        "candles_available": len(candles),
        "configuration": {
            "fast_ema": config.fast_ema,
            "slow_ema": config.slow_ema,
            "rsi_period": config.rsi_period,
            "macd_fast": config.macd_fast,
            "macd_slow": config.macd_slow,
            "macd_signal": config.macd_signal,
            "volume_average_period": config.volume_average_period,
            "volume_confirmation_multiplier": (
                config.volume_confirmation_multiplier
            ),
        },
        "price": {
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
        },
        "indicators": {
            "ema_fast": float(ema_fast.iloc[-1]),
            "ema_slow": float(ema_slow.iloc[-1]),
            "rsi": float(rsi.iloc[-1]),
            "macd": float(macd["macd"].iloc[-1]),
            "macd_signal": float(macd["signal"].iloc[-1]),
            "macd_histogram": float(macd["histogram"].iloc[-1]),
        },
        "trend": trend,
        "crossover": crossover,
        "momentum": momentum,
        "volume_analysis": volume,
        "technical_score": technical_score,
    }
