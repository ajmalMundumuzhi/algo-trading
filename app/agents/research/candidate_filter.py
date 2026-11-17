
import re
import unicodedata

from app.agents.research.config import RESEARCH_CONFIG


EXCLUDED_SYMBOLS = {
    "USDT", "USDC", "USDS", "USDE", "DAI",
    "FDUSD", "TUSD", "USDP", "PYUSD", "BUSD",
    "RLUSD", "USD1", "EURC",
    "A7A5", "YLDS", "STABLE",
}

EXCLUDED_NAME_PATTERNS = [
    r"\bstablecoin\b",
    r"\busd coin\b",
    r"\bus dollar\b",
    r"\beuro stablecoin\b",
    r"\btokenized treasury\b",
    r"\btreasury bill\b",
    r"\bt-bill\b",
    r"\bmoney market fund\b",
    r"\btreasury fund\b",
    r"\bgovernment bond fund\b",
    r"\btokenized stock\b",
    r"\btokenized equity\b",
    r"\bwrapped bitcoin\b",
    r"\bwrapped ether\b",
]

COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in EXCLUDED_NAME_PATTERNS
]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = value.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def get_exclusion_reason(candidate: dict) -> str | None:
    symbol = normalize_text(candidate.get("symbol", "")).upper()
    name = normalize_text(candidate.get("name", ""))

    if symbol in EXCLUDED_SYMBOLS:
        return "excluded_symbol"

    for pattern in COMPILED_PATTERNS:
        if pattern.search(name):
            return "excluded_asset_type"

    return None


def filter_research_candidates(
    candidates: list[dict],
) -> dict:
    eligible = []
    rejected = []

    for candidate in candidates:
        reason = get_exclusion_reason(candidate)

        if reason:
            rejected.append({
                "id": candidate.get("id"),
                "name": normalize_text(candidate.get("name", "")),
                "symbol": candidate.get("symbol"),
                "reason": reason,
            })
            continue

        eligible.append(candidate)

    return {
        "eligible": eligible,
        "rejected": rejected,
        "total_received": len(candidates),
        "total_eligible": len(eligible),
        "total_rejected": len(rejected),
    }
