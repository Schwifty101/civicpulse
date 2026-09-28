# Evidence the merge gate actually works — red check blocks the merge, then green

Required by spec §3.4: "a PR with a deliberately failing test, screenshot of the red
check and the blocked merge button, fixed in the same PR, screenshot of green."

## Status: not yet captured

This one is honestly incomplete, not staged. An attempt to build it in this session
(add a deliberately-failing test, commit, push, observe red, then push a fix) was
blocked at the very first step: this environment's git-push permission classifier
refuses `git push` on this branch outright, so no such commit ever actually reached
git history here — check `git log -- backend/tests/` yourself, there is no trace of
one. Writing this file to claim otherwise would be exactly the kind of thing this
spec is designed to catch, so it doesn't claim that.

## How to actually produce it (a few minutes, needs a real push)

```bash
git checkout -b ci-gate-demo origin/main
# add one small, obviously-labelled failing test, e.g.:
cat > backend/tests/test_ci_gate_evidence.py <<'PY'
def test_deliberately_failing_check_for_ci_gate_evidence() -> None:
    assert False, "intentional failure — proves ci.yml blocks a red required check"
PY
git add backend/tests/test_ci_gate_evidence.py
git commit -m "test: deliberately failing check for CI gate evidence"
git push -u origin ci-gate-demo
# open a PR (ci-gate-demo -> main) on GitHub, wait ~1 min for ci.yml, then screenshot:
#   - the red X on a required check (e.g. test-backend)
#   - the merge button showing "Merging is blocked"
git rm backend/tests/test_ci_gate_evidence.py
git commit -m "fix: remove the deliberately failing test"
git push
# wait for ci.yml again, screenshot the green check + enabled merge button,
# then merge (or close) this demo PR and delete the branch.
```

Save both screenshots into this directory (e.g. `ci-gate-red.jpg`, `ci-gate-green.jpg`)
and link them from the README's evidence table once captured.
