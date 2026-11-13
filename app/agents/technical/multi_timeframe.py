
import logging

import pandas as pd

from app.agents.technical.report import build_technical_report


logger = logging.getLogger(__name__)

SUPPORTED_TIMEFRAMES = ("15m", "1h", "4h", "1d")


def analyze_multiple_timeframes(
    snapshots: dict,
    symbol: str,
) -> dict:
    if not isinstance(snapshots, dict):
        raise ValueError("Snapshots must be a dictionary")

    reports = {}

    for timeframe in SUPPORTED_TIMEFRAMES:
        candles = snapshots.get(timeframe)

        if candles is None or len(candles) == 0:
            reports[timeframe] = {
                "status": "unavailable",
                "reason": "No candle data available",
            }
            continue

        try:
            dataframe = pd.DataFrame(candles)

            reports[timeframe] = build_technical_report(
                candles=dataframe,
                symbol=symbol,
                timeframe=timeframe,
            )

        except Exception as error:
            logger.exception(
                "Technical analysis failed for %s on %s",
                symbol,
                timeframe,
            )

            reports[timeframe] = {
                "status": "analysis_error",
                "reason": str(error),
            }

    successful_reports = [
        report
        for report in reports.values()
        if report.get("status") == "ok"
    ]

    return {
        "symbol": symbol,
        "timeframes": reports,
        "successful_timeframes": len(successful_reports),
        "total_timeframes": len(SUPPORTED_TIMEFRAMES),
        "failed_timeframes": [
            timeframe
            for timeframe, report in reports.items()
            if report.get("status") != "ok"
        ],
    }
