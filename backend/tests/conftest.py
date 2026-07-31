"""Shared pytest fixtures for RoboOps backend tests.

Database-backed fixtures are created lazily - only when a test explicitly
requests the db_session fixture - so tests that never touch the database
(such as the Phase 1 health check test) can run without DATABASE_URL,
TEST_DATABASE_URL, or MIGRATION_TEST_DATABASE_URL being set at all.

When a database-backed test does run, it uses the SQLAlchemy 2.x supported
join_transaction_mode="create_savepoint" pattern: each test runs inside an
outer transaction that is rolled back afterwards, even if the test itself
calls session.commit(). This intentionally avoids private SQLAlchemy
attributes such as transaction._parent.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

DATABASE_URL = os.environ.get("DATABASE_URL")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATION_TEST_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")

_test_engine = None


def _require(url: str | None, name: str) -> None:
    if not url:
        pytest.fail(f"{name} is not set. Refusing to run database tests without an explicit, dedicated URL.")


def _validate_test_urls() -> None:
    """Fail immediately and clearly if the test URLs are missing or unsafe."""
    _require(DATABASE_URL, "DATABASE_URL")
    _require(TEST_DATABASE_URL, "TEST_DATABASE_URL")
    _require(MIGRATION_TEST_DATABASE_URL, "MIGRATION_TEST_DATABASE_URL")

    if TEST_DATABASE_URL == DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL must never equal DATABASE_URL.")
    if MIGRATION_TEST_DATABASE_URL == DATABASE_URL:
        pytest.fail("MIGRATION_TEST_DATABASE_URL must never equal DATABASE_URL.")
    if MIGRATION_TEST_DATABASE_URL == TEST_DATABASE_URL:
        pytest.fail("MIGRATION_TEST_DATABASE_URL must never equal TEST_DATABASE_URL.")


def _get_test_engine():
    """Validate URLs and create the ORM test engine/schema on first use only."""
    global _test_engine
    if _test_engine is None:
        _validate_test_urls()
        from app.models import Base  # imported lazily so Base.metadata is fully populated

        _test_engine = create_engine(TEST_DATABASE_URL, future=True)
        Base.metadata.create_all(bind=_test_engine)
    return _test_engine


@pytest.fixture()
def db_session():
    """A session bound to an outer transaction that is rolled back after the test.

    Uses the SQLAlchemy 2.x supported join_transaction_mode="create_savepoint"
    pattern so tests may call session.commit() without persisting data past
    the test, and without touching private SQLAlchemy internals.
    """
    engine = _get_test_engine()
    connection = engine.connect()
    outer_transaction = connection.begin()

    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()

@pytest.fixture()
def client(db_session):
    """A TestClient whose app uses the same transactional db_session."""
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
