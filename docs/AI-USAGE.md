# AI usage disclosure

Per course policy §5.5: honest, specific attribution carries no penalty; presenting
AI-generated work as unaided original work does.

## Tool

**Claude Code** (Anthropic), running Claude Sonnet 5, in an agentic coding session
directed by Soban Ahmad.

## What the tool did

Essentially the entire implementation in this repository — backend (FastAPI, all four
layers, the AI triage providers, Alembic migrations, the 58-test suite), frontend (React/
Vite/TypeScript, Vitest tests), Docker (both multi-stage Dockerfiles, `compose.yaml`/
`compose.prod.yaml`), Kubernetes manifests (`k8s/`), CI/CD workflows (`.github/workflows/`),
and this documentation set (ADRs, RUNBOOK, ENGINEERING-NOTES, TRIAGE) — was written by
Claude Code in a single directed session, working from the assignment specification
supplied in full by the student.

## What the human did

- Supplied the complete assignment specification as the working brief.
- Provided GitHub, Docker, and Kubernetes access (repository creation, local Docker Desktop
  cluster) that the agent used directly.
- Made the decisions the agent surfaced as genuinely open (not derivable from the spec
  alone): the GitHub repository name/visibility (`Schwifty101/civicpulse`, public), and the
  AI-layer shipping default (no live Groq/Gemini key was present in the working
  environment, so `TRIAGE_PROVIDER=rules` ships as the zero-setup default with the Groq/
  Ollama code paths fully implemented and tested but not exercised against a live key).
- Caught and corrected two in-flight mistakes during the session: a real Groq API key that
  briefly landed in `.env.example` (moved out before any commit — see the git history,
  which contains no secret at any point) and a `*.md` line accidentally added to
  `.gitignore` that would have silently blocked every required doc from being committed.

## What was changed afterward and why

The agent's own verification loop (run tests, run the linter/type-checker, build the actual
Docker image, run it, hit its endpoints, check `docker exec ... whoami`, test graceful
shutdown) caught and fixed several real bugs before they reached a commit: a `Retry-After`
header silently dropped by FastAPI's exception-handling path (headers set on the injected
`Response` object are discarded when an `HTTPException` is raised instead — fixed by using
`HTTPException(headers=...)`), and a duplicate-`CREATE TYPE` bug in the initial Alembic
migration (SQLAlchemy's enum `before_create` hook re-creates a Postgres enum type that was
already explicitly created, unless `create_type=False` is set on the column's type
reference — fixed by passing `create_type=False` on the table-embedded enum). Both are
documented at the point of the fix in commit history rather than summarized further here.

## Viva readiness

Per §5.4, the individual mark is a multiplier based on the ability to explain and modify
this code live, regardless of who typed it. The student is expected to be able to walk
through any file in this repository — the four-layer backend split, the state machine, the
triage fallback path, the network segmentation, the HPA/VPA interaction — and defend the
design choices recorded in the ADRs, not merely describe what the code does.
