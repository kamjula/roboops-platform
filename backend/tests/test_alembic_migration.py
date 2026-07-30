"""Destructive Alembic migration round-trip test.

This is the ONLY test allowed to drop/recreate the public schema, and it
does so exclusively inside MIGRATION_TEST_DATABASE_URL - never DATABASE_URL
and never TEST_DATABASE_URL. Alembic is invoked as a subprocess with
DATABASE_URL temporarily overridden (in that subprocess's environment only)
to point at MIGRATION_TEST_DATABASE_URL, since alembic/env.py reads
DATABASE_URL from the environment.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ.get("DATABASE_URL")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
MIGRATION_TEST_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "sites",
    "robot_models",
    "technicians",
    "robots",
    "sensors",
    "sensor_readings",
    "maintenance_schedules",
    "maintenance_records",
    "alerts",
}


def _run_alembic(command: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = MIGRATION_TEST_DATABASE_URL
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *command.split()],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic {command} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"


@pytest.mark.skipif(not MIGRATION_TEST_DATABASE_URL, reason="MIGRATION_TEST_DATABASE_URL is not set.")
def test_alembic_upgrade_and_downgrade_round_trip():
    if MIGRATION_TEST_DATABASE_URL == DATABASE_URL:
        pytest.fail("MIGRATION_TEST_DATABASE_URL must never equal DATABASE_URL.")
    if MIGRATION_TEST_DATABASE_URL == TEST_DATABASE_URL:
        pytest.fail("MIGRATION_TEST_DATABASE_URL must never equal TEST_DATABASE_URL.")

    engine = create_engine(MIGRATION_TEST_DATABASE_URL, future=True)

    # Reset to a clean slate. This destructive drop/recreate of the public
    # schema is only ever performed against MIGRATION_TEST_DATABASE_URL.
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    _run_alembic("upgrade head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Migration did not create expected tables: {missing}"

    _run_alembic("downgrade base")

    inspector = inspect(engine)
    tables_after_downgrade = set(inspector.get_table_names())
    remaining = EXPECTED_TABLES & tables_after_downgrade
    assert not remaining, f"Downgrade did not remove expected tables: {remaining}"

    # Leave the migration test database at head so the run is repeatable.
    _run_alembic("upgrade head")
    engine.dispose()
