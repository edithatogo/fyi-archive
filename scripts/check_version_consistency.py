#!/usr/bin/env python3
"""Assert version consistency across release and package metadata.

Exits non-zero if the four sources disagree. Run in CI and via ``make``.

Structural script (no project logic); works once the repo exists.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYPROJECT_FILE = ROOT / "pyproject.toml"
PKG_VERSION_FILE = ROOT / "src" / "fyi_archive" / "version.py"
LOCK_FILE = ROOT / "uv.lock"


def read_version_file() -> str:
    text = VERSION_FILE.read_text(encoding="utf-8").strip()
    match = re.match(r"^([0-9]+(?:\.[0-9]+)+(?:[a-z0-9.+-]*)?)\b", text)
    if not match:
        sys.exit(f"Could not find version in {VERSION_FILE}")
    return match.group(1)


def read_pyproject_version() -> str:
    text = PYPROJECT_FILE.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        sys.exit(f"Could not find version in {PYPROJECT_FILE}")  # noqa: PLR2004
    return match.group(1)


def read_pkg_version() -> str:
    text = PKG_VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        sys.exit(f"Could not find __version__ in {PKG_VERSION_FILE}")
    return match.group(1)


def read_lock_version() -> str:
    data = tomllib.loads(LOCK_FILE.read_text(encoding="utf-8"))
    matches = [
        package
        for package in data.get("package", [])
        if package.get("name") == "fyi-archive" and package.get("source") == {"editable": "."}
    ]
    if len(matches) != 1 or not matches[0].get("version"):
        sys.exit(f"Could not find editable fyi-archive package in {LOCK_FILE}")
    return str(matches[0]["version"])


def main() -> int:
    sources = {
        "VERSION": read_version_file(),
        "pyproject.toml": read_pyproject_version(),
        "src/fyi_archive/version.py": read_pkg_version(),
        "uv.lock": read_lock_version(),
    }
    distinct = set(sources.values())
    if len(distinct) != 1:
        sys.exit(f"Version mismatch across sources: {sources}")
    print(f"Version consistent across all sources: {next(iter(distinct))}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
