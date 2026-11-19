
from types import SimpleNamespace

from app.agents.research.news_collector import (
    article_matches_candidate,
    matches_candidate_text,
)


def make_article(title, summary="", affected_coins=None):
    return SimpleNamespace(
        title=title,
        summary=summary,
        affected_coins=affected_coins or [],
    )


def test_explicit_cash_dollar_symbol_matches():
    candidate = {"name": "CASH", "symbol": "cash"}

    article = make_article(
        "The $CASH token gains momentum in crypto markets"
    )

    assert matches_candidate_text(candidate, article) is True


def test_cash_usd_trading_pair_matches():
    candidate = {"name": "CASH", "symbol": "cash"}

    article = make_article(
        "CASH/USD trading volume increases"
    )

    assert matches_candidate_text(candidate, article) is True


def test_ordinary_word_cash_does_not_match():
    candidate = {"name": "CASH", "symbol": "cash"}

    article = make_article(
        "Meta tests prediction market app using cred points instead of cash"
    )

    assert matches_candidate_text(candidate, article) is False


def test_legitimate_coin_name_matches():
    candidate = {"name": "SwissBorg", "symbol": "BORG"}

    article = make_article(
        "SwissBorg announces a new ecosystem development"
    )

    assert matches_candidate_text(candidate, article) is True


def test_unrelated_article_does_not_match():
    candidate = {"name": "SwissBorg", "symbol": "BORG"}

    article = make_article(
        "Bitcoin market analysis and Ethereum price update"
    )

    assert matches_candidate_text(candidate, article) is False


def test_structured_affected_coins_matches_candidate():
    candidate = {
        "id": "eigenlayer",
        "name": "EigenCloud",
        "symbol": "EIGEN",
    }

    article = make_article(
        "A new development in the crypto ecosystem",
        affected_coins=[
            {
                "symbol": "EIGEN",
                "name": "EigenCloud",
            }
        ],
    )

    assert article_matches_candidate(candidate, article) is True


def test_unrelated_structured_coin_does_not_match():
    candidate = {
        "id": "eigenlayer",
        "name": "EigenCloud",
        "symbol": "EIGEN",
    }

    article = make_article(
        "Bitcoin market analysis",
        affected_coins=[
            {
                "symbol": "BTC",
                "name": "Bitcoin",
            }
        ],
    )

    assert article_matches_candidate(candidate, article) is False


def test_bare_br_does_not_match_unrelated_article():
    candidate = {
        "name": "Bedrock",
        "symbol": "BR",
    }

    article = make_article(
        "Ethereum blockchain development continues to grow"
    )

    assert matches_candidate_text(candidate, article) is False


def test_bare_trac_does_not_match_unrelated_article():
    candidate = {
        "name": "OriginTrail",
        "symbol": "TRAC",
    }

    article = make_article(
        "Safe wallet loses funds after security breach"
    )

    assert matches_candidate_text(candidate, article) is False


def test_br_dollar_symbol_matches():
    candidate = {
        "name": "Bedrock",
        "symbol": "BR",
    }

    article = make_article(
        "The $BR token gains attention in crypto markets"
    )

    assert matches_candidate_text(candidate, article) is True


def test_trac_usdt_pair_matches():
    candidate = {
        "name": "OriginTrail",
        "symbol": "TRAC",
    }

    article = make_article(
        "TRAC/USDT trading volume increases"
    )

    assert matches_candidate_text(candidate, article) is True


def test_origintrail_exact_name_matches():
    candidate = {
        "name": "OriginTrail",
        "symbol": "TRAC",
    }

    article = make_article(
        "OriginTrail announces a network development"
    )

    assert matches_candidate_text(candidate, article) is True


def test_bedrock_generic_word_does_not_match():
    candidate = {
        "name": "Bedrock",
        "symbol": "BR",
    }

    article = make_article(
        "The company builds its business on a solid bedrock"
    )

    assert matches_candidate_text(candidate, article) is False


def test_bedrock_structured_affected_coin_matches():
    candidate = {
        "id": "bedrock",
        "name": "Bedrock",
        "symbol": "BR",
    }

    article = make_article(
        "A new development in the crypto ecosystem",
        affected_coins=[
            {
                "name": "Bedrock",
                "symbol": "BR",
            }
        ],
    )

    assert article_matches_candidate(candidate, article) is True
