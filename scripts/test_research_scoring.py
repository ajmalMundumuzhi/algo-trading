
from app.agents.research.scorer import calculate_research_score
from app.agents.research.evaluator import evaluate_project


def main():
    print("RESEARCH SCORING TEST")
    print("=====================")

    test_scores = {
        "market_fundamentals": 80,
        "development_activity": None,
        "project_growth": 70,
        "security": None,
        "news_sentiment": 60,
    }

    result = calculate_research_score(test_scores)

    print("\nPartial scoring:")
    print(result)

    assert result["status"] == "partial"
    assert result["coverage"] == 60
    assert result["score"] == 71.67

    sample_project = {
        "project": {
            "name": "Example Project",
            "market_cap": 100000000,
            "market_cap_rank": 150,
            "total_volume": 5000000,
        },
        "sources": {},
    }

    evaluation = evaluate_project(sample_project)

    print("\nProject evaluation:")
    print(evaluation)

    assert evaluation["research_score"]["coverage"] == 25

    print("\nALL RESEARCH SCORING TESTS PASSED")


if __name__ == "__main__":
    main()
