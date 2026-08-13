"""Atheris harness for untrusted GitHub catalog ZIP artifacts."""

from __future__ import annotations

import sys
from contextlib import suppress

import atheris

with atheris.instrument_imports():
    from fyi_archive.catalog_fallback import CatalogArtifactError, parse_catalog_archive


def test_one_input(data: bytes) -> None:
    """Exercise bounded ZIP structure, decompression, JSON, and catalog validation."""
    with suppress(CatalogArtifactError):
        parse_catalog_archive(data)


def main() -> None:
    """Start libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
