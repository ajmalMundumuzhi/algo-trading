
import pandas as pd

from app.agents.market_data.collector import fetch_market_snapshot
from app.agents.technical.config import INDICATOR_CONFIG
from app.agents.technical.report import build_technical_report


def get_required_candles() -> int:
    config = INDICATOR_CONFIG

    return max(
        config.minimum_candles,
        config.slow_ema + 1,
        config.macd_slow + config.macd_signal,
        config.volume_average_period + 1,
    )


async def run_technical_analysis(
    exchange,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
) -> dict:
    snapshot = await fetch_market_snapshot(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )

    candles = pd.DataFrame(snapshot["candles"])

    market_metadata = {
        "ticker": snapshot["ticker"],
        "candles_received": len(candles),
        "rejected_candles": snapshot["rejected_candles"],
        "incomplete_candles": snapshot["incomplete_candles"],
    }

    if candles.empty:
        return {
            "status": "insufficient_data",
            "symbol": symbol,
            "timeframe": timeframe,
            "market_data": market_metadata,
            "technical_analysis": {
                "status": "insufficient_data",
                "candles_available": 0,
                "required_candles": get_required_candles(),
                "score": None,
            },
        }

    report = build_technical_report(
        candles=candles,
        symbol=symbol,
        timeframe=timeframe,
    )

    return {
        "status": report["status"],
        "symbol": symbol,
        "timeframe": timeframe,
        "market_data": market_metadata,
        "technical_analysis": report,
    }
