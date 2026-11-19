
from datetime import datetime, timezone


VALID_SOURCE_STATUSES = {"available", "success"}


def extract_project_risks(evidence: dict) -> list[dict]:
    risks = []
    seen = set()

    def add_risk(category: str, name: str, details: dict | None = None):
        key = (category, name)

        if key in seen:
            return

        seen.add(key)

        risks.append({
            "category": category,
            "risk": name,
            "details": details or {},
        })

    security = evidence.get("security", {})

    if isinstance(security, dict):
        for flag in security.get("critical_flags", []):
            add_risk(
                "security",
                str(flag),
                {"source": "GoPlus critical flag"},
            )

        checks = security.get("checks", {})

        if isinstance(checks, dict):
            for check_name, check_data in checks.items():
                if not isinstance(check_data, dict):
                    continue

                if check_data.get("risk_detected") is True:
                    add_risk(
                        "security",
                        check_name,
                        {
                            "value": check_data.get("value"),
                            "penalty": check_data.get("penalty"),
                        },
                    )

        tax_results = security.get("tax_results", {})

        if isinstance(tax_results, dict):
            for tax_name, tax_data in tax_results.items():
                if not isinstance(tax_data, dict):
                    continue

                penalty = tax_data.get("penalty", 0) or 0

                if penalty > 0:
                    add_risk(
                        "security",
                        tax_name,
                        {
                            "value": tax_data.get("value"),
                            "penalty": penalty,
                        },
                    )

    growth = evidence.get("project_growth", {})

    if isinstance(growth, dict):
        growth_percentage = growth.get(
            "tvl_growth_30d_percentage"
        )

        if (
            isinstance(growth_percentage, (int, float))
            and not isinstance(growth_percentage, bool)
            and growth_percentage < 0
        ):
            add_risk(
                "project_growth",
                "Negative TVL growth over 30 days",
                {
                    "tvl_growth_30d_percentage": growth_percentage,
                },
            )

    return risks


def extract_research_gaps(
    evidence: dict,
    unavailable_categories: list[str],
) -> list[dict]:
    gaps = []

    for category in unavailable_categories:
        category_evidence = evidence.get(category, {})

        reason = None

        if isinstance(category_evidence, dict):
            reason = category_evidence.get("reason")

        gaps.append({
            "category": category,
            "reason": reason or "Required research data unavailable",
        })

    return gaps


def normalize_source_status(source) -> str:
    if not isinstance(source, dict):
        return "unavailable"

    status = source.get("status", "unavailable")

    if not isinstance(status, str) or not status.strip():
        return "unavailable"

    return status.strip().lower()


def build_research_report(results: list[dict]) -> dict:
    projects = []

    for result in results:
        project = result.get("project", {})
        score_data = result.get("score", {})
        sources = result.get("sources", {})
        evidence = result.get("evidence", {})

        coverage = score_data.get("coverage", 0) or 0
        score = score_data.get("score")

        is_final = score_data.get(
            "is_final",
            coverage >= 80,
        )

        score_type = (
            "final"
            if is_final and score is not None
            else "provisional"
            if score is not None
            else "unavailable"
        )

        source_status = {
            name: normalize_source_status(source)
            for name, source in sources.items()
        }

        missing_sources = [
            name
            for name, status in source_status.items()
            if status not in VALID_SOURCE_STATUSES
        ]

        market_data = sources.get("market_data", {})

        if not isinstance(market_data, dict):
            market_data = {
                "status": "unavailable",
                "reason": "Invalid market-data response",
            }

        market_data_status = normalize_source_status(
            market_data
        )

        market_data_summary = {
            "status": market_data_status,
            "reason": market_data.get("reason"),
            "timeframe": market_data.get("timeframe"),
            "latest_candle_price": market_data.get(
                "latest_candle_price"
            ),
            "previous_candle_price": market_data.get(
                "previous_candle_price"
            ),
            "price_change_pct": market_data.get(
                "price_change_pct"
            ),
            "volume": market_data.get("volume"),
            "latest_candle_timestamp": market_data.get(
                "latest_candle_timestamp"
            ),
            "candle_age_minutes": market_data.get(
                "candle_age_minutes"
            ),
        }

        unavailable_categories = score_data.get(
            "unavailable_categories",
            [],
        )

        identified_risks = extract_project_risks(evidence)

        research_gaps = extract_research_gaps(
            evidence,
            unavailable_categories,
        )

        if score is None:
            conclusion = "Insufficient research data"
        elif not is_final:
            conclusion = (
                "Provisional research score - additional data "
                "required before final evaluation"
            )
        elif score >= 70:
            conclusion = (
                "Strong research score - requires human review"
            )
        elif score >= 50:
            conclusion = (
                "Moderate research score - requires human review"
            )
        else:
            conclusion = (
                "Weak research score - requires careful review"
            )

        projects.append({
            "name": project.get("name"),
            "symbol": project.get("symbol"),
            "coingecko_id": project.get("coingecko_id"),
            "market_cap_rank": project.get("market_cap_rank"),
            "market_cap": project.get("market_cap"),
            "current_price": project.get("current_price"),
            "total_volume": project.get("total_volume"),

            "research_status": result.get("research_status"),
            "watchlist_status": result.get(
                "watchlist_status",
                "pending_review",
            ),

            "score": score,
            "provisional_score": score_data.get(
                "provisional_score"
            ),
            "coverage_adjusted_score": score_data.get(
                "coverage_adjusted_score"
            ),
            "score_type": score_type,
            "score_reliability": score_data.get(
                "score_reliability",
                "none",
            ),
            "score_warning": score_data.get("score_warning"),
            "is_final": is_final,

            "coverage": coverage,
            "available_categories": score_data.get(
                "available_categories",
                [],
            ),
            "unavailable_categories": unavailable_categories,
            "category_scores": result.get("category_scores", {}),

            "source_status": source_status,
            "missing_sources": missing_sources,
            "market_data": market_data_summary,
            "missing_categories": unavailable_categories,
            "research_gaps": research_gaps,

            "evidence": evidence,
            "identified_risks": identified_risks,
            "research_conclusion": conclusion,
            "human_review_required": True,
        })

    projects.sort(
        key=lambda item: (
            not item["is_final"],
        )
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "small_cap_research",
        "total_projects": len(projects),
        "ready_for_review": sum(
            item["research_status"] == "ready"
            for item in projects
        ),
        "partial_research": sum(
            item["research_status"] == "partial"
            for item in projects
        ),
        "insufficient_data": sum(
            item["research_status"] == "insufficient_data"
            for item in projects
        ),
        "projects": projects,
        "disclaimer": (
            "Research output only. No investment recommendation "
            "or trade execution is performed. Human review is required. "
            "Provisional scores must not be used as final rankings or "
            "approval signals. A research score does not establish "
            "token safety."
        ),
    }


def print_research_report(report: dict) -> None:
    print("\n" + "=" * 70)
    print("SMALL-CAP RESEARCH REPORT")
    print("=" * 70)

    print(f"Generated: {report['generated_at']}")
    print(f"Total projects: {report['total_projects']}")
    print(f"Ready for review: {report['ready_for_review']}")
    print(f"Partial research: {report['partial_research']}")
    print(f"Insufficient data: {report['insufficient_data']}")

    print("\nPROJECT RESULTS")
    print("-" * 70)

    for index, project in enumerate(report["projects"], start=1):
        print(f"\n{index}. {project['name']} ({project['symbol']})")
        print(f"   CoinGecko ID: {project['coingecko_id']}")
        print(f"   Market cap rank: {project['market_cap_rank']}")
        print(f"   Research status: {project['research_status']}")
        print(f"   Watchlist status: {project['watchlist_status']}")

        print(
            f"   Score: {project['score']} "
            f"({project['score_type']})"
        )

        print(f"   Data coverage: {project['coverage']}%")
        print(f"   Score reliability: {project['score_reliability']}")
        print(f"   Final score: {project['is_final']}")

        if project["score_warning"]:
            print(f"   Score warning: {project['score_warning']}")

        print(f"   Conclusion: {project['research_conclusion']}")

        print("   Sources:")

        for source, status in project["source_status"].items():
            print(f"      {source}: {status}")

        market_data = project["market_data"]

        print(
            "   Market data details: "
            f"{market_data['status']}"
        )

        if market_data["reason"]:
            print(f"      Reason: {market_data['reason']}")

        if market_data["latest_candle_timestamp"]:
            print(
                "      Latest candle: "
                f"{market_data['latest_candle_timestamp']}"
            )

        if market_data["candle_age_minutes"] is not None:
            print(
                "      Candle age: "
                f"{market_data['candle_age_minutes']} minutes"
            )

        if project["research_gaps"]:
            print("   Research gaps:")

            for gap in project["research_gaps"]:
                print(
                    f"      {gap['category']}: {gap['reason']}"
                )

        if project["identified_risks"]:
            print("   Identified risks:")

            for risk in project["identified_risks"]:
                print(
                    f"      {risk['category']}: {risk['risk']}"
                )

        print(
            "   Human review required:",
            project["human_review_required"],
        )

    print("\n" + "=" * 70)
    print(report["disclaimer"])
    print("=" * 70)
