"""Run safe deployment initialization, then replace this process with Uvicorn."""
from __future__ import annotations

import os
import subprocess
import sys


TRUE_VALUES = {"1", "true", "yes", "on"}


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUE_VALUES


def _run_module(module: str, *, env: dict[str, str]) -> None:
    subprocess.run([sys.executable, "-m", module], check=True, env=env)


def initialize() -> None:
    runtime_env = os.environ.copy()
    migration_url = runtime_env.get("DATABASE_URL_UNPOOLED")
    if not migration_url:
        raise RuntimeError("DATABASE_URL_UNPOOLED is required for production migrations.")

    migration_env = runtime_env | {"DATABASE_URL": migration_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=migration_env,
    )

    if _enabled("ROBOOPS_SEED_ON_STARTUP"):
        _run_module("scripts.seed", env=runtime_env)

    bootstrap_email = runtime_env.get("ROBOOPS_BOOTSTRAP_EMAIL")
    bootstrap_password = runtime_env.get("ROBOOPS_BOOTSTRAP_PASSWORD")
    if bool(bootstrap_email) != bool(bootstrap_password):
        raise RuntimeError(
            "ROBOOPS_BOOTSTRAP_EMAIL and ROBOOPS_BOOTSTRAP_PASSWORD must be provided together."
        )
    if bootstrap_email and bootstrap_password:
        _run_module("scripts.bootstrap_user", env=runtime_env)


def main() -> None:
    initialize()
    port = os.environ.get("PORT", "8000")
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


if __name__ == "__main__":
    main()
