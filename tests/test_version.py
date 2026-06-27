"""Smoke test: the package imports and the CLI reports the version."""

from __future__ import annotations

from typer.testing import CliRunner

from fyi_archive import __version__
from fyi_archive.cli import app

runner = CliRunner()


def test_version_constant_matches_file() -> None:
    """__version__ must be a non-empty PEP 440-ish string."""
    assert __version__
    assert __version__.count(".") >= 1


def test_cli_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
