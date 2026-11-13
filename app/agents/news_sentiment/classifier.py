
import re


POSITIVE_KEYWORDS = {
    "surge",
    "surges",
    "rally",
    "rallies",
    "bullish",
    "adoption",
    "approval",
    "approved",
    "partnership",
    "integration",
    "inflow",
    "inflows",
    "record high",
    "breakout",
    "growth",
    "recovery",
    "profit",
    "gains",
}

NEGATIVE_KEYWORDS = {
    "crash",
    "crashes",
    "plunge",
    "plunges",
    "bearish",
    "hack",
    "hacked",
    "exploit",
    "exploited",
    "breach",
    "stolen",
    "lawsuit",
    "ban",
    "banned",
    "delisting",
    "delisted",
    "bankruptcy",
    "insolvency",
    "outflow",
    "outflows",
    "loss",
    "losses",
    "collapse",
    "liquidation",
    "liquidations",
}



CRITICAL_PATTERNS = {
    "confirmed_hack": (
        r"\b(?:suffers?|suffered|hit by|targeted by)\s+"
        r"(?:a\s+)?(?:major\s+|security\s+)?"
        r"(?:hack|exploit|breach|attack)\b",

        r"\b(?:protocol|exchange|bridge|network|platform)\s+"
        r"(?:was|has been|have been)\s+"
        r"(?:hacked|exploited|breached|attacked)\b",

        r"\b(?:hack|exploit|breach|attack)\s+"
        r"(?:of|on|against)\s+"
        r"(?:the\s+)?(?:protocol|exchange|bridge|network|platform)\b",

        r"\b(?:private keys?|wallets?)\s+"
        r"(?:were\s+)?(?:compromised|drained)\b",
    ),

    "critical_service_disruption": (
        r"\b(?:withdrawals?|deposits?)\s+"
        r"(?:have been\s+)?suspended\b",

        r"\b(?:exchange|protocol|bridge)\s+"
        r"(?:has\s+)?(?:shut down|halted operations)\b",
    ),
}


HIGH_PATTERNS = {
    "delisting": (
        r"\b(?:will be|to be|is being)\s+delisted\b",
        r"\bdelisting\s+of\b",
    ),
    "regulatory_action": (
        r"\b(?:charged|indicted|sued|sanctioned)\s+"
        r"(?:by|for)\b",
        r"\bregulatory\s+(?:action|crackdown|investigation)\b",
        r"\b(?:SEC|CFTC)\s+(?:files|filed)\s+"
        r"(?:a\s+)?(?:lawsuit|charges|action)\b",
    ),
    "service_restriction": (
        r"\bwithdrawals?\s+(?:restricted|frozen)\b",
        r"\btrading\s+(?:suspended|halted)\b",
    ),
}

MEDIUM_PATTERNS = {
    "partnership": (
        r"\bpartnership\b",
        r"\bpartners?\s+with\b",
    ),
    "network_upgrade": (
        r"\bnetwork\s+upgrade\b",
        r"\bmainnet\s+(?:launch|upgrade)\b",
        r"\bprotocol\s+upgrade\b",
    ),
    "token_unlock": (
        r"\btoken\s+unlock\b",
        r"\bvesting\s+release\b",
    ),
    "etf_event": (
        r"\bETF\s+(?:approval|rejection|launch)\b",
    ),
}

LOW_PATTERNS = {
    "community_event": (
        r"\bconference\b",
        r"\bcommunity\s+event\b",
        r"\binterview\b",
    ),
}


def _normalize_text(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text).lower(),
    ).strip()


def _find_keywords(
    text: str,
    keywords: set[str],
) -> list[str]:
    return sorted(
        keyword
        for keyword in keywords
        if re.search(
            rf"(?<!\w){re.escape(keyword)}(?!\w)",
            text,
        )
    )


def _find_patterns(
    text: str,
    patterns: dict,
) -> list[str]:
    matches = []

    for event_name, expressions in patterns.items():
        if any(
            re.search(expression, text, re.IGNORECASE)
            for expression in expressions
        ):
            matches.append(event_name)

    return matches


def identify_affected_coins(
    article: dict,
    assets: list[dict],
) -> list[dict]:
    text = _normalize_text(
        f"{article.get('title', '')} "
        f"{article.get('summary', '')}"
    )

    affected_coins = []
    seen_symbols = set()

    for asset in assets:
        name = str(asset.get("name", "")).strip()
        symbol = str(asset.get("symbol", "")).strip().upper()

        if not name or not symbol:
            continue

        aliases = asset.get("aliases", [])

        if not isinstance(aliases, list):
            aliases = []

        terms = [name, *aliases]
        matched_terms = []

        for term in terms:
            term = str(term).strip()

            if not term:
                continue

            normalized_term = _normalize_text(term)

            pattern = (
                rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
            )

            if re.search(pattern, text):
                matched_terms.append(term)

        symbol_patterns = [
            rf"\${re.escape(symbol)}(?!\w)",
            rf"(?<!\w){re.escape(symbol)}"
            rf"\s*[/\-]\s*(?:USDT|USD|USDC|BTC)(?!\w)",
        ]

        symbol_match = any(
            re.search(pattern, text)
            for pattern in symbol_patterns
        )

        if (matched_terms or symbol_match) and symbol not in seen_symbols:
            affected_coins.append({
                "name": name,
                "symbol": symbol,
                "matched_terms": matched_terms,
                "matched_by_symbol": symbol_match,
            })

            seen_symbols.add(symbol)

    return affected_coins


def classify_sentiment(article: dict) -> dict:
    text = _normalize_text(
        f"{article.get('title', '')} "
        f"{article.get('summary', '')}"
    )

    positive_matches = _find_keywords(
        text,
        POSITIVE_KEYWORDS,
    )

    negative_matches = _find_keywords(
        text,
        NEGATIVE_KEYWORDS,
    )

    positive_score = len(positive_matches)
    negative_score = len(negative_matches)

    if positive_score > negative_score:
        sentiment = "positive"
    elif negative_score > positive_score:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "positive_score": positive_score,
        "negative_score": negative_score,
        "positive_keywords": positive_matches,
        "negative_keywords": negative_matches,
    }


def classify_severity(article: dict) -> dict:
    text = _normalize_text(
        f"{article.get('title', '')} "
        f"{article.get('summary', '')}"
    )

    critical_events = _find_patterns(
        text,
        CRITICAL_PATTERNS,
    )

    high_events = _find_patterns(
        text,
        HIGH_PATTERNS,
    )

    medium_events = _find_patterns(
        text,
        MEDIUM_PATTERNS,
    )

    low_events = _find_patterns(
        text,
        LOW_PATTERNS,
    )

    if critical_events:
        severity = "critical"
        matched_events = critical_events
    elif high_events:
        severity = "high"
        matched_events = high_events
    elif medium_events:
        severity = "medium"
        matched_events = medium_events
    elif low_events:
        severity = "low"
        matched_events = low_events
    else:
        severity = "low"
        matched_events = []

    return {
        "severity": severity,
        "matched_events": matched_events,
    }


def classify_news(
    article: dict,
    assets: list[dict],
) -> dict:
    sentiment = classify_sentiment(article)
    severity = classify_severity(article)

    affected_coins = identify_affected_coins(
        article,
        assets,
    )

    return {
        "article_id": article.get("article_id"),
        "source": article.get("source"),
        "title": article.get("title"),
        "url": article.get("url"),
        "sentiment": sentiment,
        "severity": severity,
        "affected_coins": affected_coins,
    }
