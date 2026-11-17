
from app.agents.research.candidate_filter import (
    filter_research_candidates,
)


def test_excludes_stablecoins():
    candidates = [
        {"id": "tether", "name": "Tether", "symbol": "usdt"},
        {"id": "usd-coin", "name": "USDC", "symbol": "usdc"},
    ]

    result = filter_research_candidates(candidates)

    assert result["total_eligible"] == 0
    assert result["total_rejected"] == 2


def test_excludes_tokenized_treasury():
    candidates = [
        {
            "id": "example",
            "name": "Example Tokenized Treasury Fund",
            "symbol": "ETF",
        }
    ]

    result = filter_research_candidates(candidates)

    assert result["total_rejected"] == 1


def test_keeps_regular_crypto_projects():
    candidates = [
        {"id": "pyth-network", "name": "Pyth Network", "symbol": "pyth"},
        {"id": "render-token", "name": "Render", "symbol": "render"},
    ]

    result = filter_research_candidates(candidates)

    assert result["total_eligible"] == 2
    assert result["total_rejected"] == 0


def test_removes_zero_width_characters():
    candidates = [
        {"id": "stable", "name": "\u200b\u200bStable", "symbol": "stable"},
    ]

    result = filter_research_candidates(candidates)

    assert result["eligible"][0]["name"] == "Stable"
