"""Atheris harness for historical status manifests and declared artifact paths."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

import atheris

with atheris.instrument_imports():
    from scripts.build_historical_archive_manifest import build_manifest


def test_one_input(data: bytes) -> None:
    """Exercise JSON shape, path containment, and digest validation."""
    if len(data) > 64 * 1024:
        return
    with tempfile.TemporaryDirectory(prefix="fyi-manifest-fuzz-") as directory:
        root = Path(directory)
        artifact = root / "artifact.json"
        artifact.write_bytes(b"{}\n")
        root.joinpath("au.status.json").write_bytes(data)
        with suppress(OSError, UnicodeError, ValueError, KeyError, TypeError):
            build_manifest(root, instance_id="au")

        # Always reach the valid digest path when the input is small enough.
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        root.joinpath("au.status.json").write_text(
            '{"artifacts":{"artifact.json":{"byte_count":3,"sha256":"'
            + digest
            + '"}},"replay_delay_seconds":0,"replay_limit_per_instance":1,'
            '"replay_timeout_seconds":1}',
            encoding="utf-8",
        )
        build_manifest(root, instance_id="au")


def main() -> None:
    """Start libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
