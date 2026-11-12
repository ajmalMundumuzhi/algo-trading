
import pandas as pd

from app.agents.technical.analyzer import (
    analyze_momentum,
    analyze_volume,
)


candles = pd.DataFrame({
    "close": [
        100 + (i * 1.5) + ((i % 5) * 0.2)
        for i in range(100)
    ],
    "volume": [
        1000 for _ in range(99)
    ] + [2500],
})

momentum = analyze_momentum(candles)
volume = analyze_volume(candles)

print("Momentum analysis:")
print(momentum)

print("\nVolume analysis:")
print(volume)

assert momentum["status"] == "ok"
assert momentum["momentum"] == "bullish"

assert volume["status"] == "ok"
assert volume["confirmation"] == "bullish"
assert volume["volume_ratio"] == 2.5

print("\nAll momentum and volume tests passed!")
