"""Production startup orchestration without external services."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from scripts import start_production


def test_initialize_uses_unpooled_migration_url_and_runtime_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://pooled/app?sslmode=require")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgres://direct/app?sslmode=require")
    monkeypatch.setenv("ROBOOPS_SEED_ON_STARTUP", "true")
    monkeypatch.setenv("ROBOOPS_BOOTSTRAP_EMAIL", "demo@example.com")
    monkeypatch.setenv("ROBOOPS_BOOTSTRAP_PASSWORD", "demo-password-123")

    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(command, *, check, env):
        assert check is True
        calls.append((command, env))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(start_production.subprocess, "run", fake_run)
    start_production.initialize()

    assert [call[0] for call in calls] == [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "scripts.seed"],
        [sys.executable, "-m", "scripts.bootstrap_user"],
    ]
    assert calls[0][1]["DATABASE_URL"] == "postgresql+psycopg://direct/app?sslmode=require"
    assert calls[1][1]["DATABASE_URL"] == "postgresql+psycopg://pooled/app?sslmode=require"
    assert calls[2][1]["DATABASE_URL"] == "postgresql+psycopg://pooled/app?sslmode=require"


def test_initialize_requires_direct_url_and_complete_bootstrap_pair(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_UNPOOLED", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL_UNPOOLED"):
        start_production.initialize()

    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgresql+psycopg://direct/app")
    monkeypatch.setenv("ROBOOPS_BOOTSTRAP_EMAIL", "demo@example.com")
    monkeypatch.delenv("ROBOOPS_BOOTSTRAP_PASSWORD", raising=False)
    monkeypatch.setattr(start_production.subprocess, "run", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="must be provided together"):
        start_production.initialize()


def test_main_replaces_process_with_uvicorn_after_initialization(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setattr(start_production, "initialize", lambda: None)
    captured: dict[str, object] = {}

    def fake_execv(executable, arguments):
        captured.update(executable=executable, arguments=arguments)

    monkeypatch.setattr(start_production.os, "execv", fake_execv)
    start_production.main()

    assert captured == {
        "executable": sys.executable,
        "arguments": [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
        ],
    }
