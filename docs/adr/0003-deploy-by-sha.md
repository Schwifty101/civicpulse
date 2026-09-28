# ADR 0003: Deploy by commit SHA, never `:latest`

## Context

`:latest` is a mutable pointer. Two people who both "deploy latest" a week apart can be
running different code with no way to tell from the tag alone. "What is production
running?" needs a one-word answer pasteable into `git show`. `:latest` cannot answer that
question; a commit SHA always can.

## Decision

- `cd.yml`'s `build-push` job tags every image with `${{ github.sha }}` (and, separately,
  also pushes `:latest` — pushing it is allowed, per the spec; it is never what gets
  *deployed*).
- `deploy-k8s` never applies the base manifests directly. It runs
  `kustomize edit set image backend=...:$SHA frontend=...:$SHA` inside
  `k8s/overlays/prod/` immediately before `kubectl apply -k`, so the exact SHA that was
  just built and tested is the exact SHA that reaches the cluster.
- `k8s/base/backend.yaml` and `k8s/base/frontend.yaml` reference a placeholder tag
  (`:dev`) that is never meant to be applied as-is in prod — `overlays/prod/kustomization.yaml`
  says so explicitly in a comment, and `scripts/check_submission.py` fails the build if any
  tracked manifest still says `:latest`.
- `compose.prod.yaml` takes the same shape: `image: ${REGISTRY}/backend:${IMAGE_TAG}` with
  `IMAGE_TAG` supplied at deploy time (a real SHA), never hardcoded.
- Rollback has two forms, both traceable to a SHA: `kubectl rollout undo` (fast — walks
  back to the previous ReplicaSet, whatever SHA that was) and re-running `kustomize edit
  set image` with the previous known-good SHA plus `kubectl apply -k` again (slower,
  auditable, the one you use once the fire is out and you want the manifest in git to match
  what's running).

## Consequences

- Every running pod's image tag IS the answer to "what commit is this." `kubectl get
  deployment backend -n civicpulse -o jsonpath='{.spec.template.spec.containers[0].image}'`
  gives a SHA you can `git show` directly.
- The cost: one extra `kustomize edit` step in CI instead of a static manifest. Worth it —
  a static manifest with a real SHA baked in would need a commit (and a PR, and CI) just to
  bump a tag, which is exactly the ceremony immutable-reference deploys are supposed to
  avoid at the *manifest* layer while still keeping it at the *registry* layer.
