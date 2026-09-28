import os
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL_OVERRIDE",
    "postgresql+psycopg://civicpulse:civicpulse@localhost:5432/civicpulse",
)
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("TRIAGE_PROVIDER", "simulated")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sqltext

from alembic import command
from alembic.config import Config as AlembicConfig
from app.config import get_settings
from app.db.session import get_engine, get_sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrated_schema():
    get_settings.cache_clear()
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sqltext("TRUNCATE TABLE complaints"))
    yield


@pytest.fixture()
def db_session():
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_redis():
    from app.providers.cache import get_redis

    client = get_redis()
    client.flushdb()
    yield
    client.flushdb()


@pytest.fixture()
def redis_client():
    from app.providers.cache import get_redis

    return get_redis()


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
