
import pandas as pd

from app.agents.technical.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
)


data = {
    "close": [
        100, 102, 101, 104, 106, 105, 108, 110, 109, 112,
        114, 113, 116, 118, 117, 120, 122, 121, 124, 126,
        125, 128, 130, 129, 132, 134, 133, 136, 138, 137,
        140, 142, 141, 144, 146, 145, 148, 150, 149, 152,
        154, 153, 156, 158, 157, 160, 162, 161, 164, 166,
        165, 168, 170, 169, 172, 174, 173, 176, 178, 177,
        180, 182, 181, 184, 186, 185, 188, 190, 189, 192,
        194, 193, 196, 198, 197, 200, 202, 201, 204, 206,
        205, 208, 210, 209, 212, 214, 213, 216, 218, 217,
        220, 222, 221, 224, 226, 225, 228, 230, 229, 232,
    ]
}

candles = pd.DataFrame(data)

ema_20 = calculate_ema(candles, 20)
ema_50 = calculate_ema(candles, 50)
rsi = calculate_rsi(candles)
macd = calculate_macd(candles)

print("Total candles:", len(candles))

print("\nLatest indicator values:")
print("EMA 20:", ema_20.iloc[-1])
print("EMA 50:", ema_50.iloc[-1])
print("RSI:", rsi.iloc[-1])
print("MACD:", macd["macd"].iloc[-1])
print("MACD Signal:", macd["signal"].iloc[-1])
print("MACD Histogram:", macd["histogram"].iloc[-1])

assert not pd.isna(ema_20.iloc[-1])
assert not pd.isna(ema_50.iloc[-1])
assert not pd.isna(rsi.iloc[-1])
assert not pd.isna(macd["macd"].iloc[-1])
assert not pd.isna(macd["signal"].iloc[-1])
assert not pd.isna(macd["histogram"].iloc[-1])

assert 0 <= rsi.iloc[-1] <= 100

print("\nAll indicator tests passed!")
