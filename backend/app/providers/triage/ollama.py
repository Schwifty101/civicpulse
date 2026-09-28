"""Fully offline path — a container running a small model via the Ollama HTTP API.
Same TriageProvider interface, no key, no external network, no PII leaving the machine.
Not started by default (see compose.yaml's `ollama` profile); code here works the moment
TRIAGE_PROVIDER=ollama and the service is up.
"""

import httpx

from app.providers.triage.base import NonRetryableTriageError, RetryableTriageError, retry_call
from app.providers.triage.prompt import build_messages, parse_llm_json
from app.schemas import TriageResult

_TIMEOUT_SECONDS = 10.0


class OllamaTriage:
    name = "llm:ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def triage(self, text: str, location: str) -> TriageResult:
        messages = build_messages(text, location)
        raw = retry_call(lambda: self._call(messages))
        return parse_llm_json(raw)

    def _call(self, messages: list[dict[str, str]]) -> str:
        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2},
                },
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise RetryableTriageError(f"llm:ollama timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise RetryableTriageError(f"llm:ollama request error: {exc}") from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise RetryableTriageError(f"llm:ollama returned {resp.status_code}")
        if resp.status_code >= 400:
            raise NonRetryableTriageError(
                f"llm:ollama returned {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise NonRetryableTriageError(f"llm:ollama unexpected response shape: {exc}") from exc
