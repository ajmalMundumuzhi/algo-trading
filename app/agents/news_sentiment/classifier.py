
import re


POSITIVE_KEYWORDS = {
    "surge", "surges", "rally", "rallies", "bullish",
    "adoption", "approval", "approved", "partnership",
    "integration", "inflow", "inflows", "record high",
    "breakout", "growth", "recovery", "profit", "gains",
    "rises", "rose", "climbs", "climbed", "upgrade",
    "launch", "launched", "expansion", "milestone",
}

NEGATIVE_KEYWORDS = {
    "crash", "crashes", "plunge", "plunges", "bearish",
    "hack", "hacked", "exploit", "exploited", "breach",
    "stolen", "lawsuit", "ban", "banned", "delisting",
    "delisted", "bankruptcy", "insolvency", "outflow",
    "outflows", "loss", "losses", "collapse", "liquidation",
    "liquidations", "falls", "fell", "drops", "dropped",
    "decline", "declines", "slump", "slumps", "suspends",
    "suspended", "halted", "fraud", "investigation",
}


CRITICAL_PATTERNS = {
    "confirmed_hack": (
        r"\b(?:suffers?|suffered|hit by|targeted by)\s+"
        r"(?:a\s+)?(?:major\s+|security\s+)?"
        r"(?:hack|exploit|breach|attack)\b",
        r"\b(?:protocol|exchange|bridge|network|platform)\s+"
        r"(?:was|has been|have been)\s+"
        r"(?:hacked|exploited|breached|attacked)\b",
        r"\b(?:private keys?|wallets?)\s+"
        r"(?:were\s+)?(?:compromised|drained)\b",
        r"\b(?:millions|billions|\$[\d,.]+)\s+"
        r"(?:stolen|drained)\b",
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
        r"\bdelist(?:ed|ing)?\b",
        r"\b(?:exchange|binance|coinbase|kraken)\s+"
        r"(?:will|plans to|announces|announced)\s+"
        r"delist\b",
    ),
    "regulatory_action": (
        r"\b(?:charged|indicted|sued|sanctioned)\s+(?:by|for)\b",
        r"\bregulatory\s+(?:action|crackdown|investigation)\b",
        r"\b(?:SEC|CFTC)\s+(?:files|filed)\s+"
        r"(?:a\s+)?(?:lawsuit|charges|action)\b",
    ),
    "service_restriction": (
        r"\bwithdrawals?\s+(?:restricted|frozen)\b",
        r"\btrading\s+(?:suspended|halted)\b",
    ),
    "major_security_risk": (
        r"\b(?:critical|major|severe)\s+"
        r"(?:security\s+)?(?:vulnerability|exploit)\b",
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
        r"\bunlock(?:s|ed)?\s+"
        r"(?:tokens?|worth|valued)\b",
    ),
    "etf_event": (
        r"\bETF\s+(?:approval|rejection|launch)\b",
    ),
    "fundraising": (
        r"\braises?\s+\$[\d,.]+\s+"
        r"(?:million|billion)\b",
        r"\bfunding\s+round\b",
    ),
    "exchange_listing": (
        r"\blisted\s+on\s+(?:binance|coinbase|kraken)\b",
        r"\bnew\s+exchange\s+listing\b",
    ),
    "market_outflows": (
        r"\bETF\s+outflows?\b",
        r"\b(?:fund|exchange|market)\s+outflows?\b",
    ),
    "market_decline": (
        r"\b(?:sharp|major|significant)\s+"
        r"(?:price\s+)?(?:decline|drop|loss)\b",
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
        str(text or "").lower(),
    ).strip()


def _find_keywords(text: str, keywords: set[str]) -> list[str]:
    return sorted(
        keyword
        for keyword in keywords
        if re.search(
            rf"(?<!\w){re.escape(keyword)}(?!\w)",
            text,
        )
    )


def _find_patterns(text: str, patterns: dict) -> list[str]:
    return [
        event_name
        for event_name, expressions in patterns.items()
        if any(
            re.search(expression, text, re.IGNORECASE)
            for expression in expressions
        )
    ]


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

        matched_terms = []

        for term in [name, *aliases]:
            term = str(term).strip()

            if not term:
                continue

            pattern = (
                rf"(?<!\w){re.escape(_normalize_text(term))}(?!\w)"
            )

            if re.search(pattern, text):
                matched_terms.append(term)

        symbol_patterns = (
            rf"\${re.escape(symbol)}(?!\w)",
            rf"(?<!\w){re.escape(symbol)}"
            rf"\s*[/\-]\s*(?:USDT|USD|USDC|BTC)(?!\w)",
        )

        symbol_match = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in symbol_patterns
        )

        if (
            matched_terms or symbol_match
        ) and symbol not in seen_symbols:
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

    positive_matches = _find_keywords(text, POSITIVE_KEYWORDS)
    negative_matches = _find_keywords(text, NEGATIVE_KEYWORDS)

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

    severity_rules = (
        ("critical", CRITICAL_PATTERNS),
        ("high", HIGH_PATTERNS),
        ("medium", MEDIUM_PATTERNS),
        ("low", LOW_PATTERNS),
    )

    for severity, patterns in severity_rules:
        matched_events = _find_patterns(text, patterns)

        if matched_events:
            return {
                "severity": severity,
                "matched_events": matched_events,
            }

    return {
        "severity": "low",
        "matched_events": [],
    }


def classify_news(
    article: dict,
    assets: list[dict],
) -> dict:
    return {
        "article_id": article.get("article_id"),
        "source": article.get("source"),
        "title": article.get("title"),
        "url": article.get("url"),
        "sentiment": classify_sentiment(article),
        "severity": classify_severity(article),
        "affected_coins": identify_affected_coins(
            article,
            assets,
        ),
    }
