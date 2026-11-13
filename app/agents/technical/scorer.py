
from app.agents.technical.config import SCORING_CONFIG, INDICATOR_CONFIG


def calculate_technical_score(
    trend: dict,
    crossover: dict,
    momentum: dict,
    volume: dict,
) -> dict:
    config = SCORING_CONFIG

    score = 0.0
    available_weight = 0.0
    breakdown = {}

    weights = {
        "trend": config.trend_weight,
        "crossover": config.crossover_weight,
        "momentum": config.momentum_weight,
        "rsi": config.rsi_weight,
        "volume": config.volume_weight,
    }

    if any(weight < 0 for weight in weights.values()):
        raise ValueError("Scoring weights cannot be negative")

    if sum(weights.values()) <= 0:
        raise ValueError("At least one scoring weight must be positive")

    def add_component(name: str, signal: str, weight: int):
        nonlocal score, available_weight

        values = {
            "bullish": 1,
            "bearish": -1,
            "neutral": 0,
            "none": 0,
            "weak": 0,
        }

        if signal not in values or weight == 0:
            return

        contribution = values[signal] * weight

        score += contribution
        available_weight += weight

        breakdown[name] = {
            "signal": signal,
            "weight": weight,
            "contribution": contribution,
        }

    add_component("trend", trend.get("trend"), weights["trend"])
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
        if not 0 <= rsi <= 100:
            raise ValueError("RSI must be between 0 and 100")

        if rsi >= INDICATOR_CONFIG.rsi_overbought:
            rsi_signal = "bearish"
        elif rsi <= INDICATOR_CONFIG.rsi_oversold:
            rsi_signal = "bullish"
        elif rsi > 55:
            rsi_signal = "bullish"
        elif rsi < 45:
            rsi_signal = "bearish"
        else:
            rsi_signal = "neutral"

        add_component("rsi", rsi_signal, weights["rsi"])

    add_component(
        "volume",
        volume.get("confirmation"),
        weights["volume"],
    )

    total_weight = sum(weights.values())

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

    if final_score >= config.strong_bullish_threshold:
        direction = "strong_bullish"
    elif final_score >= config.bullish_threshold:
        direction = "bullish"
    elif final_score <= config.strong_bearish_threshold:
        direction = "strong_bearish"
    elif final_score <= config.bearish_threshold:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "status": "ok",
        "score": final_score,
        "direction": direction,
        "coverage": round(
            (available_weight / total_weight) * 100,
            2,
        ),
        "available_weight": available_weight,
        "total_weight": total_weight,
        "breakdown": breakdown,
    }
