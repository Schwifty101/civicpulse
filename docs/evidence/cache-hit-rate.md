# Triage content-hash cache hit rate — measured

Measured against the real `LLMTriage` code path (`TRIAGE_PROVIDER=llm`), not `rules` (which
never populates this cache by design — see `docs/TRIAGE.md`).

`GROQ_BASE_URL` pointed at a local stub server (`fake_groq.py`, not committed — a throwaway
test fixture) that speaks Groq's exact `/chat/completions` response shape. This was
necessary because pulling an Ollama model in this sandbox hit repeated
`unexpected EOF` errors against `registry.ollama.ai` (network instability in the sandbox,
not a code issue — see `docs/ENGINEERING-NOTES.md`). The stub exercises the identical
`LLMTriage` → `parse_llm_json` → content-hash cache path a real Groq call would; only the
network hop to the LLM vendor itself is faked.

## Test

5× an identical complaint (`"Burst water main flooding Street 12 since fajr..."`), then 2×
distinct complaints, all `POST /api/complaints`.

## Result — `GET /api/meta/providers`

```json
{
  "active_provider": "llm",
  "triage_cache_hits": 4,
  "triage_cache_lookups": 7,
  "triage_cache_hit_rate": 0.5714
}
```

4 hits / 7 lookups = **57.14%** — exactly the expected 4-of-5 duplicate submissions hitting
the cache (the first of the five is the miss that populates it) plus the 2 genuinely unique
submissions each missing once. `recent_outcomes` latencies confirm the mechanism directly:
the first (miss) call took 127ms (a real HTTP round trip to the stub); every subsequent hit
on the same content hash took 0ms (no HTTP call at all, served straight from Redis).

Full raw response: `docs/evidence/cache-hit-rate-response.json`.
