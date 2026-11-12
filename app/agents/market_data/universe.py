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

def build_trading_universe(coins: list, markets: dict) -> list:
    symbol_map = defaultdict(list)

    for coin in coins:
        symbol = coin.get("symbol", "").upper().strip()

        if symbol:
            symbol_map[symbol].append(coin)

    universe = []

    for pair, market in markets.items():
        if not market.get("spot"):
            continue

        if not market.get("active"):
            continue

        if market.get("quote") != "USDT":
            continue

        base_symbol = market.get("base", "").upper()
        if base_symbol in STABLECOIN_SYMBOLS:
            continue

        matching_coins = symbol_map.get(base_symbol, [])

        if len(matching_coins) != 1:
            continue

        coin = matching_coins[0]

        universe.append({
            "coingecko_id": coin.get("id"),
            "name": coin.get("name"),
            "symbol": base_symbol,
            "market_cap_rank": coin.get("market_cap_rank"),
            "market_cap": coin.get("market_cap"),
            "binance_pair": pair,
        })

    universe.sort(
        key=lambda item: item["market_cap_rank"] or float("inf")
    )

    return universe