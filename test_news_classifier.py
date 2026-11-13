
from app.agents.news_sentiment.classifier import classify_news


assets = [
    {
        "name": "Bitcoin",
        "symbol": "BTC",
        "aliases": [],
    },
    {
        "name": "Ethereum",
        "symbol": "ETH",
        "aliases": [],
    },
    {
        "name": "Solana",
        "symbol": "SOL",
        "aliases": [],
    },
    {
        "name": "BNB",
        "symbol": "BNB",
        "aliases": ["BNB Chain", "BNB token"],
    },
]


test_articles = [
    {
        "article_id": "test-001",
        "source": "test",
        "title": "Bitcoin adoption surges after major institutional inflows",
        "summary": "Bitcoin sees strong growth and bullish market sentiment.",
        "url": "https://example.com/bitcoin",
    },
    {
        "article_id": "test-002",
        "source": "test",
        "title": "Ethereum protocol suffers major hack and exploit",
        "summary": "Millions of dollars were stolen after a security breach.",
        "url": "https://example.com/ethereum",
    },
    {
        "article_id": "test-003",
        "source": "test",
        "title": "Solana announces a new network upgrade",
        "summary": "The project announced a technical upgrade.",
        "url": "https://example.com/solana",
    },
    {
        "article_id": "test-004",
        "source": "test",
        "title": "Crypto community conference announced",
        "summary": "A community event will take place next month.",
        "url": "https://example.com/community",
    },
    {
        "article_id": "test-005",
        "source": "test",
        "title": "General crypto hack losses increase across the industry",
        "summary": "A research report discusses historical crypto security losses.",
        "url": "https://example.com/security-report",
    },
    {
        "article_id": "test-006",
        "source": "test",
        "title": "BNB Chain suffers a major exploit and funds are stolen",
        "summary": "The network confirms that attackers exploited a vulnerability.",
        "url": "https://example.com/bnb-exploit",
    },
    {
        "article_id": "test-007",
        "source": "test",
        "title": "Binance announces a new trading competition",
        "summary": "The exchange launches a promotional event.",
        "url": "https://example.com/binance-event",
    },
]


live_headline_tests = [
    {
        "title": "DOJ moves to seize $1.2B from Binance hack, disrupts FaceStealer scam",
        "summary": "",
        "expected": "low",
    },
    {
        "title": "NK hackers join memecoin trenches, xStocks adds Hong Kong equities: Asia Express",
        "summary": "",
        "expected": "low",
    },
    {
        "title": "Crypto hack losses equal 57 cents per $1 earned onchain: Ark's Valente",
        "summary": "",
        "expected": "low",
    },
    {
        "title": "Ethereum protocol suffers major hack and exploit",
        "summary": "Millions of dollars were stolen after a security breach.",
        "expected": "critical",
    },
    {
        "title": "BNB Chain suffers a major exploit and funds are stolen",
        "summary": "The network confirms that attackers exploited a vulnerability.",
        "expected": "critical",
    },
]

for index, test in enumerate(live_headline_tests):
    result = classify_news(test, assets)

    actual = result["severity"]["severity"]

    assert actual == test["expected"], (
        f"Headline test {index + 1} failed: "
        f"expected {test['expected']}, got {actual}"
    )

print("All live headline regression tests passed!")


print("\nNEWS CLASSIFIER TEST REPORT")
print("===========================")

for article in test_articles:
    result = classify_news(article, assets)

    print("\nARTICLE:", result["title"])
    print("Sentiment:", result["sentiment"]["sentiment"])
    print("Severity:", result["severity"]["severity"])
    print("Affected coins:", result["affected_coins"])


print("\nRUNNING ASSERTIONS")
print("==================")


bitcoin = classify_news(test_articles[0], assets)

assert bitcoin["sentiment"]["sentiment"] == "positive", (
    "Bitcoin adoption article should have positive sentiment"
)

assert any(
    coin["symbol"] == "BTC"
    for coin in bitcoin["affected_coins"]
), "Bitcoin should be identified"


ethereum = classify_news(test_articles[1], assets)

assert ethereum["sentiment"]["sentiment"] == "negative", (
    "Ethereum hack should have negative sentiment"
)

assert ethereum["severity"]["severity"] == "critical", (
    "Ethereum hack should be classified as critical"
)

assert any(
    coin["symbol"] == "ETH"
    for coin in ethereum["affected_coins"]
), "Ethereum should be identified"


solana = classify_news(test_articles[2], assets)

assert solana["sentiment"]["sentiment"] == "neutral", (
    "Solana upgrade should have neutral sentiment"
)

assert solana["severity"]["severity"] == "medium", (
    "Solana network upgrade should have medium severity"
)

assert any(
    coin["symbol"] == "SOL"
    for coin in solana["affected_coins"]
), "Solana should be identified"


community = classify_news(test_articles[3], assets)

assert community["sentiment"]["sentiment"] == "neutral", (
    "Community conference should have neutral sentiment"
)

assert community["severity"]["severity"] == "low", (
    "Community conference should have low severity"
)

assert community["affected_coins"] == [], (
    "Community conference should not identify unrelated coins"
)


general_security = classify_news(test_articles[4], assets)

assert general_security["severity"]["severity"] != "critical", (
    "General security research should not automatically be critical"
)


bnb_exploit = classify_news(test_articles[5], assets)

assert bnb_exploit["severity"]["severity"] == "critical", (
    "Confirmed BNB Chain exploit should be critical"
)

assert any(
    coin["symbol"] == "BNB"
    for coin in bnb_exploit["affected_coins"]
), "BNB Chain alias should identify BNB"


binance_event = classify_news(test_articles[6], assets)

assert not any(
    coin["symbol"] == "BNB"
    for coin in binance_event["affected_coins"]
), "Binance exchange mention should not automatically identify BNB"


print("\nAll 7 news classifier test cases passed!")
