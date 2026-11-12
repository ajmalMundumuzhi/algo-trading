
from datetime import datetime, timezone

import pandas as pd

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


def build_technical_report(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
) -> dict:

    required_columns = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns - set(candles.columns)

    if missing_columns:
        raise ValueError(
            f"Missing candle columns: {sorted(missing_columns)}"
        )

    if candles.empty:
        raise ValueError("Cannot analyse an empty candle dataset")

    if len(candles) < 50:
        return {
            "status": "insufficient_data",
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_available": len(candles),
            "required_candles": 50,
            "score": None,
        }

    candles = candles.copy()

    ema_20 = calculate_ema(candles, 20)
    ema_50 = calculate_ema(candles, 50)
    rsi = calculate_rsi(candles)
    macd = calculate_macd(candles)

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
        "latest_candle_timestamp": str(latest["timestamp"]),
        "price": {
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
        },
        "indicators": {
            "ema_20": float(ema_20.iloc[-1]),
            "ema_50": float(ema_50.iloc[-1]),
            "rsi_14": float(rsi.iloc[-1]),
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
