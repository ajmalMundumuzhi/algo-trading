
import logging

from sqlalchemy import select

from app.agents.market_data.collector import fetch_market_snapshot
from app.agents.market_data.repository import (
    upsert_assets,
    upsert_candles,
)
from app.core.database import SessionLocal
from app.models.market_asset import MarketAsset


logger = logging.getLogger(__name__)

MIN_QUOTE_VOLUME_USDT = 1_000_000

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


def _normalize_symbol(symbol) -> str:
    if not isinstance(symbol, str):
        return ""

    return symbol.upper().strip()


def _get_quote_volume(ticker: dict) -> float | None:
    quote_volume = ticker.get("quoteVolume")

    if quote_volume is None:
        info = ticker.get("info") or {}

        quote_volume = info.get("quoteVolume")

    if quote_volume is None:
        return None

    try:
        value = float(quote_volume)
    except (TypeError, ValueError):
        return None

    if value < 0:
        return None

    return value


def _get_candidate_pair(
    candidate: dict,
    markets: dict,
    tickers: dict,
    global_symbol_counts: dict,
    candidate_symbol_counts: dict,
) -> tuple[str | None, str | None, float | None]:

    symbol = _normalize_symbol(candidate.get("symbol"))

    if not symbol:
        return None, "Candidate has no valid symbol", None

    if symbol in STABLECOIN_SYMBOLS:
        return None, "Stablecoin is not eligible", None

    if global_symbol_counts.get(symbol, 0) != 1:
        return None, "CoinGecko symbol is ambiguous", None

    if candidate_symbol_counts.get(symbol, 0) != 1:
        return (
            None,
            "Multiple research candidates share this symbol",
            None,
        )

    diagnostics = {
        "base_matches": 0,
        "inactive_markets": 0,
        "non_spot_markets": 0,
        "non_usdt_markets": 0,
        "missing_tickers": 0,
        "missing_quote_volume": 0,
        "low_liquidity": 0,
    }

    matching_pairs = []

    for pair, market in markets.items():
        market_base = _normalize_symbol(market.get("base"))

        if market_base != symbol:
            continue

        diagnostics["base_matches"] += 1

        market_type = market.get("type")
        is_spot = market.get("spot")

        if is_spot is not True and market_type != "spot":
            diagnostics["non_spot_markets"] += 1
            continue

        if market.get("active") is not True:
            diagnostics["inactive_markets"] += 1
            continue

        if _normalize_symbol(market.get("quote")) != "USDT":
            diagnostics["non_usdt_markets"] += 1
            continue

        ticker = tickers.get(pair)

        if not ticker:
            diagnostics["missing_tickers"] += 1
            continue

        quote_volume = _get_quote_volume(ticker)

        if quote_volume is None:
            diagnostics["missing_quote_volume"] += 1
            continue

        if quote_volume < MIN_QUOTE_VOLUME_USDT:
            diagnostics["low_liquidity"] += 1
            continue

        matching_pairs.append((pair, quote_volume))

    if not matching_pairs:
        logger.info(
            "Binance pair diagnostics for %s (%s): %s",
            candidate.get("name"),
            symbol,
            diagnostics,
        )

        if diagnostics["base_matches"] == 0:
            reason = "No Binance market found with this exact base symbol"

        elif diagnostics["non_spot_markets"] == diagnostics["base_matches"]:
            reason = "Matching Binance markets are not spot markets"

        elif (
            diagnostics["inactive_markets"] > 0
            and diagnostics["inactive_markets"]
            + diagnostics["non_spot_markets"]
            == diagnostics["base_matches"]
        ):
            reason = "Matching Binance spot markets are inactive"

        elif diagnostics["non_usdt_markets"] > 0:
            reason = "Matching market exists but has no eligible USDT pair"

        elif diagnostics["missing_tickers"] > 0:
            reason = "Binance ticker data is unavailable for matching pair"

        elif diagnostics["missing_quote_volume"] > 0:
            reason = "Binance ticker does not provide usable quote volume"

        elif diagnostics["low_liquidity"] > 0:
            reason = (
                "Binance USDT spot pair does not meet liquidity requirements "
                f"(minimum ${MIN_QUOTE_VOLUME_USDT:,.0f} 24h quote volume)"
            )

        else:
            reason = "No eligible Binance USDT spot pair found"

        return None, reason, None

    if len(matching_pairs) > 1:
        logger.warning(
            "Multiple eligible Binance pairs found for %s (%s): %s",
            candidate.get("name"),
            symbol,
            matching_pairs,
        )

        return (
            None,
            "Multiple eligible Binance USDT spot pairs found",
            None,
        )

    pair, quote_volume = matching_pairs[0]

    return pair, None, quote_volume


async def collect_research_market_data(
    candidates: list[dict],
    exchange,
    all_coins: list[dict],
    timeframe: str = "1h",
    candle_limit: int = 100,
) -> dict:

    result = {
        "status": "success",
        "candidates_received": len(candidates),
        "assets_matched": 0,
        "assets_saved": 0,
        "candles_saved": 0,
        "assets_failed": 0,
        "assets_unavailable": 0,
        "results": [],
    }

    if not candidates:
        return result

    if candle_limit < 1:
        raise ValueError("candle_limit must be positive")

    if not timeframe:
        raise ValueError("timeframe is required")

    try:
        markets = await exchange.load_markets()
        tickers = await exchange.fetch_tickers()

    except Exception:
        logger.exception(
            "Failed to load Binance markets or tickers for research"
        )

        result["status"] = "failed"
        result["assets_failed"] = len(candidates)

        result["results"] = [
            {
                "coingecko_id": candidate.get("id"),
                "name": candidate.get("name"),
                "symbol": _normalize_symbol(candidate.get("symbol")),
                "status": "error",
                "reason": "Failed to load exchange markets or tickers",
            }
            for candidate in candidates
        ]

        return result

    global_symbol_counts = {}

    for coin in all_coins:
        symbol = _normalize_symbol(coin.get("symbol"))

        if symbol:
            global_symbol_counts[symbol] = (
                global_symbol_counts.get(symbol, 0) + 1
            )

    candidate_symbol_counts = {}

    for candidate in candidates:
        symbol = _normalize_symbol(candidate.get("symbol"))

        if symbol:
            candidate_symbol_counts[symbol] = (
                candidate_symbol_counts.get(symbol, 0) + 1
            )

    for candidate in candidates:
        coingecko_id = candidate.get("id")
        name = candidate.get("name")
        symbol = _normalize_symbol(candidate.get("symbol"))

        candidate_result = {
            "coingecko_id": coingecko_id,
            "name": name,
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "unavailable",
            "reason": None,
            "binance_pair": None,
            "quote_volume_24h": None,
            "candles_saved": 0,
            "rejected_candles": 0,
            "incomplete_candles": 0,
        }

        if not coingecko_id or not name:
            candidate_result["status"] = "error"
            candidate_result["reason"] = (
                "Missing CoinGecko ID or asset name"
            )
            result["assets_failed"] += 1
            result["results"].append(candidate_result)
            continue

        pair, reason, quote_volume = _get_candidate_pair(
            candidate=candidate,
            markets=markets,
            tickers=tickers,
            global_symbol_counts=global_symbol_counts,
            candidate_symbol_counts=candidate_symbol_counts,
        )

        if pair is None:
            candidate_result["reason"] = reason
            result["assets_unavailable"] += 1
            result["results"].append(candidate_result)
            continue

        candidate_result["binance_pair"] = pair
        candidate_result["quote_volume_24h"] = quote_volume

        try:
            with SessionLocal() as db:
                pair_owner = db.execute(
                    select(MarketAsset).where(
                        MarketAsset.binance_pair == pair,
                        MarketAsset.coingecko_id != coingecko_id,
                    )
                ).scalar_one_or_none()

                if pair_owner is not None:
                    candidate_result["reason"] = (
                        "Binance pair is already assigned to another "
                        "CoinGecko asset"
                    )
                    result["assets_unavailable"] += 1
                    result["results"].append(candidate_result)
                    continue

                asset_data = {
                    "coingecko_id": coingecko_id,
                    "name": name,
                    "symbol": symbol,
                    "binance_pair": pair,
                    "market_cap_rank": candidate.get(
                        "market_cap_rank"
                    ),
                    "market_cap": candidate.get("market_cap"),
                }

                saved_count = upsert_assets(
                    db=db,
                    assets=[asset_data],
                )

                asset = db.execute(
                    select(MarketAsset).where(
                        MarketAsset.coingecko_id == coingecko_id
                    )
                ).scalar_one_or_none()

                if asset is None:
                    raise RuntimeError(
                        "Market asset could not be retrieved after saving"
                    )

                asset_id = asset.id

            result["assets_matched"] += 1
            result["assets_saved"] += saved_count

            snapshot = await fetch_market_snapshot(
                exchange=exchange,
                symbol=pair,
                timeframe=timeframe,
                limit=candle_limit,
            )

            candidate_result["rejected_candles"] = (
                snapshot["rejected_candles"]
            )

            candidate_result["incomplete_candles"] = (
                snapshot["incomplete_candles"]
            )

            candles = snapshot["candles"]

            if not candles:
                candidate_result["status"] = "unavailable"
                candidate_result["reason"] = (
                    "No valid closed candles returned by exchange"
                )
                result["assets_unavailable"] += 1
                result["results"].append(candidate_result)
                continue

            with SessionLocal() as db:
                saved_candles = upsert_candles(
                    db=db,
                    asset_id=asset_id,
                    symbol=pair,
                    timeframe=timeframe,
                    candles=candles,
                )

            candidate_result["status"] = "available"
            candidate_result["candles_saved"] = saved_candles

            result["candles_saved"] += saved_candles

            logger.info(
                "Research market data collected for %s: %s candles",
                name,
                saved_candles,
            )

        except Exception as exc:
            logger.exception(
                "Research market data collection failed for %s",
                name,
            )

            candidate_result["status"] = "error"
            candidate_result["reason"] = str(exc)

            result["assets_failed"] += 1

        result["results"].append(candidate_result)

    if result["assets_failed"] or result["assets_unavailable"]:
        result["status"] = "partial"

    return result
