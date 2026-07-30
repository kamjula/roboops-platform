"""Shared pytest fixtures for RoboOps backend tests.

Provides an isolated ORM test session backed by TEST_DATABASE_URL, using the
SQLAlchemy 2.x supported join_transaction_mode="create_savepoint" pattern:
each test runs inside an outer transaction that is rolled back afterwards,
even if the test itself calls session.commit(). This intentionally avoids
private SQLAlchemy attributes such as transaction._parent.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

DATABASE_URL = os.environ.get("DATABASE_URL")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATION_TEST_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")


def _require(url: str | None, name: str) -> None:
    if not url:
        pytest.exit(
            f"{name} is not set. Refusing to run database tests without an explicit, dedicated URL.",
            returncode=1,
        )


def _validate_test_urls() -> None:
    """Fail immediately and clearly if the test URLs are missing or unsafe."""
    _require(DATABASE_URL, "DATABASE_URL")
    _require(TEST_DATABASE_URL, "TEST_DATABASE_URL")
    _require(MIGRATION_TEST_DATABASE_URL, "MIGRATION_TEST_DATABASE_URL")

    if TEST_DATABASE_URL == DATABASE_URL:
        pytest.exit("TEST_DATABASE_URL must never equal DATABASE_URL.", returncode=1)
    if MIGRATION_TEST_DATABASE_URL == DATABASE_URL:
        pytest.exit("MIGRATION_TEST_DATABASE_URL must never equal DATABASE_URL.", returncode=1)
    if MIGRATION_TEST_DATABASE_URL == TEST_DATABASE_URL:
        pytest.exit("MIGRATION_TEST_DATABASE_URL must never equal TEST_DATABASE_URL.", returncode=1)


_validate_test_urls()

# Import models so Base.metadata is fully populated before create_all().
from app.models import *  # noqa: E402,F401,F403

test_engine = create_engine(TEST_DATABASE_URL, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    """Create ORM tables in the dedicated TEST_DATABASE_URL once per session."""
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture()
def db_session():
    """A session bound to an outer transaction that is rolled back after the test.

    Uses the SQLAlchemy 2.x supported join_transaction_mode="create_savepoint"
    pattern so tests may call session.commit() without persisting data past
    the test, and without touching private SQLAlchemy internals.
    """
    connection = test_engine.connect()
    outer_transaction = connection.begin()

    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
