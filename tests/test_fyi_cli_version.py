"""Test to ensure fyi-cli version matches the pinned dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 compatibility
    import tomli as tomllib  # type: ignore[no-redef]


def _expected_fyi_cli_version(pyproject_path: Path) -> str:
    pyproject_data: dict[str, Any] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependencies = pyproject_data["project"]["dependencies"]
    pinned = [dep.removeprefix("fyi-cli==") for dep in dependencies if dep.startswith("fyi-cli==")]
    if not pinned:
        msg = "fyi-cli dependency not found in pyproject.toml"
        raise AssertionError(msg)
    return pinned[0]


def test_fyi_cli_version_matches_pyproject() -> None:
    """Test that installed fyi-cli matches the version pinned in pyproject.toml."""
    expected_version = _expected_fyi_cli_version(Path("pyproject.toml"))

    fyi_cli = pytest.importorskip("fyi_cli", reason="fyi-cli is not installed in this environment")
    actual_version = getattr(fyi_cli, "__version__", None)

    assert actual_version == expected_version
