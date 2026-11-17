
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchWeights:
    market_fundamentals: float = 0.25
    development_activity: float = 0.20
    project_growth: float = 0.20
    security: float = 0.20
    news_sentiment: float = 0.15


WEIGHTS = ResearchWeights()


def calculate_research_score(
    category_scores: dict[str, float | None],
) -> dict:
    weights = {
        "market_fundamentals": WEIGHTS.market_fundamentals,
        "development_activity": WEIGHTS.development_activity,
        "project_growth": WEIGHTS.project_growth,
        "security": WEIGHTS.security,
        "news_sentiment": WEIGHTS.news_sentiment,
    }

    weighted_score = 0.0
    available_weight = 0.0
    available_categories = []
    unavailable_categories = []

    for category, weight in weights.items():
        score = category_scores.get(category)

        if score is None:
            unavailable_categories.append(category)
            continue

        if isinstance(score, bool) or not isinstance(
            score,
            (int, float),
        ):
            raise ValueError(
                f"Invalid score for {category}"
            )

        if not 0 <= score <= 100:
            raise ValueError(
                f"{category} score must be between 0 and 100"
            )

        weighted_score += score * weight
        available_weight += weight
        available_categories.append(category)

    if available_weight == 0:
        return {
            "score": None,
            "provisional_score": None,
            "coverage_adjusted_score": None,
            "coverage": 0,
            "available_categories": [],
            "unavailable_categories": unavailable_categories,
            "status": "insufficient_data",
            "score_type": "unavailable",
            "score_reliability": "none",
            "score_warning": (
                "No research categories have valid scores. "
                "A project ranking cannot be calculated."
            ),
            "is_final": False,
        }

    normalized_score = round(
        weighted_score / available_weight,
        2,
    )

    coverage = round(
        available_weight * 100,
        2,
    )

    if coverage >= 80:
        reliability = "high"
        warning = None
    elif coverage >= 60:
        reliability = "moderate"
        warning = (
            "Provisional score: some research categories are "
            "missing. Do not treat this as a complete project ranking."
        )
    else:
        reliability = "low"
        warning = (
            "Very limited research coverage. The provisional score "
            "is based on a small subset of categories and must not "
            "be used to rank or approve this project."
        )

    is_final = coverage >= 80

    return {
        "score": normalized_score,
        "provisional_score": (
            None if is_final else normalized_score
        ),
        "coverage_adjusted_score": round(
            weighted_score,
            2,
        ),
        "coverage": coverage,
        "available_categories": available_categories,
        "unavailable_categories": unavailable_categories,
        "status": (
            "complete"
            if coverage == 100
            else "partial"
        ),
        "score_type": (
            "final"
            if is_final
            else "provisional"
        ),
        "score_reliability": reliability,
        "score_warning": warning,
        "is_final": is_final,
    }
