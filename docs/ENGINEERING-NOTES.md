# Engineering notes

Answers to the eight required questions (§5.2), with references to this repository's own
files and lines.

## 1. Three things that differ between laptop and CI runner, and the exact line that freezes each

1. **OS/CPU architecture.** This was built on macOS/arm64; GitHub's `ubuntu-latest` runners
   are Linux/amd64. Frozen by `backend/Dockerfile:2` (`FROM python:3.12-slim`) and
   `frontend/Dockerfile:2` (`FROM node:22-alpine`) — both are multi-arch manifest tags, so
   the exact same Dockerfile produces a correct image on either host, and the app only ever
   runs inside that image, never against the host's own Python/Node.
2. **Interpreter/runtime version.** The host had three Python versions installed
   (3.11/3.13/3.14) during this build, none of them 3.12. Frozen twice: once for the app
   itself (`backend/Dockerfile:2,20`, `python:3.12-slim`), and once for CI's own toolchain
   (`.github/workflows/ci.yml:15`, `env.PYTHON_VERSION: "3.12"`, consumed by
   `actions/setup-python@v5`) — so the CI runner's ambient Python is irrelevant; the pinned
   version is what actually executes.
3. **Pre-existing local services.** The single most disruptive difference, and the literal
   cause of the failure in Q8: a laptop can have a process already bound to a port a
   container also wants (here, a native Postgres.app on `127.0.0.1:5432`, more specific than
   Docker's own wildcard bind and therefore winning routing priority). A CI runner has no
   such history — `.github/workflows/ci.yml:44-58` defines Postgres/Redis as `services:`
   containers that exist for exactly the duration of that one job, on a clean runner, so
   this entire class of bug structurally cannot occur in CI. (It can still occur on a
   contributor's laptop, which is why `compose.yaml` deliberately does not publish
   Postgres/Redis ports at all — see `docs/RUNBOOK.md`.)

## 2. Where this pipeline sits on the CI/CD maturity ladder

This pipeline is **continuous delivery to a single environment, not continuous deployment**:
every push to `main` runs the full test suite again
(`.github/workflows/cd.yml` `test` job), builds and pushes immutable, SHA-tagged images
(`build-push`, gated by `needs: test`), and *automatically* applies them to a cluster
(`deploy-k8s`, gated by `needs: build-push`) — no manual "click to deploy" step exists once
code lands on `main`. That already clears the classic CD bar (automated build → test → scan
→ deploy on every merge, §3.4's `needs:` chain enforcing that a failing test cannot reach a
cluster).

It stops short of the next rung the spec itself names in its bonus section: **progressive
delivery with automatic, metrics-driven rollback** (Argo CD/Flux reconciling from git,
canary or blue/green traffic shifting, automatic rollback on an SLO breach rather than a
human running `kubectl rollout undo`). Right now, `deploy-k8s` does a single all-at-once
`kubectl apply -k` to an ephemeral CI cluster and smoke-tests it — a real production rollout
uses the same manifests but there is no controller continuously reconciling desired state
against a git source of truth, and no automated rollback trigger beyond the rolling-update
`maxUnavailable: 0` safety net (`k8s/base/backend.yaml`).

What the next rung buys: today, a bad deploy is caught by either the CI smoke test (before
traffic) or a human watching dashboards (after). GitOps + canary would catch a bad deploy
*during* rollout, automatically, from live metrics, and roll back without a human in the
loop — the difference between "we tested it" and "we're watching it live and can undo it in
seconds without anyone paged."

## 3. The exact line guaranteeing build-once-deploy-many, and what breaks without it

`frontend/nginx.conf:20` — `proxy_pass http://backend:8000;` — combined with the backend's
Service being named literally `backend` in both `compose.yaml:84` (service key) and
`k8s/base/backend.yaml` (`metadata.name: backend`). The frontend image never has an
absolute API URL baked into it anywhere; it always fetches relative `/api/...` paths, and
whichever environment it's running in resolves `backend` via that environment's own DNS
(Docker's embedded DNS in Compose, CoreDNS in Kubernetes). The exact same built image —
same digest — runs correctly in dev Compose, prod Compose, and every Kubernetes overlay.

Without it: Vite bakes `import.meta.env.*` values into the built static JS at `npm run
build` time (that's just how Vite works, not a mistake to fix). An absolute
`VITE_API_BASE_URL` baked in at build time would mean a dev build's JS literally contains
`http://localhost:8000`, permanently wrong the moment that same image runs anywhere else —
a different image per environment, i.e. exactly the build-once-deploy-many violation the
spec calls out. See `docs/adr/0002-frontend-runtime-config.md` for the full reasoning.

## 4. What "correct" means for a probabilistic component, and how CI stays deterministic

With `TRIAGE_PROVIDER=llm`, "correct" cannot mean "returns the exact category a human would
pick" — the same input can legitimately get `water`/`high` from one call and `water`/`normal`
from the next, and that's not a bug. "Correct" here means **schema-valid and safe**: the
response is one of the six defined categories, one of the three priorities, a summary
≤140 characters, and a confidence in `[0,1]` — enforced by re-validating every model
response against `TriageResult` regardless of what the model returned
(`backend/app/providers/triage/prompt.py::parse_llm_json`), never by trusting the model's
own claim about its output shape. "Correct" also means the system's *behaviour* around the
uncertainty is right: a timeout is retried once with jitter and nothing else
(`backend/app/providers/triage/base.py::retry_call`), a malformed or out-of-enum response is
never retried and always falls back (`NonRetryableTriageError`), and a citizen never sees a
500 because Groq had a bad minute.

CI stays green on every run because it never calls a real model at all: `TRIAGE_PROVIDER`
defaults to `simulated` in `backend/tests/conftest.py:10`, and `SimulatedTriage`
(`backend/app/providers/triage/simulated.py`) is a pure function of the input text's SHA-256
hash — same input, same output, forever, with zero network calls. The one test that must
never flake or go red — a provider that always raises still yields `201` with
`triaged_by == "rules:fallback"` — is
`backend/tests/test_complaints_routes.py::test_triage_failure_falls_back_to_rules_and_still_returns_201`,
using a small `AlwaysFailsProvider` test double injected via FastAPI's
`dependency_overrides`, never a `time.sleep()` or a real retry against anything live.

## 5. HPA lag: how many seconds between offered load rising and replicas rising

Measured in this session against a local k3d cluster (`k3d cluster create civicpulse`),
`metrics-server` installed with `--kubelet-insecure-tls` (k3d's kubelet certs aren't
otherwise trusted by metrics-server's default verification), and `load/k6-script.js`
(shortened stages for a laptop-scale run) driven straight at the `backend` Service via
`kubectl port-forward`. Raw `kubectl get hpa -w` output is in `docs/evidence/hpa-watch.log`;
the replicas-vs-load chart is `docs/evidence/hpa-scaling-chart.png`.

Where the lag comes from, in order:
1. **Metrics propagation.** `metrics-server` scrapes kubelets on a fixed interval (default
   15s) and the HPA controller's own sync loop polls the metrics API on its own interval
   (default 15s) — CPU usage rising on a pod doesn't reach the HPA's decision loop
   instantly; it's a report, not a push.
2. **The decision itself is fast.** `k8s/base/hpa.yaml`'s `scaleUp.stabilizationWindowSeconds:
   0` (line ~24) means the HPA acts on the very first over-threshold reading it sees — no
   debounce window on the way up (only `scaleDown` waits, 300s, deliberately, to not flap).
3. **New pod scheduling + image pull + startup dominate the tail.** A freshly-scheduled
   backend pod runs `wait-for-postgres` (an `initContainer`, `k8s/base/backend.yaml`) then
   `alembic upgrade head` then boots uvicorn, and only then does `startupProbe`
   (`failureThreshold: 30, periodSeconds: 2` — up to 60s of grace) let it receive traffic at
   all. On a cluster where the image is already resident (as it is once imported into k3d),
   this step is seconds, not the full 60s budget — but it's real, non-zero time in which
   offered load has already risen while capacity has not yet.

Net: the gap between "load crosses the CPU threshold" and "a new pod is `Ready` and taking
traffic" is dominated by (metrics scrape + HPA sync ≈ up to 30s) + (pod schedule + startup
probe settle, single-digit seconds to ~60s worst case). That lag is exactly why autoscaling
is a capacity *response*, not a capacity *plan* — a burst that arrives faster than ~30-90s
will be under-served by definition, no matter how aggressively `scaleUp` is tuned, because
the pod that would serve it doesn't exist yet.

## 6. Why VPA is in Off mode, and the failure mode of Auto alongside this HPA

`k8s/base/vpa.yaml`: `updatePolicy.updateMode: "Off"` — recommend only, never evict or
mutate a running pod's resources.

The HPA (`k8s/base/hpa.yaml`) scales replica *count* on CPU utilization, computed as
`usage ÷ request` (`k8s/base/backend.yaml`'s `resources.requests.cpu: 100m`, comment on that
line). If VPA ran in `Auto` mode on the same Deployment, it would periodically rewrite that
same `requests.cpu` based on observed usage. The two controllers would then be reading and
writing the same signal in a loop: VPA raises the CPU request because usage has been high →
the SAME usage divided by a now-larger request computes as a LOWER utilization percentage →
the HPA sees headroom and scales the replica count back down → each remaining pod now
carries more of the traffic → per-pod usage rises again → VPA raises the request again.
Neither controller is malfunctioning; they're both correctly reacting to a signal the other
one just changed. Recommender mode plus a human in the loop — read the recommendation,
decide, commit a manifest change — is the documented industrial pattern specifically because
it breaks that loop without needing either controller to know the other exists.

## 7. Where the `internal: true` network leaves the service that calls a hosted LLM

`compose.yaml`'s `internal` network (`internal: true`, no route to the outside world) holds
`database` and `cache` only. `backend` is deliberately on *both* networks
(`compose.yaml:84`, `networks: [edge, internal]`) — `edge` is a normal bridge network with
Docker's default NAT internet access, so backend can reach `https://api.groq.com` while
Postgres/Redis structurally cannot reach anything outside the compose stack at all. The
resolution is: **the segmentation boundary is "internet-facing vs. internet-capable," not
"has an outbound route vs. doesn't"** — `frontend` (the actually internet-facing, most
likely to be compromised component) is on `edge` only and can reach neither the data layer
nor, for that matter, does it need to reach Groq itself (only `backend` calls the LLM). The
optional `ollama` service makes the same trade-off explicitly for the same reason — it needs
outbound internet exactly once, to pull its model — and is commented as such at
`compose.yaml`'s `ollama:` service definition.

## 8. The failure

**Symptoms:** every backend integration test failed identically —
`sqlalchemy.exc.OperationalError: ... FATAL: role "civicpulse" does not exist` — when
connecting to a throwaway `postgres:16-alpine` container over `127.0.0.1:5432`, despite
`docker logs` on that exact container clearly showing its entrypoint had run `CREATE
DATABASE` and the role existed (confirmed directly via
`docker exec cp-test-pg psql -U civicpulse -d civicpulse -c "select current_user;"`, which
succeeded).

**What I wrongly believed first:** that the official `postgres` image's `POSTGRES_USER`
entrypoint logic had failed silently, or that `psycopg`/SQLAlchemy's connection string was
malformed. Both were wrong; the container was fine.

**The command that told the truth:** `lsof -nP -iTCP:5432 -sTCP:LISTEN`, which showed a
long-running native **Postgres.app** process already bound to `127.0.0.1:5432` and
`[::1]:5432` — a more specific bind than Docker's own `*:5432` wildcard forward for the same
port, so the OS routed every "localhost:5432" connection to the *wrong* Postgres entirely,
one that had never heard of a `civicpulse` role. Every symptom was real and every belief
about the container was correct; the container was simply never being asked.

**Fix:** remap the throwaway container to a non-conflicting host port (`55432`), which
immediately surfaced a second, unrelated bug the first one had been masking: Alembic's
`op.create_table(...)` re-triggers `CREATE TYPE` for any `postgresql.ENUM` column that
doesn't explicitly set `create_type=False`, even after that type was already created
explicitly earlier in the same migration — SQLAlchemy's enum `before_create` hook fires on
table creation regardless. Fixed at
`backend/alembic/versions/0001_initial_schema.py:35-43`. Both fixes are one apiece; finding
them required treating "the error message" and "the actual root cause" as two different
things, twice in a row.
