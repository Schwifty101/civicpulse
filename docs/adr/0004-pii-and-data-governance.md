# ADR 0004: PII and data governance for the AI triage call

## Context

A citizen complaint routinely contains a name, a street address, sometimes a phone number,
typed straight into the free-text field. `POST /api/complaints` also collects a separate
`reporter_contact` field. When `TRIAGE_PROVIDER=llm`, that text leaves the machine and goes
to Groq's API. Groq's free tier does not carry the same data-handling guarantees as a paid
enterprise tier — see the spec's own framing of Google AI Studio's free tier as a comparable
case: inputs may be used to improve the provider's models. This has to be a documented
engineering decision, not a thing nobody thought about.

## Decision

1. **`reporter_contact` is never sent to any triage provider.** Look at
   `app/services/complaint_service.py::create_complaint` — it calls `triage_complaint(...,
   payload.text, payload.location)`, and `app/providers/triage/prompt.py::build_messages`
   only accepts `text` and `location`. The one field that is unambiguously and only PII
   (a phone number or email a citizen gave to be contacted back) structurally cannot reach
   Groq/Ollama — there is no code path that passes it.

2. **The complaint `text` and `location` are sent as-is, not redacted**, and that is an
   accepted, documented exposure for `TRIAGE_PROVIDER=llm`, not an oversight. Reasons:
   - A regex/NER redaction pass would itself be unreliable (it would miss names it doesn't
     recognise, over-redact street names that look like person names, and add a second
     "trust this heuristic" layer to a system whose entire lesson is "don't trust model
     output blindly" — the same applies to trusting a redaction filter blindly).
   - The complaint text's whole *point* is the location and circumstance ("Street 12, water
     entering ground floors since fajr") — heavy redaction would degrade triage quality on
     the exact fields that matter most for correct categorisation.
   - The system offers a genuinely zero-exposure alternative instead of a fake one:
     `TRIAGE_PROVIDER=ollama` runs a model in-cluster/in-compose. Nothing leaves the
     machine. No key, no network call, no third-party retention policy to reason about.

3. **This is a per-deployment operator decision, not a hardcoded default.** The shipped
   default is `TRIAGE_PROVIDER=rules` (no network call to anywhere, no LLM at all). A
   municipality that cannot accept Groq's free-tier data terms sets `TRIAGE_PROVIDER=ollama`
   and gets identical behaviour (same `TriageProvider` interface, same
   category/priority/summary output shape) with zero data leaving their infrastructure.

4. **The API key itself is never logged.** `LLMTriage.__init__` stores it on the instance,
   never in an exception message (`tests/test_llm_provider.py::test_api_key_never_appears_in_exception_text`
   pins this). It comes from `GROQ_API_KEY`, sourced from `.env` locally (gitignored) and a
   Kubernetes `Secret` in cluster (placeholder-only in the committed manifest).

## Consequences

- A municipality using `llm`/Groq is accepting that complaint text (which may contain
  incidental PII — a name mentioned in passing, "my neighbour Ahmed's pipe") is processed
  by a third party under Groq's free-tier terms. That is a real, named trade-off, not a
  silent one.
- A municipality that cannot accept that trade-off has a first-class, equally-functional
  fallback (`ollama`), not a second-class "sorry, no AI for you" degradation.
- `reporter_contact` — the field with the clearest, least-ambiguous PII — never leaves the
  database regardless of provider choice.
