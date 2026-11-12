
def calculate_technical_score(
    trend: dict,
    crossover: dict,
    momentum: dict,
    volume: dict,
) -> dict:
    score = 0.0
    available_weight = 0.0
    breakdown = {}

    weights = {
        "trend": 30,
        "crossover": 15,
        "momentum": 30,
        "rsi": 10,
        "volume": 15,
    }

    def add_component(name: str, signal: str, weight: int):
        nonlocal score, available_weight

        values = {
            "bullish": 1,
            "bearish": -1,
            "neutral": 0,
            "none": 0,
            "weak": 0,
        }

        if signal not in values:
            return

        contribution = values[signal] * weight

        score += contribution
        available_weight += weight

        breakdown[name] = {
            "signal": signal,
            "weight": weight,
            "contribution": contribution,
        }

    add_component(
        "trend",
        trend.get("trend"),
        weights["trend"],
    )

    add_component(
        "crossover",
        crossover.get("crossover"),
        weights["crossover"],
    )

    add_component(
        "momentum",
        momentum.get("momentum"),
        weights["momentum"],
    )

    rsi = momentum.get("rsi")

    if rsi is not None:
        if rsi >= 70:
            rsi_signal = "bearish"
        elif rsi <= 30:
            rsi_signal = "bullish"
        elif rsi > 55:
            rsi_signal = "bullish"
        elif rsi < 45:
            rsi_signal = "bearish"
        else:
            rsi_signal = "neutral"

        add_component(
            "rsi",
            rsi_signal,
            weights["rsi"],
        )

    add_component(
        "volume",
        volume.get("confirmation"),
        weights["volume"],
    )

    if available_weight == 0:
        return {
            "status": "insufficient_data",
            "score": None,
            "direction": "unavailable",
            "coverage": 0,
            "breakdown": breakdown,
        }

    final_score = round(
        (score / available_weight) * 100,
        2,
    )

    if final_score >= 60:
        direction = "strong_bullish"
    elif final_score >= 20:
        direction = "bullish"
    elif final_score <= -60:
        direction = "strong_bearish"
    elif final_score <= -20:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "status": "ok",
        "score": final_score,
        "direction": direction,
        "coverage": round(available_weight, 2),
        "breakdown": breakdown,
    }
