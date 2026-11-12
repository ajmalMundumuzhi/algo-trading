
import pandas as pd

from app.agents.technical.report import build_technical_report


candles = pd.DataFrame({
    "timestamp": pd.date_range(
        start="2026-01-01",
        periods=100,
        freq="1h",
        tz="UTC",
    ),
    "open": [
        100 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ],
    "high": [
        102 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ],
    "low": [
        99 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ],
    "close": [
        101 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ],
    "volume": [
        1000 for _ in range(99)
    ] + [2500],
})

report = build_technical_report(
    candles=candles,
    symbol="BTC/USDT",
    timeframe="1h",
)

print("Technical report:")
print(report)

assert report["status"] == "ok"
assert report["symbol"] == "BTC/USDT"
assert report["timeframe"] == "1h"

assert "indicators" in report
assert "trend" in report
assert "momentum" in report
assert "volume_analysis" in report
assert "technical_score" in report

assert -100 <= report["technical_score"]["score"] <= 100

print("\nAll technical report tests passed!")
