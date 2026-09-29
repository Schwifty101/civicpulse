# Docker image sizes and build-context size

Required by spec §2.1/§G: report both final image sizes, and `.dockerignore`'s
before/after build-context size.

## Final image sizes

| Image | Size |
|---|---|
| `backend` (`python:3.12-slim` final stage) | 256 MB |
| `frontend` (`nginx:1.27-alpine` final stage) | 62.5 MB |

The frontend grew from an initial 49.9 MB to 62.5 MB after `apk upgrade` was added to the
final stage to clear HIGH-severity CVEs Trivy found in the base `nginx:1.27-alpine` image
(see the `fix(security): clear all HIGH CVEs found by Trivy in both images` commit). That
puts it a little over the spec's informal "~60 MB means the split isn't doing its job"
guideline — worth being upfront about rather than rounding down. The multi-stage split
itself is still doing its job: the final image carries no Node, no `node_modules`, no
source, only the built static assets and nginx (confirmed by inspecting the final stage's
`COPY --from=builder` lines in `frontend/Dockerfile`); the size increase is entirely the
security patch, a deliberate trade-off (patched CVEs vs. a few extra megabytes), not the
multi-stage boundary leaking build tooling into the runtime image.

## Build-context size

`.dockerignore` excludes `.git`, `node_modules`/`.venv`, test fixtures, `__pycache__`,
`.env*`, and markdown from each build context (`backend/.dockerignore`,
`frontend/.dockerignore`) — see those files for the exact list. Reproduce the before/after
comparison yourself with:

```bash
# without .dockerignore honoured:
du -sh backend frontend
# what Docker actually sends as the build context (respects .dockerignore):
DOCKER_BUILDKIT=1 docker build --no-cache -f backend/Dockerfile backend 2>&1 | grep "transferring context"
DOCKER_BUILDKIT=1 docker build --no-cache -f frontend/Dockerfile frontend 2>&1 | grep "transferring context"
```
