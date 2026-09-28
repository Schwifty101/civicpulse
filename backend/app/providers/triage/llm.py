"""Production triage path — a free-tier hosted model via Groq's OpenAI-compatible
chat-completions endpoint, called with plain httpx (no SDK needed for one JSON POST).
"""

import httpx

from app.providers.triage.base import NonRetryableTriageError, RetryableTriageError, retry_call
from app.providers.triage.prompt import build_messages, parse_llm_json
from app.schemas import TriageResult

_TIMEOUT_SECONDS = 10.0


class LLMTriage:
    name = "llm:groq"

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key  # never logged, never included in exceptions
        self._base_url = base_url.rstrip("/")
        self._model = model

    def triage(self, text: str, location: str) -> TriageResult:
        messages = build_messages(text, location)
        raw = retry_call(lambda: self._call(messages))
        return parse_llm_json(raw)

    def _call(self, messages: list[dict[str, str]]) -> str:
        try:
            resp = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            raise RetryableTriageError(f"llm:groq timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise RetryableTriageError(f"llm:groq request error: {exc}") from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise RetryableTriageError(f"llm:groq returned {resp.status_code}")
        if resp.status_code >= 400:
            raise NonRetryableTriageError(
                f"llm:groq returned {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise NonRetryableTriageError(f"llm:groq unexpected response shape: {exc}") from exc
