
import pandas as pd


def calculate_ema(
    candles: pd.DataFrame,
    period: int,
) -> pd.Series:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    if period <= 0:
        raise ValueError("EMA period must be positive")

    return candles["close"].ewm(
        span=period,
        adjust=False,
        min_periods=period,
    ).mean()


def calculate_rsi(
    candles: pd.DataFrame,
    period: int = 14,
) -> pd.Series:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    if period <= 0:
        raise ValueError("RSI period must be positive")

    delta = candles["close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    relative_strength = average_gain / average_loss

    rsi = 100 - (100 / (1 + relative_strength))

    rsi = rsi.mask(
        (average_loss == 0) & (average_gain > 0),
        100,
    )

    rsi = rsi.mask(
        (average_loss == 0) & (average_gain == 0),
        50,
    )

    return rsi


def calculate_macd(
    candles: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    if "close" not in candles.columns:
        raise ValueError("Candles must contain a close column")

    if not 0 < fast_period < slow_period:
        raise ValueError("Fast period must be smaller than slow period")

    if signal_period <= 0:
        raise ValueError("Signal period must be positive")

    fast_ema = candles["close"].ewm(
        span=fast_period,
        adjust=False,
        min_periods=fast_period,
    ).mean()

    slow_ema = candles["close"].ewm(
        span=slow_period,
        adjust=False,
        min_periods=slow_period,
    ).mean()

    macd_line = fast_ema - slow_ema

    signal_line = macd_line.ewm(
        span=signal_period,
        adjust=False,
        min_periods=signal_period,
    ).mean()

    histogram = macd_line - signal_line

    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }, index=candles.index)
