#!/usr/bin/env python3
"""A lint, not a grader (per the spec, §5.8): catches the mechanical failures behind most
of the automatic deductions in §5.3. A clean run does not guarantee a good mark; a dirty
run nearly guarantees a bad one. Stdlib only — run with any python3, no deps needed.

Usage: python scripts/check_submission.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read(path: str) -> str:
    p = ROOT / path
    return p.read_text() if p.exists() else ""


def git_tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0


# --- 1. Secrets ---
if git_tracked(".env"):
    fail(".env is tracked by git — rotate any real credential in it immediately (-20).")

gitignore = read(".gitignore")
if ".env" not in gitignore:
    fail(".gitignore does not exclude .env.")

for manifest in ["k8s/base/secret.yaml"]:
    content = read(manifest)
    for line in content.splitlines():
        m = re.match(r"\s*(\w+):\s*([A-Za-z0-9+/=]{20,})\s*$", line)
        if m and "changeme" not in m.group(2).lower():
            import base64
            try:
                decoded = base64.b64decode(m.group(2) + "===").decode(errors="replace")
            except Exception:
                decoded = ""
            if "changeme" not in decoded.lower() and decoded:
                warn(f"{manifest}: '{m.group(1)}' does not look like a placeholder — verify it isn't a real secret.")

# --- 2. Unpinned base images ---
IMAGE_LINE = re.compile(r"image:\s*([\w./-]+)(:[\w.-]+)?")
for f in ["compose.yaml", "compose.prod.yaml", *[str(p.relative_to(ROOT)) for p in (ROOT / "k8s").rglob("*.yaml")]]:
    for line in read(f).splitlines():
        if line.strip().startswith("#"):  # comments aren't manifest content
            continue
        m = IMAGE_LINE.search(line)
        if not m:
            continue
        image, tag = m.group(1), m.group(2)
        if "${" in image:  # variable-substituted image (compose.prod backend/frontend) — fine
            continue
        if tag is None:
            fail(f"{f}: image '{image}' has no tag pinned.")
        elif tag == ":latest":
            fail(f"{f}: image '{image}' is pinned to :latest, not a real version.")

# --- 3. localhost for service-to-service ---
# A container healthchecking its own listening port via localhost (self-check, not
# service-to-service) and CORS_ORIGINS (a browser-facing allowed-origin list, not a
# service address) are both legitimate uses — only flag other occurrences.
for f in ["compose.yaml", "compose.prod.yaml"]:
    for line in read(f).splitlines():
        if "CMD" in line or "CORS_ORIGINS" in line:
            continue
        if re.search(r"localhost|127\.0\.0\.1", line):
            fail(f"{f}: references localhost/127.0.0.1 — services must address each other by name. ({line.strip()})")

# --- 4. Published DB/cache ports in prod ---
prod_compose = read("compose.prod.yaml")
db_block_match = re.search(r"database:.*?(?=\n  \w+:|\Z)", prod_compose, re.DOTALL)
cache_block_match = re.search(r"cache:.*?(?=\n  \w+:|\Z)", prod_compose, re.DOTALL)
for name, block in [("database", db_block_match), ("cache", cache_block_match)]:
    if block and re.search(r"^\s*ports:", block.group(0), re.MULTILINE):
        fail(f"compose.prod.yaml: '{name}' service publishes a port — must not in prod.")

# --- 5. NodePort/LoadBalancer on database/cache in k8s ---
for f in ["k8s/base/postgres.yaml", "k8s/base/redis.yaml"]:
    content = read(f)
    if "NodePort" in content or "LoadBalancer" in content:
        fail(f"{f}: database/cache Service must be ClusterIP, not NodePort/LoadBalancer.")

# --- 6. Postgres must be a StatefulSet with a PVC ---
pg = read("k8s/base/postgres.yaml")
if "kind: Deployment" in pg and "postgres" in pg:
    fail("k8s/base/postgres.yaml: Postgres must be a StatefulSet, not a Deployment.")
if "volumeClaimTemplates" not in pg:
    fail("k8s/base/postgres.yaml: missing volumeClaimTemplates (no PVC for Postgres).")

# --- 7. needs: gating on publish/deploy jobs ---
cd_workflow = read(".github/workflows/cd.yml")
for job in ["build-push", "deploy-k8s"]:
    block = re.search(rf"^  {job}:\n(.*?)(?=^  \w[\w-]*:\n|\Z)", cd_workflow, re.DOTALL | re.MULTILINE)
    if not block or "needs:" not in block.group(1):
        fail(f".github/workflows/cd.yml: job '{job}' is not gated by needs:.")

# --- 8. Required docs present ---
required_docs = [
    "README.md",
    "docs/RUNBOOK.md",
    "docs/AI-USAGE.md",
    "docs/TRIAGE.md",
    "docs/ENGINEERING-NOTES.md",
    "docs/adr/0001-provider-interface.md",
    "docs/adr/0002-frontend-runtime-config.md",
    "docs/adr/0003-deploy-by-sha.md",
    "docs/adr/0004-pii-and-data-governance.md",
]
for doc in required_docs:
    if not (ROOT / doc).exists():
        fail(f"Missing required doc: {doc}")

# --- 9. README has a real quickstart ---
readme = read("README.md")
if "docker compose up" not in readme:
    fail("README.md: no 'docker compose up' quickstart command found.")

# --- 10. Currently on main with uncommitted work? (soft check) ---
branch = subprocess.run(
    ["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True
).stdout.strip()
if branch == "main":
    warn("You are on 'main'. Do your work on 'dev' or a feature branch and open a PR.")

# --- Report ---
print(f"\ncheck_submission.py — {len(failures)} failure(s), {len(warnings)} warning(s)\n")
for w in warnings:
    print(f"  WARN  {w}")
for f in failures:
    print(f"  FAIL  {f}")
if not failures and not warnings:
    print("  Clean. (Still just a lint — see §5.8.)")

sys.exit(1 if failures else 0)
