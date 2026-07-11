"""Single source of truth for the package version.

Mirrors ``VERSION`` and ``pyproject.toml`` ``[project].version``; kept in sync by
``scripts/check_version_consistency.py`` in CI.
"""

from __future__ import annotations

__version__ = "0.8.0"
