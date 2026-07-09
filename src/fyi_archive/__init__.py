"""fyi-archive: orchestration + distribution for read-only Alaveteli FOI archives.

This package is intentionally thin. All network capture (enumeration, WARC/WACZ
writing, attachment download, content diff, health) is delegated to the companion
tool `fyi-cli`. This package provides:

- the orchestration CLI that drives `fyi-cli` commands,
- mirror adapters (Hugging Face, Zenodo, OSF),
- dataset metadata (Croissant, Frictionless),
- the DuckDB read-only analytics export,
- manifest/changes assembly, and
- health/parity reporting.

See ``conductor/`` for the track breakdown and ``docs/`` for architecture.
"""

from __future__ import annotations

from fyi_archive.version import __version__

__all__ = ["__version__"]
