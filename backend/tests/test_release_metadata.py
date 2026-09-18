"""Prevent version drift across the first tagged release artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_release_version_is_consistent_across_artifacts():
    version = (PROJECT_ROOT / "VERSION").read_text().strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)

    package = json.loads((PROJECT_ROOT / "frontend/package.json").read_text())
    assert package["version"] == version
    assert f'version="{version}"' in (PROJECT_ROOT / "backend/app/main.py").read_text()
    assert (PROJECT_ROOT / f"docs/releases/v{version}.md").is_file()
    assert f"## [{version}]" in (PROJECT_ROOT / "CHANGELOG.md").read_text()


def test_release_workflow_preserves_publish_before_release_order():
    workflow = (PROJECT_ROOT / ".github/workflows/release.yml").read_text()
    assert "paths: [VERSION]" in workflow
    assert "packages: write" in workflow
    assert "sbom: true" in workflow
    assert "provenance: mode=max" in workflow
    assert "needs: [prepare, publish-images]" in workflow
