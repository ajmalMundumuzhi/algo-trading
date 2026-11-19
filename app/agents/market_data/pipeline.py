
import logging

from sqlalchemy import select

from app.agents.market_data.collector import fetch_market_snapshot
from app.agents.market_data.repository import upsert_assets, upsert_candles
from app.agents.market_data.universe import build_trading_universe
from app.core.database import SessionLocal
from app.integrations.exchange.client import create_exchange_client
from app.integrations.market_data.coingecko import CoinGeckoClient
from app.models.market_asset import MarketAsset


logger = logging.getLogger(__name__)


async def run_market_data_pipeline(
    coin_limit: int = 500,
    timeframe: str = "1h",
    candle_limit: int = 100,
) -> dict:

    result = {
        "status": "running",
        "coins_retrieved": 0,
        "universe_size": 0,
        "assets_saved": 0,
        "candles_saved": 0,
        "assets_processed": 0,
        "assets_failed": 0,
        "assets_without_candles": 0,
        "candles_rejected": 0,
        "candles_incomplete": 0,
        "timeframe": timeframe,
        "errors": [],
    }

    coingecko = None
    exchange = None

    try:
        if coin_limit < 1 or candle_limit < 1:
            raise ValueError("coin_limit and candle_limit must be positive.")

        coingecko = CoinGeckoClient()
        exchange = create_exchange_client()

        logger.info("Loading CoinGecko market data")

        coins = await coingecko.get_top_coins(limit=coin_limit)
        all_coins = await coingecko.get_coin_list()

        result["coins_retrieved"] = len(coins)

        logger.info("Loading exchange markets")

        markets = await exchange.load_markets()

        if not exchange.timeframes or timeframe not in exchange.timeframes:
            raise ValueError(
                f"Timeframe {timeframe} is not supported by {exchange.id}"
            )

        tickers = await exchange.fetch_tickers()

        universe = build_trading_universe(
            coins=coins,
            markets=markets,
            tickers=tickers,
            all_coins=all_coins,
        )

        result["universe_size"] = len(universe)

        if not universe:
            result["status"] = "no_eligible_assets"
            return result

        logger.info(
            "Trading universe contains %s eligible assets",
            len(universe),
        )

        with SessionLocal() as db:
            result["assets_saved"] = upsert_assets(db, universe)

            coingecko_ids = [
                item["coingecko_id"] for item in universe
            ]

            saved_assets = db.execute(
                select(MarketAsset).where(
                    MarketAsset.coingecko_id.in_(coingecko_ids)
                )
            ).scalars().all()

            asset_id_map = {
                asset.coingecko_id: asset.id
                for asset in saved_assets
            }

        for item in universe:
            coingecko_id = item["coingecko_id"]
            pair = item["binance_pair"]
            asset_id = asset_id_map.get(coingecko_id)

            if asset_id is None:
                result["assets_failed"] += 1
                result["errors"].append({
                    "symbol": item["symbol"],
                    "error": "Saved market asset could not be retrieved",
                })
                continue

            try:
                snapshot = await fetch_market_snapshot(
                    exchange=exchange,
                    symbol=pair,
                    timeframe=timeframe,
                    limit=candle_limit,
                )

                result["candles_rejected"] += snapshot["rejected_candles"]
                result["candles_incomplete"] += snapshot["incomplete_candles"]

                candles = snapshot["candles"]

                if not candles:
                    result["assets_without_candles"] += 1
                    result["assets_processed"] += 1
                    continue

                with SessionLocal() as db:
                    saved_count = upsert_candles(
                        db=db,
                        asset_id=asset_id,
                        symbol=pair,
                        timeframe=timeframe,
                        candles=candles,
                    )

                result["candles_saved"] += saved_count
                result["assets_processed"] += 1

                logger.info(
                    "Processed %s: %s candles saved, %s rejected, %s incomplete",
                    pair,
                    saved_count,
                    snapshot["rejected_candles"],
                    snapshot["incomplete_candles"],
                )

            except Exception as exc:
                logger.exception(
                    "Market data collection failed for %s",
                    pair,
                )

                result["assets_failed"] += 1
                result["errors"].append({
                    "symbol": pair,
                    "error": str(exc),
                })

        if result["assets_failed"]:
            result["status"] = "partial"
        else:
            result["status"] = "success"

        logger.info("Market data pipeline completed: %s", result)

    except Exception as exc:
        logger.exception("Market data pipeline failed")

        result["status"] = "failed"
        result["errors"].append({
            "error": str(exc),
        })

    finally:
        if exchange is not None:
            try:
                await exchange.close()
            except Exception as exc:
                logger.exception("Failed to close exchange client")
                result["errors"].append({
                    "error": f"Exchange cleanup failed: {exc}",
                })

        if coingecko is not None:
            try:
                await coingecko.close()
            except Exception as exc:
                logger.exception("Failed to close CoinGecko client")
                result["errors"].append({
                    "error": f"CoinGecko cleanup failed: {exc}",
                })

    return result
