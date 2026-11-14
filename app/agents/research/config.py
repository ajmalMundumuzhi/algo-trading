
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchConfig:
    min_market_cap_rank: int = 101
    max_market_cap_rank: int = 500
    min_quote_volume_usdt: float = 1_000_000
    quote_currency: str = "USDT"
    market_type: str = "spot"
    excluded_symbols: frozenset[str] = frozenset({
        "USDT", "USDC", "USDS", "USDE", "DAI",
        "FDUSD", "TUSD", "USDP", "PYUSD", "BUSD",
        "RLUSD", "USD1", "EURC",
    })


RESEARCH_CONFIG = ResearchConfig()
