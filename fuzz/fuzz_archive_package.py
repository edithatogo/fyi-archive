"""Atheris harness for immutable package manifests, paths, and NDJSON parsing."""

from __future__ import annotations

import sys
import tempfile
from contextlib import suppress
from pathlib import Path

import atheris

with atheris.instrument_imports():
    from fyi_archive.archive_package import verify_archive_package


def test_one_input(data: bytes) -> None:
    """Treat fuzzer bytes as an archive manifest and verify it fail-closed."""
    if len(data) > 64 * 1024:
        return
    with tempfile.TemporaryDirectory(prefix="fyi-archive-fuzz-") as directory:
        Path(directory, "archive-package.json").write_bytes(data)
        with suppress(OSError, UnicodeError, ValueError, KeyError, TypeError):
            verify_archive_package(Path(directory))


def main() -> None:
    """Start libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
