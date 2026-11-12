
from app.agents.technical.scorer import calculate_technical_score


trend = {
    "trend": "bullish",
}

crossover = {
    "crossover": "bullish",
}

momentum = {
    "momentum": "bullish",
    "rsi": 60,
}

volume = {
    "confirmation": "bullish",
}

result = calculate_technical_score(
    trend,
    crossover,
    momentum,
    volume,
)

print("Technical score:")
print(result)

assert result["status"] == "ok"
assert result["score"] == 100
assert result["direction"] == "strong_bullish"
assert result["coverage"] == 100

print("\nAll scoring tests passed!")
