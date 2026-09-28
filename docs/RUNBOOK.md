# Runbook

## Deploy — local Docker Compose

```bash
cp .env.example .env         # edit if you want real Groq/Ollama values; safe defaults ship
docker compose up -d --build
curl http://localhost:8000/ready
docker compose exec backend python -m scripts.seed   # idempotent — safe to re-run
```

Frontend: http://localhost:8080. Backend docs: http://localhost:8000/docs.

Optional offline LLM path (pulls ~800MB the first time):
```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull llama3.2:1b
# then set TRIAGE_PROVIDER=ollama in .env and restart the backend
```

## Deploy — Kubernetes (local k3d/kind, or Docker Desktop's built-in cluster)

```bash
# Build images locally and load them into the cluster (dev overlay expects civicpulse-backend:dev etc.)
docker build -t civicpulse-backend:dev backend/
docker build -t civicpulse-frontend:dev frontend/
# k3d: k3d image import civicpulse-backend:dev civicpulse-frontend:dev -c <cluster-name>
# kind: kind load docker-image civicpulse-backend:dev civicpulse-frontend:dev
# Docker Desktop's own cluster: no import needed, it shares the local image daemon.

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/kind/deploy.yaml
kubectl apply -k k8s/overlays/dev
kubectl -n civicpulse rollout status deployment/backend
kubectl -n civicpulse rollout status deployment/frontend
echo "127.0.0.1 civicpulse.local" | sudo tee -a /etc/hosts   # once
kubectl -n civicpulse port-forward svc/frontend 8080:80 &    # or use the Ingress controller's own port
curl -H "Host: civicpulse.local" http://localhost:8080/api/health
```

Prod overlay (`k8s/overlays/prod`) is applied the same way by `cd.yml` against a real SHA
tag — see `docs/adr/0003-deploy-by-sha.md`. Don't apply it locally with the placeholder tag.

### Autoscaling demo

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n civicpulse get hpa -w &            # capture this output — required deliverable
k6 run -e BASE_URL=http://civicpulse.local load/k6-script.js
```

VPA (recommender only, `updateMode: "Off"` — see `docs/ENGINEERING-NOTES.md` Q6):
```bash
kubectl -n civicpulse describe vpa backend-vpa   # commit the Target/Lower/Upper bounds you see
```

## Roll back

**Fast, imperative — the 3am answer:**
```bash
kubectl -n civicpulse rollout undo deployment/backend
```

**Declarative, auditable — the correct answer once the fire is out:**
```bash
cd k8s/overlays/prod
kustomize edit set image \
  ghcr.io/schwifty101/civicpulse/backend=ghcr.io/schwifty101/civicpulse/backend:<previous-good-sha>
kubectl apply -k .
git add k8s/overlays/prod/kustomization.yaml
git commit -m "fix: roll back backend to <sha> — <why>"
```
Use imperative rollback to stop the bleeding immediately; follow up with the declarative
form so the manifest in git matches what's actually running (otherwise the next `kubectl
apply -k` silently re-deploys the broken version).

Docker Compose rollback is simpler — nothing to undo declaratively, just redeploy the
previous tag:
```bash
IMAGE_TAG=<previous-good-sha> docker compose -f compose.prod.yaml up -d
```

## Read logs

All logs are structured JSON on stdout (never a file — the container filesystem is
ephemeral). Every line carries `request_id`, propagated from the `X-Request-ID` header
(generated if the caller didn't send one) — grep by it to follow one request across every
log line it produced:

```bash
docker compose logs -f backend | grep '"request_id": "<id>"'
kubectl -n civicpulse logs -l app=backend -f --prefix
```

Triage fallbacks log a single `WARNING` with the complaint id, provider, and error class
(never the raw exception text, to avoid ever leaking a key):
```bash
kubectl -n civicpulse logs -l app=backend | grep '"message": "triage fallback'
```

## When triage starts failing

1. Check `GET /api/meta/providers` — `recent_outcomes` shows the last 20 calls with
   `fallback: true/false` and latency. If everything is `rules:fallback`, the configured
   provider (Groq/Ollama) is down, rate-limited, or misconfigured — not the backend itself.
2. Check the `civicpulse_triage_fallback_total` counter on `/metrics` — a sudden step
   change pinpoints when it started.
3. If `TRIAGE_PROVIDER=llm`: check Groq's status page and your key's rate limit (the free
   tier is tens of requests/minute — a burst of duplicate complaints without the content-hash
   cache warm can exhaust it; the rate limiter on `POST /api/complaints` protects the quota,
   but doesn't eliminate this).
4. Nothing to page anyone over: the fallback to `RuleBasedTriage` means citizens still get a
   201 with a (less precise) category/priority — see
   `tests/test_complaints_routes.py::test_triage_failure_falls_back_to_rules_and_still_returns_201`.
   This is the one behaviour in the whole system that must never regress.
5. Recovery is automatic — the next successful call to the configured provider resumes
   normal `triaged_by` values with no restart needed.

## Secrets

Never in a committed file, ever, even base64-encoded (base64 is encoding, not encryption —
`k8s/base/secret.yaml` ships placeholders only). Set real values imperatively:

```bash
kubectl -n civicpulse create secret generic backend-secret \
  --from-literal=POSTGRES_PASSWORD='<real password>' \
  --from-literal=GROQ_API_KEY='<real key>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

In CI, secrets come from GitHub Secrets (`GITHUB_TOKEN` for GHCR, scoped to
`packages: write` only) — never a personal account password.
