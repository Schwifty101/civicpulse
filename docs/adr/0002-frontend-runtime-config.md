# 0002 — Frontend Runtime Configuration

## Context

A Vite build bakes every `import.meta.env` value into the static JS bundle at build
time. If the frontend image contains a baked-in absolute backend URL
(`https://api.example.com`), that image is only valid for one environment — dev,
prod, and every k8s overlay would each need their own build, which destroys
build-once-deploy-many for the one artifact (§1.4, §2.1) the whole assignment is
built to demonstrate.

Two documented ways to avoid this: (a) generate `/config.js` from environment
variables at container start and have the SPA read `window.__CONFIG__.apiUrl`, or
(b) have nginx reverse-proxy `/api/*` to the backend so the SPA never needs an
absolute URL at all — every request is same-origin.

## Decision

**(b): nginx reverse proxy.** `frontend/nginx.conf` proxies `location /api/`
to `http://backend:8000`, and the SPA (`src/api/client.ts`) only ever calls
relative paths like `fetch("/api/complaints")`.

`backend` is not an environment variable — it's the literal Service/container
hostname, kept identical across every environment on purpose:
`compose.yaml`'s backend service is named `backend`, and `k8s/base/backend.yaml`'s
Service is also named `backend`. Because the hostname never changes, the same
`nginx.conf`, baked into the same image, works unmodified in dev compose, prod
compose, and every k8s overlay — zero envsubst, zero `/config.js`, zero
per-environment rebuild.

This also means the frontend needs no secrets and no build-time backend
knowledge whatsoever: `docker build` for this image is identical regardless of
where it will run.

## Consequences

- **Simpler than (a).** No entrypoint script generating config at container
  start, no client-side fetch-then-render-config indirection, one fewer moving
  part to get wrong.
- **Couples the image to the hostname `backend`.** Any deployment target must
  name the backend Service/container exactly `backend` on a network the
  frontend container can reach. This is already true of this repo's compose
  and k8s manifests, so the constraint costs nothing here — but it does mean
  option (a) would be the better choice for a frontend meant to be deployed
  independently of a specific backend topology (e.g. shipped as a public SDK
  example pointed at arbitrary customer backends). CivicPulse is not that.
- **nginx must tolerate `backend` not existing yet at container start.**
  `proxy_pass` with a static hostname is resolved once, at nginx config load —
  if `backend` isn't resolvable then, nginx's master process refuses to start
  at all, not just fail the proxied request. We accept this rather than add a
  dynamic-resolver (`resolver` directive + variable `proxy_pass`, resolved
  per-request) because both real deployment targets already guarantee the name
  resolves before frontend starts: `compose.yaml` gives frontend
  `depends_on: backend: condition: service_healthy`, and a Kubernetes
  ClusterIP Service gets a DNS record the moment the Service object exists,
  independent of whether any backend pod is ready yet. Adding request-time
  resolution would only guard against a scenario (frontend running with no
  Service/container named `backend` anywhere on its network) that doesn't
  occur in this project's two real targets — the added complexity would be
  solving a problem we don't have.
- **No absolute backend URL ever appears in the bundle or Docker image** —
  confirmed by grepping the built `dist/` output for `http://` / `https://`
  during frontend verification; the only URLs are relative `/api/...` calls.
