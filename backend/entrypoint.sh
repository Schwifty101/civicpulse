#!/bin/sh
set -e

alembic upgrade head

# exec replaces this shell with uvicorn, so it becomes PID 1 and receives SIGTERM
# directly — required for graceful shutdown (in-flight requests drain before exit).
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 25
