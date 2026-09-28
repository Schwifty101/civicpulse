# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Dependencies before source: this layer only invalidates when pyproject.toml changes.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip uninstall -y pip setuptools wheel \
    && rm -rf /opt/venv/lib/python3.12/site-packages/pip \
              /opt/venv/lib/python3.12/site-packages/pip-*.dist-info \
              /opt/venv/lib/python3.12/site-packages/setuptools* \
              /opt/venv/lib/python3.12/site-packages/pkg_resources \
              /opt/venv/lib/python3.12/site-packages/_distutils_hack \
              /opt/venv/bin/pip*
    # pip vendors its own (outdated) copy of msgpack, and the venv's default setuptools
    # from `python -m venv` is old — neither is needed at runtime (uvicorn/alembic don't
    # import pip or setuptools), so delete both rather than try to patch pip's internals.

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts


FROM python:3.12-slim

# The base image's system-level pip/setuptools (outside the venv, never invoked at
# runtime — the app runs entirely from /opt/venv) carries HIGH CVEs in old setuptools and
# in msgpack, which pip vendors internally. Nothing in this image ever calls system pip,
# so delete it rather than patch it — Trivy scans the filesystem, not what's reachable.
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip* \
           /usr/local/lib/python3.12/site-packages/setuptools* \
           /usr/local/lib/python3.12/site-packages/pkg_resources \
           /usr/local/lib/python3.12/site-packages/_distutils_hack \
           /usr/local/bin/pip*

RUN groupadd --system civicpulse && useradd --system --gid civicpulse civicpulse

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh && chown -R civicpulse:civicpulse /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER civicpulse
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://localhost:8000/health', timeout=3).status==200 else 1)"]

CMD ["./entrypoint.sh"]
