
import pandas as pd

from app.agents.technical.trend import (
    detect_trend,
    detect_ema_crossover,
)


candles = pd.DataFrame({
    "close": [
        100 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ]
})

trend = detect_trend(candles)
crossover = detect_ema_crossover(candles)

print("Trend analysis:")
print(trend)

print("\nEMA crossover:")
print(crossover)

assert trend["trend"] == "bullish"
assert crossover["crossover"] in {
    "none",
    "bullish",
    "bearish",
}

print("\nAll trend tests passed!")
