import json

import httpx
import pytest

from app.providers.triage.base import NonRetryableTriageError, RetryableTriageError
from app.providers.triage.llm import LLMTriage


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or json.dumps(payload or {})

    def json(self):
        return self._payload


def _chat_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _valid_content() -> str:
    return json.dumps(
        {"category": "water", "priority": "high", "summary": "Burst pipe", "confidence": 0.9}
    )


@pytest.fixture()
def provider() -> LLMTriage:
    return LLMTriage(api_key="secret-test-key", base_url="https://fake.groq", model="test-model")


def test_successful_call_returns_triage_result(monkeypatch, provider):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        return FakeResponse(200, _chat_payload(_valid_content()))

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    result = provider.triage("burst pipe", "Street 1")
    assert result.category.value == "water"
    assert len(calls) == 1


def test_malformed_json_is_non_retryable_and_not_retried(monkeypatch, provider):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        return FakeResponse(200, _chat_payload("this is not json at all"))

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    with pytest.raises(NonRetryableTriageError):
        provider.triage("text", "loc")
    assert len(calls) == 1  # malformed output must not be retried


def test_out_of_enum_category_rejected_by_schema(monkeypatch, provider):
    bad = json.dumps(
        {"category": "not_a_real_category", "priority": "high", "summary": "x", "confidence": 0.5}
    )

    def fake_post(url, **kwargs):
        return FakeResponse(200, _chat_payload(bad))

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    with pytest.raises(NonRetryableTriageError):
        provider.triage("text", "loc")


def test_429_retried_then_succeeds(monkeypatch, provider):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return FakeResponse(429, text="rate limited")
        return FakeResponse(200, _chat_payload(_valid_content()))

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    monkeypatch.setattr("app.providers.triage.base.time.sleep", lambda *_: None)

    result = provider.triage("text", "loc")
    assert result.category.value == "water"
    assert len(calls) == 2


def test_400_is_never_retried(monkeypatch, provider):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        return FakeResponse(400, text="bad request")

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    with pytest.raises(NonRetryableTriageError):
        provider.triage("text", "loc")
    assert len(calls) == 1


def test_timeout_exhausts_retries_then_raises(monkeypatch, provider):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    monkeypatch.setattr("app.providers.triage.base.time.sleep", lambda *_: None)

    with pytest.raises(RetryableTriageError):
        provider.triage("text", "loc")
    assert len(calls) == 2  # one try + one retry, per spec


def test_api_key_never_appears_in_exception_text(monkeypatch, provider):
    def fake_post(url, **kwargs):
        return FakeResponse(400, text="bad request")

    monkeypatch.setattr("app.providers.triage.llm.httpx.post", fake_post)
    with pytest.raises(NonRetryableTriageError) as exc_info:
        provider.triage("text", "loc")
    assert "secret-test-key" not in str(exc_info.value)
