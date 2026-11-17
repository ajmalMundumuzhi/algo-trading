
import math

from app.agents.research.scorer import calculate_research_score


def _to_float(value) -> float | None:
    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _parse_flag(value) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in {"1", "true", "yes"}:
        return True

    if normalized in {"0", "false", "no"}:
        return False

    return None


def calculate_market_fundamentals(
    project: dict,
) -> tuple[float | None, dict]:
    rank = project.get("market_cap_rank")
    market_cap = _to_float(project.get("market_cap"))
    volume = _to_float(project.get("total_volume"))

    try:
        rank = int(rank)
    except (TypeError, ValueError):
        rank = None

    if rank is None or market_cap is None or volume is None:
        return None, {"reason": "Missing or invalid market data"}

    if rank < 1 or market_cap <= 0 or volume < 0:
        return None, {"reason": "Invalid market cap, rank or volume"}

    rank_score = max(
        0,
        min(100, 100 - ((rank - 101) / 399 * 100)),
    )

    if 10_000_000 <= market_cap <= 1_000_000_000:
        cap_score = 100
    elif market_cap < 10_000_000:
        cap_score = market_cap / 10_000_000 * 100
    else:
        cap_score = max(
            0,
            100 - (
                (market_cap - 1_000_000_000)
                / 9_000_000_000
                * 100
            ),
        )

    volume_ratio = volume / market_cap

    if 0.05 <= volume_ratio <= 0.50:
        liquidity_score = 100
    elif volume_ratio < 0.05:
        liquidity_score = min(
            100,
            volume_ratio / 0.05 * 100,
        )
    else:
        liquidity_score = max(
            0,
            100 - ((volume_ratio - 0.50) * 100),
        )

    score = (
        rank_score * 0.20
        + cap_score * 0.35
        + liquidity_score * 0.45
    )

    return _clamp_score(score), {
        "market_cap_rank": rank,
        "market_cap_usd": market_cap,
        "volume_24h_usd": volume,
        "volume_to_market_cap_ratio": round(volume_ratio, 4),
        "rank_score": round(rank_score, 2),
        "market_cap_score": round(cap_score, 2),
        "liquidity_score": round(liquidity_score, 2),
        "method": "Preliminary market fundamentals heuristic",
    }


def calculate_development_activity(
    github: dict,
) -> tuple[float | None, dict]:
    if github.get("status") != "available":
        return None, {
            "reason": "GitHub repository is not verified and available",
            "repository_status": github.get("status"),
            "matched_repository": github.get("matched_repository"),
        }

    data = github.get("data") or {}

    if data.get("verified") is not True:
        return None, {
            "reason": "Official repository ownership has not been verified",
            "matched_repository": github.get("matched_repository"),
            "candidates": github.get("candidates", []),
        }

    commits = data.get("recent_commits")
    commits_available = data.get("recent_commits_available")

    if commits_available is False:
        return None, {
            "reason": "GitHub recent commit data could not be retrieved",
        }

    if not isinstance(commits, list):
        return None, {
            "reason": "GitHub recent commit data is missing or invalid",
        }

    contributors = _to_float(data.get("contributors_count"))
    stars = _to_float(data.get("stars"))

    if contributors is None or stars is None:
        return None, {
            "reason": "Contributor or star information is unavailable",
        }

    if contributors < 0 or stars < 0:
        return None, {
            "reason": "Invalid contributor or star information",
        }

    commit_count = len([
        commit for commit in commits
        if isinstance(commit, dict)
    ])

    commit_score = min(100, commit_count / 20 * 100)
    contributor_score = min(100, contributors / 20 * 100)
    star_score = min(
        100,
        math.log10(max(stars, 1) + 1) / 4 * 100,
    )

    score = (
        commit_score * 0.50
        + contributor_score * 0.30
        + star_score * 0.20
    )

    return _clamp_score(score), {
        "recent_commit_count": commit_count,
        "recent_commit_data_available": True,
        "contributors_count": int(contributors),
        "stars": int(stars),
        "commit_score": round(commit_score, 2),
        "contributor_score": round(contributor_score, 2),
        "star_score": round(star_score, 2),
        "verified_repository": data.get("repository"),
        "method": "Preliminary verified GitHub activity heuristic",
    }


def calculate_project_growth(
    defillama: dict,
) -> tuple[float | None, dict]:
    if defillama.get("status") != "available":
        return None, {
            "reason": "DeFiLlama data is unavailable",
        }

    data = defillama.get("data") or {}
    details = data.get("details") or {}
    tvl_history = details.get("tvl")

    if not isinstance(tvl_history, list):
        return None, {
            "reason": "Historical TVL data is unavailable",
        }

    valid_points = []

    for point in tvl_history:
        if not isinstance(point, dict):
            continue

        timestamp = _to_float(point.get("date"))
        tvl = _to_float(point.get("totalLiquidityUSD"))

        if timestamp is None or tvl is None or tvl < 0:
            continue

        valid_points.append({
            "timestamp": timestamp,
            "tvl": tvl,
        })

    valid_points.sort(
        key=lambda point: point["timestamp"]
    )

    if len(valid_points) < 2:
        return None, {
            "reason": "Insufficient historical TVL observations",
        }

    latest = valid_points[-1]
    target_timestamp = latest["timestamp"] - 30 * 24 * 60 * 60

    earlier_points = [
        point
        for point in valid_points[:-1]
        if point["timestamp"] <= target_timestamp
    ]

    if not earlier_points:
        return None, {
            "reason": "At least 30 days of historical TVL is required",
            "latest_tvl_usd": latest["tvl"],
        }

    previous = earlier_points[-1]

    if previous["tvl"] <= 0:
        return None, {
            "reason": "Historical TVL baseline is zero or invalid",
        }

    growth_percentage = (
        (latest["tvl"] - previous["tvl"])
        / previous["tvl"]
    ) * 100

    growth_score = max(
        0,
        min(100, 50 + growth_percentage),
    )

    return round(growth_score, 2), {
        "protocol_name": data.get("name"),
        "protocol_slug": data.get("slug"),
        "latest_tvl_usd": round(latest["tvl"], 2),
        "previous_tvl_usd": round(previous["tvl"], 2),
        "tvl_growth_30d_percentage": round(
            growth_percentage,
            2,
        ),
        "growth_score": round(growth_score, 2),
        "method": (
            "30-day TVL growth heuristic; 0% growth scores 50"
        ),
    }


def calculate_security_score(
    goplus: dict,
) -> tuple[float | None, dict]:
    if goplus.get("status") != "available":
        return None, {
            "reason": "GoPlus security data is unavailable",
            "source_status": goplus.get("status"),
        }

    response = goplus.get("data") or {}
    security_data = response.get("security_data")

    if not isinstance(security_data, dict):
        return None, {
            "reason": "GoPlus security data has an unexpected format",
        }

    checks = {
        "is_honeypot": (True, 35),
        "cannot_sell_all": (True, 20),
        "hidden_owner": (True, 15),
        "selfdestruct": (True, 15),
        "external_call": (True, 10),
        "owner_change_balance": (True, 20),
        "is_blacklisted": (True, 15),
        "is_mintable": (True, 10),
        "is_open_source": (False, 15),
    }

    score = 100.0
    evaluated_checks = {}
    critical_flags = []

    for field, (danger_value, penalty) in checks.items():
        flag = _parse_flag(security_data.get(field))

        if flag is None:
            continue

        dangerous = flag == danger_value

        evaluated_checks[field] = {
            "value": flag,
            "risk_detected": dangerous,
            "penalty": penalty if dangerous else 0,
        }

        if dangerous:
            score -= penalty
            critical_flags.append(field)

    tax_results = {}

    for tax_name in ("buy_tax", "sell_tax"):
        tax_value = _to_float(
            security_data.get(tax_name)
        )

        if tax_value is None or tax_value < 0:
            continue

        if tax_value > 0.10:
            penalty = 20
        elif tax_value > 0.05:
            penalty = 10
        else:
            penalty = 0

        score -= penalty

        tax_results[tax_name] = {
            "value": tax_value,
            "penalty": penalty,
        }

    evaluated_count = (
        len(evaluated_checks)
        + len(tax_results)
    )

    if evaluated_count < 5:
        return None, {
            "reason": "Insufficient GoPlus indicators for scoring",
            "evaluated_checks": evaluated_count,
            "checks": evaluated_checks,
            "tax_results": tax_results,
            "critical_flags": critical_flags,
        }

    final_score = _clamp_score(score)

    return final_score, {
        "evaluated_checks": evaluated_count,
        "checks": evaluated_checks,
        "tax_results": tax_results,
        "critical_flags": critical_flags,
        "security_score": final_score,
        "method": (
            "Preliminary GoPlus risk-flag penalty heuristic; "
            "not a security audit"
        ),
    }


def calculate_news_sentiment(
    news: dict,
) -> tuple[float | None, dict]:
    if news.get("status") != "available":
        return None, {
            "reason": "News sentiment data is unavailable",
        }

    news_data = news.get("data") or {}
    article_count = news_data.get("article_count", 0)
    news_score = _to_float(news_data.get("score"))

    try:
        article_count = int(article_count)
    except (TypeError, ValueError):
        article_count = 0

    if article_count < 3:
        return None, {
            "reason": "At least 3 matched analyzed articles are required",
            "article_count": article_count,
        }

    if news_score is None or not 0 <= news_score <= 100:
        return None, {
            "reason": "News score is missing or outside the 0-100 range",
            "article_count": article_count,
        }

    return round(news_score, 2), {
        **news_data,
        "method": "Matched article sentiment score",
    }


def evaluate_project(research_data: dict) -> dict:
    project = research_data.get("project", {})
    sources = research_data.get("sources", {})

    category_scores = {
        "market_fundamentals": None,
        "development_activity": None,
        "project_growth": None,
        "security": None,
        "news_sentiment": None,
    }

    evidence = {}

    calculations = {
        "market_fundamentals": calculate_market_fundamentals(
            project
        ),
        "development_activity": calculate_development_activity(
            sources.get("github", {})
        ),
        "project_growth": calculate_project_growth(
            sources.get("defillama", {})
        ),
        "security": calculate_security_score(
            sources.get("goplus", {})
        ),
        "news_sentiment": calculate_news_sentiment(
            sources.get("news", {})
        ),
    }

    for category, (score, category_evidence) in calculations.items():
        category_scores[category] = score
        evidence[category] = category_evidence

    scoring = calculate_research_score(category_scores)

    if scoring["coverage"] >= 80:
        research_status = "ready"
    elif scoring["coverage"] > 0:
        research_status = "partial"
    else:
        research_status = "insufficient_data"

    scoring["score_type"] = (
        "final"
        if scoring["is_final"]
        else "provisional"
    )

    return {
        "project": project,
        "category_scores": category_scores,
        "score": scoring,
        "evidence": evidence,
        "research_status": research_status,
        "watchlist_status": "pending_review",
    }
