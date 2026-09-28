import random
import time
from collections.abc import Callable
from typing import Protocol, TypeVar

from app.schemas import TriageResult


class TriageError(Exception):
    """Base class for triage provider failures."""


class RetryableTriageError(TriageError):
    """Timeout, 429 or 5xx — worth one retry with jitter."""


class NonRetryableTriageError(TriageError):
    """Bad request, malformed/unparseable output — retrying would fail the same way."""


class TriageProvider(Protocol):
    name: str

    def triage(self, text: str, location: str) -> TriageResult: ...


T = TypeVar("T")

MAX_ATTEMPTS = 2  # one try + one retry, per spec: "retry once, with jitter"


def retry_call(fn: Callable[[], T]) -> T:
    """Shared retry loop for LLMTriage/OllamaTriage: retries only RetryableTriageError
    (timeout/429/5xx), never NonRetryableTriageError (bad request/bad output)."""
    last_error: RetryableTriageError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except RetryableTriageError as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(0.1 * (2**attempt) + random.uniform(0, 0.1), 2.0))
    assert last_error is not None
    raise last_error
