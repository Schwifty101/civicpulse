# Triage: how a complaint gets a category, priority and summary

## Flow

`POST /api/complaints` → `app/services/complaint_service.create_complaint` →
`app/services/triage_service.triage_complaint`:

1. **Content-hash cache lookup.** `text` is normalised (trimmed, lowercased, whitespace
   collapsed) and SHA-256 hashed. If a result for that hash exists in Redis (24h TTL), it's
   reused — this is the "nine neighbours report the same burst main" case from the spec.
   Only genuine `llm:groq`/`llm:ollama` results are cached (not `rules` — the keyword
   matcher is already instant, caching it buys nothing; not `rules:fallback` — a fallback
   result shouldn't mask the real provider recovering within the 24h window).
2. **Provider call**, with the timeout/retry/fallback machinery living inside the provider
   itself (`LLMTriage`/`OllamaTriage`) — see `docs/adr/0001-provider-interface.md`.
3. **On any `TriageError`**, fall back to `RuleBasedTriage`, log one `WARNING` with the
   complaint's provider name and the exception class (never the exception's full text, to
   avoid ever accidentally logging a key), and record `triaged_by = "rules:fallback"`.
4. **Latency and outcome recorded** to a Redis-backed ring buffer (last 20), shared across
   backend replicas (`LPUSH` + `LTRIM`, not an in-process list) — that's what
   `GET /api/meta/providers` reads.

## Measuring the cache hit rate

`GET /api/meta/providers` returns:

```json
{
  "active_provider": "llm",
  "recent_outcomes": [{"provider": "llm:groq", "latency_ms": 412, "fallback": false, "at": "..."}],
  "triage_cache_hits": 4,
  "triage_cache_lookups": 7,
  "triage_cache_hit_rate": 0.5714
}
```

`triage_cache_hits`/`triage_cache_lookups` are cumulative counters in Redis
(`triage:cache:counters`), incremented on every triage call regardless of outcome.

**Measured, not hypothetical**: the numbers above are a real run — 5× an identical
complaint plus 2 distinct ones through `TRIAGE_PROVIDER=llm`, giving the expected 4 hits
(the 2nd-5th identical submissions) against 7 total lookups. `recent_outcomes`' latencies
confirm the mechanism: the one real miss took 127ms (an actual outbound call), every
subsequent hit on the same content hash took 0ms (served from Redis, no outbound call at
all). Full writeup and raw response: `docs/evidence/cache-hit-rate.md`.

To reproduce: seed a few duplicate complaints with `TRIAGE_PROVIDER=llm` or `ollama` set
(the `rules` default never populates the cache, by design — see above), or run
`load/k6-script.js` against a `TRIAGE_PROVIDER=llm` deployment, which repeats a small pool
of sample texts and will show hits climbing after the first pass.

## Prompt-injection guardrail

`app/providers/triage/prompt.py::build_messages` delimits the citizen's text with
`<<<COMPLAINT>>> ... <<<END>>>` and instructs the model to treat anything inside as data,
never as an instruction to follow. `parse_llm_json` then validates the model's response
against `TriageResult` regardless of what the model claims — an out-of-enum category or an
oversized summary is rejected the same way malformed JSON is (`NonRetryableTriageError`,
one fallback to rules, never a 500). See
`tests/test_prompt.py` and
`tests/test_complaints_routes.py::test_prompt_injection_attempt_still_yields_schema_valid_category`.

## Fallback guarantee

The one test that must never go red:
`tests/test_complaints_routes.py::test_triage_failure_falls_back_to_rules_and_still_returns_201`
— a provider that always raises still yields a `201` with `triaged_by == "rules:fallback"`.
