"""Deterministic fake for CI: seeded by content hash, no network, configurable failure
injection. TRIAGE_PROVIDER=simulated is what CI pins to, so the suite is green on every
run — see docs/ENGINEERING-NOTES.md Q4.
"""

import hashlib

from app.providers.triage.base import RetryableTriageError
from app.providers.triage.rules import _classify_category, _classify_priority, _summarize
from app.schemas import TriageResult


class SimulatedTriage:
    name = "llm:groq"  # pretends to be the production provider it stands in for

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def triage(self, text: str, location: str) -> TriageResult:
        if self.fail:
            raise RetryableTriageError("simulated provider configured to always fail")

        text_lower = text.lower()
        category, _ = _classify_category(text_lower)
        priority = _classify_priority(text_lower)
        summary = _summarize(text, location, category)

        # Deterministic confidence derived from content hash — not a magic constant,
        # but stable across runs for the same input (what "seeded, no network" buys you).
        digest = hashlib.sha256(text_lower.encode()).hexdigest()
        confidence = 0.7 + (int(digest[:2], 16) / 255) * 0.29  # 0.70-0.99

        return TriageResult(
            category=category, priority=priority, summary=summary, confidence=round(confidence, 2)
        )
