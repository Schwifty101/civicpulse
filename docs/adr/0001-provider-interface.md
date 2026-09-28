# ADR 0001: TriageProvider interface

## Context

The complaint triage step must be done by "something that reads text and produces a
category, priority and summary." Today that's a keyword rule. Production wants a hosted
LLM (Groq). A fully offline path (Ollama) must exist so the system isn't hard-dependent on
a third-party key. CI must be deterministic — it cannot depend on a live model at all.

Four very different implementations need to be swappable without touching a single line of
`routes/` or `services/`.

## Decision

Define the contract once, in `backend/app/schemas.py` and
`backend/app/providers/triage/base.py`:

```python
class TriageResult(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)

class TriageProvider(Protocol):
    name: str
    def triage(self, text: str, location: str) -> TriageResult: ...
```

Four implementations satisfy it, selected by `TRIAGE_PROVIDER`:

| Provider | File | Use |
|---|---|---|
| `RuleBasedTriage` | `providers/triage/rules.py` | Deterministic keyword classifier. Never raises. Also the fallback target for every other provider. |
| `SimulatedTriage` | `providers/triage/simulated.py` | Seeded, no network, configurable failure injection. What CI pins to. |
| `LLMTriage` | `providers/triage/llm.py` | Groq, OpenAI-compatible `/chat/completions`, called with plain `httpx` (no SDK needed for one JSON POST). |
| `OllamaTriage` | `providers/triage/ollama.py` | Same interface against a local Ollama HTTP API. |

`providers/triage/factory.py` is the only place that knows about `TRIAGE_PROVIDER` — it
returns one `TriageProvider`, stored once on `app.state` at startup. Every route and
service depends on the `TriageProvider` Protocol, never on a concrete class.

`LLMTriage` and `OllamaTriage` share prompt-building and response-parsing
(`providers/triage/prompt.py`) and a retry loop (`providers/triage/base.retry_call`) — the
only thing that differs between "hosted" and "local" is the HTTP call shape, not the
guardrails around it.

## Consequences

- Swapping providers is a one-line env var change (`TRIAGE_PROVIDER=llm`), never a code
  change or a redeploy of anything but config.
- `app/services/triage_service.py` is the ONLY place that knows how to fall back
  (`TriageError` → `RuleBasedTriage`), cache by content hash, or record latency —
  independent of which provider was actually called. Adding a fifth provider later (a
  fine-tuned classifier, per the spec's own framing) means writing one class and touching
  the factory's `match` statement — nothing else.
- The trade-off: the Protocol is intentionally thin (one method, one input shape). It
  can't express provider-specific tuning (e.g. Groq's `response_format` JSON mode) inside
  the interface — that detail lives inside each provider's own `_call()`, which is
  correct: callers shouldn't need to know it exists.
