#!/usr/bin/env python3
"""Assert version consistency across VERSION, pyproject.toml, and the package.

Exits non-zero if the three sources disagree. Run in CI and via ``make``.

Structural script (no project logic); works once the repo exists.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYPROJECT_FILE = ROOT / "pyproject.toml"
PKG_VERSION_FILE = ROOT / "src" / "fyi_archive" / "version.py"


def read_version_file() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


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


def main() -> int:
    sources = {
        "VERSION": read_version_file(),
        "pyproject.toml": read_pyproject_version(),
        "src/fyi_archive/version.py": read_pkg_version(),
    }
    distinct = set(sources.values())
    if len(distinct) != 1:
        sys.exit(f"Version mismatch across sources: {sources}")
    print(f"Version consistent across all sources: {next(iter(distinct))}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
