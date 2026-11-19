
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.market_asset import MarketAsset
from app.agents.news_sentiment.market_context import get_market_context


def get_research_market_context(
    coingecko_id: str,
    symbol: str,
    name: str,
    timeframe: str = "1h",
) -> dict:
    db = SessionLocal()

    try:
        asset_query = select(MarketAsset).where(
            MarketAsset.coingecko_id == coingecko_id,
            MarketAsset.is_active.is_(True),
        )

        assets = db.execute(asset_query).scalars().all()

        if not assets:
            return {
                "status": "unavailable",
                "reason": "No active market asset found for CoinGecko ID",
                "coingecko_id": coingecko_id,
                "symbol": symbol,
                "asset_name": name,
                "timeframe": timeframe,
            }

        if len(assets) > 1:
            return {
                "status": "ambiguous",
                "reason": "Multiple active assets share this CoinGecko ID",
                "coingecko_id": coingecko_id,
                "symbol": symbol,
                "asset_name": name,
                "timeframe": timeframe,
            }

        asset = assets[0]

        context = get_market_context(
            db=db,
            symbol=asset.symbol,
            timeframe=timeframe,
            asset_name=asset.name,
        )

        context["coingecko_id"] = coingecko_id

        return context

    except Exception:
        return {
            "status": "error",
            "reason": "Market context lookup failed",
            "coingecko_id": coingecko_id,
            "symbol": symbol,
            "asset_name": name,
            "timeframe": timeframe,
        }

    finally:
        db.close()
