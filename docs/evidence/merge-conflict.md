# Deliberate merge conflict — evidence

Two branches, both off `dev` at the same commit, both editing `.env.example`'s
`RATE_LIMIT_PER_MINUTE` line:

- `feature/rate-limit-relaxed` (commit `ad62e8b`) — sets it to `30`.
- `feature/rate-limit-strict` (commit `a96927d`) — sets it to `15`.

Merged both into `integration/conflict-demo`: the first merge fast-forwarded cleanly, the
second produced a real conflict —

```
$ git merge feature/rate-limit-strict --no-edit
Auto-merging .env.example
CONFLICT (content): Merge conflict in .env.example
Automatic merge failed; fix conflicts and then commit the result.
```

Raw conflict markers, as they appeared in the working tree (`merge-conflict-markers.txt` in
this directory):

```
TRIAGE_PROVIDER=rules
LOG_LEVEL=INFO
<<<<<<< HEAD
RATE_LIMIT_PER_MINUTE=30
=======
RATE_LIMIT_PER_MINUTE=15
>>>>>>> feature/rate-limit-strict
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

## Resolution: 15/min wins

`feature/rate-limit-relaxed` optimized for a human not seeing a 429 while manually
clicking through the Submit form during a demo. `feature/rate-limit-strict` optimized for
the 429 + `Retry-After` path actually being reachable inside a short demo/viva window,
since that's graded behavior (spec §2.4 Job 2), and Groq's real free tier is only tens of
requests/minute — 15 is closer to representative production headroom than 30 was. 15/min
won because a rate limiter that's never actually observed tripping is a weaker
demonstration than one an evaluator can trigger in a few seconds of clicking Submit
repeatedly; the manual-testing friction the relaxed branch was solving for is better solved
by using `TRIAGE_PROVIDER=rules` (no external quota to protect, so the limiter mattering
less in practice at normal interactive speed) than by weakening the default everyone else
inherits.

Resolved and committed at `616e74d` (`integration/conflict-demo`, fast-forward-merged into
`dev`). Branches kept on the remote for inspection:
[`feature/rate-limit-relaxed`](https://github.com/Schwifty101/civicpulse/tree/feature/rate-limit-relaxed),
[`feature/rate-limit-strict`](https://github.com/Schwifty101/civicpulse/tree/feature/rate-limit-strict),
[`integration/conflict-demo`](https://github.com/Schwifty101/civicpulse/tree/integration/conflict-demo).
