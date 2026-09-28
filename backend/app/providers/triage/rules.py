"""Deterministic keyword classifier. Always available, never raises — the provider
every other provider falls back to when it can't be trusted."""

import re

from app.schemas import Category, Priority, TriageResult

_CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.WATER: (
        "water",
        "pipe",
        "burst",
        "leak",
        "flood",
        "tap",
        "sewer line",
        "supply line",
    ),
    Category.ELECTRICITY: (
        "electric",
        "power",
        "transformer",
        "wire",
        "cable",
        "shock",
        "outage",
        "voltage",
        "meter",
    ),
    Category.SANITATION: (
        "garbage",
        "trash",
        "sewage",
        "drain",
        "waste",
        "sanitation",
        "sewer",
        "smell",
        "dump",
    ),
    Category.ROADS: (
        "road",
        "pothole",
        "street damage",
        "traffic",
        "footpath",
        "speed breaker",
        "manhole",
    ),
    Category.STREETLIGHTS: (
        "streetlight",
        "street light",
        "lamp",
        "dark street",
        "pole light",
    ),
}

_HIGH_URGENCY_KEYWORDS = (
    "urgent",
    "emergency",
    "danger",
    "fire",
    "flooding",
    "electrocut",
    "collapsed",
    "injur",
    "burst",
    "since fajr",
    "since morning",
    "overnight",
)

_LOW_URGENCY_KEYWORDS = ("minor", "small", "not urgent", "whenever", "no rush", "cosmetic")


def _classify_category(text_lower: str) -> tuple[Category, float]:
    best: Category | None = None
    best_hits = 0
    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > best_hits:
            best, best_hits = category, hits
    if best is None:
        return Category.OTHER, 0.3
    confidence = min(0.5 + 0.1 * best_hits, 0.9)
    return best, confidence


def _classify_priority(text_lower: str) -> Priority:
    if any(kw in text_lower for kw in _HIGH_URGENCY_KEYWORDS):
        return Priority.HIGH
    if any(kw in text_lower for kw in _LOW_URGENCY_KEYWORDS):
        return Priority.LOW
    return Priority.NORMAL


def _summarize(text: str, location: str, category: Category) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    summary = f"{category.value.capitalize()} issue at {location}: {clean}"
    return summary[:140]


class RuleBasedTriage:
    name = "rules"

    def triage(self, text: str, location: str) -> TriageResult:
        text_lower = text.lower()
        category, confidence = _classify_category(text_lower)
        priority = _classify_priority(text_lower)
        summary = _summarize(text, location, category)
        return TriageResult(
            category=category, priority=priority, summary=summary, confidence=confidence
        )
