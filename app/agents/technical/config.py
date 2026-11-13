
from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_average_period: int = 20
    volume_confirmation_multiplier: float = 1.5
    minimum_ema_separation_pct: float = 0.1
    minimum_candles: int = 50
    rsi_overbought: float = 70
    rsi_oversold: float = 30


@dataclass(frozen=True)
class ScoringConfig:
    trend_weight: int = 30
    crossover_weight: int = 15
    momentum_weight: int = 30
    rsi_weight: int = 10
    volume_weight: int = 15
    bullish_threshold: float = 20
    strong_bullish_threshold: float = 60
    bearish_threshold: float = -20
    strong_bearish_threshold: float = -60


INDICATOR_CONFIG = IndicatorConfig()
SCORING_CONFIG = ScoringConfig()
