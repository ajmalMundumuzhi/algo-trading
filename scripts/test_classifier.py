
from app.agents.news_sentiment.classifier import (
    classify_sentiment,
    classify_severity,
)

test_articles = [
    {
        "title": "Major crypto exchange suffers security hack",
        "summary": "Millions stolen from compromised wallets.",
    },
    {
        "title": "Binance announces token delisting",
        "summary": "Trading will be suspended next week.",
    },
    {
        "title": "Ethereum announces major network upgrade",
        "summary": "The upgrade improves network performance.",
    },
    {
        "title": "Bitcoin price falls as ETF outflows increase",
        "summary": "Investors reduce exposure.",
    },
    {
        "title": "Crypto conference announces community event",
        "summary": "Developers will attend the conference.",
    },
]

for article in test_articles:
    print("\nARTICLE:", article["title"])
    print("SENTIMENT:", classify_sentiment(article))
    print("SEVERITY:", classify_severity(article))
