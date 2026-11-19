
import asyncio
import json
import logging

from pathlib import Path

from app.core.config import settings
from app.core.database import SessionLocal

from app.agents.research.candidate_filter import (
    filter_research_candidates,
)
from app.agents.research.news_collector import (
    collect_coin_news_batch,
    get_candidate_key,
)
from app.agents.research.targeted_news_collector import (
    collect_targeted_coin_news,
)
from app.agents.research.market_data_collector import (
    collect_research_market_data,
)
from app.agents.research.market_context import (
    get_research_market_context,
)
from app.agents.research.config import RESEARCH_CONFIG
from app.agents.research.data_collector import ResearchDataCollector
from app.agents.research.evaluator import evaluate_project
from app.agents.research.report import (
    build_research_report,
    print_research_report,
)
from app.agents.research.watchlist_service import (
    save_research_candidate,
)
from app.integrations.exchange.client import create_exchange_client
from app.integrations.market_data.coingecko import CoinGeckoClient

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/research")

NEWS_SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.0,
    "critical": 3.0,
}

NEWS_SENTIMENT_VALUES = {
    "positive": 1,
    "negative": -1,
    "neutral": 0,
}


def merge_news_results(
    database_result: dict | None,
    targeted_result: dict | None,
) -> dict:
    sources = [
        result
        for result in (database_result, targeted_result)
        if isinstance(result, dict)
    ]

    available_sources = [
        result
        for result in sources
        if result.get("status") == "available"
        and isinstance(result.get("data"), dict)
    ]

    if not available_sources:
        errors = [
            result.get("reason", "Unknown news collection error")
            for result in sources
            if result.get("status") == "error"
        ]

        return {
            "status": "error" if errors else "unavailable",
            "data": None,
            "reason": "; ".join(errors) if errors else (
                "No matching analyzed or targeted news articles found"
            ),
        }

    unique_articles = {}
    discovery_sources = []

    for result in available_sources:
        data = result["data"]

        discovery_source = data.get("discovery_source")

        if discovery_source:
            discovery_sources.append(discovery_source)
        else:
            discovery_sources.append("Existing database")

        for article in data.get("articles", []):
            identity = (
                str(article.get("url") or "").strip().lower()
                or str(article.get("title") or "").strip().lower()
            )

            if identity and identity not in unique_articles:
                unique_articles[identity] = article

    articles = list(unique_articles.values())

    sentiment_counts = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
    }

    severity_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    weighted_sentiment = 0.0
    maximum_weight = 0.0

    for article in articles:
        sentiment = str(
            article.get("sentiment") or "neutral"
        ).lower()

        severity = str(
            article.get("severity") or "low"
        ).lower()

        if sentiment not in NEWS_SENTIMENT_VALUES:
            continue

        weight = NEWS_SEVERITY_WEIGHTS.get(
            severity,
            1.0,
        )

        sentiment_counts[sentiment] += 1

        if severity in severity_counts:
            severity_counts[severity] += 1

        weighted_sentiment += (
            NEWS_SENTIMENT_VALUES[sentiment] * weight
        )

        maximum_weight += weight

    valid_count = sum(sentiment_counts.values())

    if valid_count == 0 or maximum_weight == 0:
        return {
            "status": "unavailable",
            "data": None,
            "reason": "No valid news sentiment evidence available",
        }

    score = round(
        50 + (
            50 * weighted_sentiment / maximum_weight
        ),
        2,
    )

    return {
        "status": "available",
        "data": {
            "period_days": 7,
            "article_count": valid_count,
            "sentiment_counts": sentiment_counts,
            "severity_counts": severity_counts,
            "score": score,
            "scoring_method": (
                "Severity-weighted sentiment heuristic: "
                "positive=+1, neutral=0, negative=-1"
            ),
            "discovery_sources": sorted(set(discovery_sources)),
            "articles": articles[:20],
            "evidence_note": (
                "Combined from returned article evidence. "
                "Article evidence is limited to the first 20 "
                "records per source."
            ),
        },
    }


def sync_research_watchlist(report: dict) -> None:
    db = SessionLocal()

    try:
        for project in report.get("projects", []):
            coingecko_id = project.get("coingecko_id")

            if not coingecko_id:
                continue

            candidate = save_research_candidate(
                db,
                coingecko_id=coingecko_id,
                name=project.get("name") or "Unknown",
                symbol=project.get("symbol") or "UNKNOWN",
                market_cap_rank=project.get("market_cap_rank"),
                research_score=project.get("score"),
                coverage=project.get("coverage"),
            )

            project["watchlist_status"] = candidate.decision.value

        logger.info(
            "Research watchlist synchronized: %s projects",
            len(report.get("projects", [])),
        )

    finally:
        db.close()


async def run_research_pipeline(max_candidates: int = 5) -> dict:
    coingecko = CoinGeckoClient()
    exchange = None

    github_token = (
        settings.github_token.get_secret_value()
        if settings.github_token
        else None
    )

    research_collector = ResearchDataCollector(
        github_token=github_token
    )

    results = []

    try:
        logger.info("Starting small-cap research pipeline")

        candidates = await coingecko.get_ranked_candidates(
            start_rank=RESEARCH_CONFIG.min_market_cap_rank,
            end_rank=RESEARCH_CONFIG.max_market_cap_rank,
        )

        logger.info(
            "Retrieved %s candidates from CoinGecko",
            len(candidates),
        )

        screening = filter_research_candidates(candidates)

        eligible_candidates = screening["eligible"]
        rejected_candidates = screening["rejected"]

        logger.info(
            "Candidate screening: received=%s eligible=%s rejected=%s",
            screening["total_received"],
            screening["total_eligible"],
            screening["total_rejected"],
        )

        for rejected in rejected_candidates:
            logger.info(
                "Excluded candidate: %s (%s) - %s",
                rejected["name"],
                rejected["symbol"],
                rejected["reason"],
            )

        candidates = eligible_candidates[:max_candidates]

        logger.info(
            "Selected %s candidates for research",
            len(candidates),
        )

        if not candidates:
            logger.warning(
                "No eligible candidates found after screening"
            )

        market_collection_results = {}

        if candidates:
            try:
                logger.info(
                    "Starting Research candidate market-data collection"
                )

                exchange = create_exchange_client()

                all_coins = await coingecko.get_coin_list()

                market_collection = await collect_research_market_data(
                    candidates=candidates,
                    exchange=exchange,
                    all_coins=all_coins,
                    timeframe="1h",
                    candle_limit=100,
                )

                market_collection_results = {
                    item["coingecko_id"]: item
                    for item in market_collection.get("results", [])
                    if item.get("coingecko_id")
                }

                for item in market_collection.get("results", []):
                    logger.info(
                        "Research market-data candidate: name=%s symbol=%s "
                        "status=%s pair=%s reason=%s quote_volume=%s",
                        item.get("name"),
                        item.get("symbol"),
                        item.get("status"),
                        item.get("binance_pair"),
                        item.get("reason"),
                        item.get("quote_volume"),
                    )

                logger.info(
                    "Research market-data collection completed: "
                    "status=%s matched=%s saved_assets=%s "
                    "saved_candles=%s unavailable=%s failed=%s",
                    market_collection.get("status"),
                    market_collection.get("assets_matched"),
                    market_collection.get("assets_saved"),
                    market_collection.get("candles_saved"),
                    market_collection.get("assets_unavailable"),
                    market_collection.get("assets_failed"),
                )

            except Exception:
                logger.exception(
                    "Research market-data collection failed"
                )

                market_collection_results = {
                    candidate.get("id"): {
                        "status": "error",
                        "reason": "Research market-data collection failed",
                        "coingecko_id": candidate.get("id"),
                        "symbol": candidate.get("symbol"),
                        "name": candidate.get("name"),
                        "timeframe": "1h",
                    }
                    for candidate in candidates
                    if candidate.get("id")
                }

        database_news_results = {}
        targeted_news_results = {}

        try:
            database_news_results = collect_coin_news_batch(
                candidates
            )

            logger.info(
                "Database news collection completed for %s candidates",
                len(database_news_results),
            )

        except Exception:
            logger.exception(
                "Database news collection failed"
            )

        try:
            targeted_news_results = (
                await collect_targeted_coin_news(
                    candidates=candidates,
                    days=7,
                )
            )

            logger.info(
                "Targeted news collection completed for %s candidates",
                len(targeted_news_results),
            )

        except Exception:
            logger.exception(
                "Targeted news collection failed"
            )

        news_results = {}

        for candidate in candidates:
            candidate_key = get_candidate_key(candidate)

            database_result = database_news_results.get(
                candidate_key
            )

            targeted_result = targeted_news_results.get(
                candidate_key
            )

            merged_result = merge_news_results(
                database_result=database_result,
                targeted_result=targeted_result,
            )

            news_results[candidate_key] = merged_result

            logger.info(
                "Combined news result for %s: status=%s articles=%s score=%s",
                candidate.get("name", candidate_key),
                merged_result.get("status"),
                (
                    merged_result.get("data", {}).get("article_count", 0)
                    if merged_result.get("data")
                    else 0
                ),
                (
                    merged_result.get("data", {}).get("score")
                    if merged_result.get("data")
                    else None
                ),
            )

        try:
            defillama_protocols = (
                await research_collector.defillama.get_protocols()
            )

            logger.info(
                "Loaded %s DeFiLlama protocols",
                len(defillama_protocols),
            )

        except Exception:
            logger.exception("Could not load DeFiLlama protocols")
            defillama_protocols = []

        for index, candidate in enumerate(candidates, start=1):
            name = candidate.get("name") or "Unknown"
            symbol = candidate.get("symbol") or "UNKNOWN"
            coingecko_id = candidate.get("id")

            logger.info(
                "Researching candidate %s/%s: %s",
                index,
                len(candidates),
                name,
            )

            try:
                token_contract = None

                try:
                    token_contract = (
                        await coingecko.get_verified_token_contract(
                            coingecko_id
                        )
                    )

                    if token_contract:
                        logger.info(
                            "Contract found for %s on %s",
                            name,
                            token_contract["platform"],
                        )
                    else:
                        logger.info(
                            "No supported contract mapping found for %s",
                            name,
                        )

                except Exception:
                    logger.exception(
                        "CoinGecko contract lookup failed for %s",
                        name,
                    )

                research_data = (
                    await research_collector.collect_project_data(
                        candidate=candidate,
                        defillama_protocols=defillama_protocols,
                        token_contract=token_contract,
                    )
                )

                research_data.setdefault("sources", {})

                news_result = news_results.get(
                    get_candidate_key(candidate),
                    {
                        "status": "error",
                        "data": None,
                        "reason": "News result unavailable",
                    },
                )

                research_data["sources"]["news"] = news_result

                try:
                    market_context = get_research_market_context(
                        coingecko_id=coingecko_id,
                        symbol=symbol,
                        name=name,
                        timeframe="1h",
                    )

                    collection_result = (
                        market_collection_results.get(coingecko_id)
                    )

                    if collection_result:
                        market_context["collection"] = (
                            collection_result
                        )

                    research_data["sources"]["market_data"] = (
                        market_context
                    )

                    logger.info(
                        "Market context for %s: status=%s collection=%s",
                        name,
                        market_context.get("status", "unknown"),
                        (
                            collection_result.get("status", "unknown")
                            if collection_result
                            else "not_attempted"
                        ),
                    )

                except Exception:
                    logger.exception(
                        "Market context retrieval failed for %s",
                        name,
                    )

                    research_data["sources"]["market_data"] = {
                        "status": "error",
                        "reason": "Market context retrieval failed",
                        "coingecko_id": coingecko_id,
                        "symbol": symbol,
                        "asset_name": name,
                        "timeframe": "1h",
                        "collection": market_collection_results.get(
                            coingecko_id
                        ),
                    }

                evaluation = evaluate_project(research_data)

                evaluation["sources"] = research_data.get(
                    "sources",
                    {},
                )

                results.append(evaluation)

            except Exception:
                logger.exception(
                    "Research failed for %s",
                    name,
                )

                results.append({
                    "project": {
                        "name": name,
                        "symbol": symbol,
                        "coingecko_id": coingecko_id,
                        "market_cap_rank": candidate.get(
                            "market_cap_rank"
                        ),
                    },
                    "category_scores": {},
                    "score": {
                        "score": None,
                        "coverage": 0,
                        "available_categories": [],
                        "unavailable_categories": [],
                    },
                    "evidence": {},
                    "research_status": "insufficient_data",
                    "watchlist_status": "pending_review",
                    "sources": {},
                })

        report = build_research_report(results)

        sync_research_watchlist(report)

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = OUTPUT_DIR / "latest_report.json"

        with output_file.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

        print_research_report(report)

        logger.info(
            "Research report saved to %s",
            output_file,
        )

        return report

    finally:
        await research_collector.close()
        await coingecko.close()

        if exchange is not None:
            try:
                await exchange.close()
            except Exception:
                logger.exception(
                    "Could not close exchange client"
                )


async def main():
    await run_research_pipeline(max_candidates=5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    asyncio.run(main())
