
import asyncio
import json
import logging

from pathlib import Path

from app.core.config import settings
from app.agents.research.candidate_filter import (
    filter_research_candidates,
)
from app.agents.research.news_collector import (
    collect_coin_news_batch,
    get_candidate_key,
)
from app.integrations.market_data.coingecko import CoinGeckoClient
from app.agents.research.config import RESEARCH_CONFIG
from app.agents.research.data_collector import ResearchDataCollector
from app.agents.research.evaluator import evaluate_project
from app.agents.research.report import (
    build_research_report,
    print_research_report,
)

from app.core.database import SessionLocal
from app.agents.research.watchlist_service import (
    save_research_candidate,
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/research")

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

    github_token = (
        settings.github_token.get_secret_value()
        if settings.github_token
        else None
    )

    collector = ResearchDataCollector(
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

        try:
            news_results = collect_coin_news_batch(candidates)

            logger.info(
                "Batch news collection completed for %s candidates",
                len(news_results),
            )

        except Exception:
            logger.exception("Batch news collection failed")
            news_results = {}

        try:
            defillama_protocols = await collector.defillama.get_protocols()

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

                research_data = await collector.collect_project_data(
                    candidate=candidate,
                    defillama_protocols=defillama_protocols,
                    token_contract=token_contract,
                )

                news_result = news_results.get(
                    get_candidate_key(candidate),
                    {
                        "status": "error",
                        "data": None,
                        "reason": "News result unavailable",
                    },
                )

                research_data.setdefault("sources", {})
                research_data["sources"]["news"] = news_result

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
        await collector.close()
        await coingecko.close()


async def main():
    await run_research_pipeline(max_candidates=5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    asyncio.run(main())
