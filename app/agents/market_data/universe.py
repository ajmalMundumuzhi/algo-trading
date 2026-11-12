
from collections import defaultdict


STABLECOIN_SYMBOLS = {
    "USDT",
    "USDC",
    "USDS",
    "USDE",
    "DAI",
    "FDUSD",
    "TUSD",
    "USDP",
    "PYUSD",
    "BUSD",
    "RLUSD",
    "USD1",
    "EURC",
}

MIN_QUOTE_VOLUME_USDT = 1_000_000


def build_trading_universe(
    coins: list,
    markets: dict,
    tickers: dict,
    all_coins: list,
) -> list:
    symbol_map = defaultdict(list)
    global_symbol_counts = defaultdict(int)

    for coin in coins:
        symbol = coin.get("symbol", "").upper().strip()

        if symbol:
            symbol_map[symbol].append(coin)

    for coin in all_coins:
        symbol = coin.get("symbol", "").upper().strip()

        if symbol:
            global_symbol_counts[symbol] += 1

    universe = []

    for pair, market in markets.items():
        if not market.get("spot"):
            continue

        if not market.get("active"):
            continue

        if market.get("quote") != "USDT":
            continue

        base_symbol = market.get("base", "").upper().strip()

        if base_symbol in STABLECOIN_SYMBOLS:
            continue

        if global_symbol_counts.get(base_symbol, 0) != 1:
            continue

        matching_coins = symbol_map.get(base_symbol, [])

        if len(matching_coins) != 1:
            continue

        coin = matching_coins[0]

        if not coin.get("id") or not coin.get("name"):
            continue

        ticker = tickers.get(pair)

        if not ticker:
            continue

        quote_volume = ticker.get("quoteVolume")

        if quote_volume is None or quote_volume < MIN_QUOTE_VOLUME_USDT:
            continue

        universe.append({
            "coingecko_id": coin["id"],
            "name": coin["name"],
            "symbol": base_symbol,
            "market_cap_rank": coin.get("market_cap_rank"),
            "market_cap": coin.get("market_cap"),
            "binance_pair": pair,
            "quote_volume_24h": quote_volume,
        })

    universe.sort(
        key=lambda item: (
            item["market_cap_rank"]
            if item["market_cap_rank"] is not None
            else float("inf")
        )
    )

    return universe
