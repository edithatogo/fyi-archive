"""Run every Atheris target with consistent resource and artifact limits."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    "fuzz_catalog_archive.py",
    "fuzz_archive_package.py",
    "fuzz_historical_manifest.py",
)
MAX_SECONDS_PER_TARGET = 900
MAX_RSS_MB = 1024
MAX_INPUT_BYTES = 64 * 1024


def _zip_seed() -> bytes:
    payload: dict[str, object] = {
        "bodies": [],
        "provenance": {"payload_sha256": "0" * 64},
    }
    provenance = {"payload_sha256": "0" * 64}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("discovered_bodies.json", json.dumps(payload))
        archive.writestr("discovered_bodies.provenance.json", json.dumps(provenance))
    return stream.getvalue()


def prepare_corpora(corpus_root: Path) -> None:
    """Create deterministic, synthetic seed inputs for each target."""
    seeds = {
        "fuzz_catalog_archive": _zip_seed(),
        "fuzz_archive_package": b'{"schema_version":"1.0.0"}',
        "fuzz_historical_manifest": b'{"artifacts":{}}',
    }
    for target, data in seeds.items():
        directory = corpus_root / target
        directory.mkdir(parents=True, exist_ok=True)
        name = base64.urlsafe_b64encode(data[:12]).decode("ascii").rstrip("=") or "empty"
        (directory / f"seed-{name}").write_bytes(data)


def main() -> int:
    """Run bounded targets serially and return the first failing status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds-per-target", type=int, default=30)
    parser.add_argument("--rss-limit-mb", type=int, default=MAX_RSS_MB)
    parser.add_argument("--corpus-root", type=Path, default=ROOT / "fuzz" / "corpus")
    parser.add_argument("--artifact-root", type=Path, default=ROOT / "fuzz" / "artifacts")
    args = parser.parse_args()
    if not 1 <= args.seconds_per_target <= MAX_SECONDS_PER_TARGET:
        parser.error(f"--seconds-per-target must be between 1 and {MAX_SECONDS_PER_TARGET}")
    if not 128 <= args.rss_limit_mb <= MAX_RSS_MB:
        parser.error(f"--rss-limit-mb must be between 128 and {MAX_RSS_MB}")

    prepare_corpora(args.corpus_root)
    args.artifact_root.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment.setdefault("PYTHONHASHSEED", "0")
    for target in TARGETS:
        stem = Path(target).stem
        artifacts = args.artifact_root / stem
        artifacts.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(ROOT / "fuzz" / target),
            str(args.corpus_root / stem),
            f"-artifact_prefix={artifacts.as_posix()}/",
            f"-max_total_time={args.seconds_per_target}",
            f"-rss_limit_mb={args.rss_limit_mb}",
            f"-max_len={MAX_INPUT_BYTES}",
            "-timeout=10",
            "-print_final_stats=1",
        ]
        result = subprocess.run(
            command,
            check=False,
            cwd=ROOT,
            env=environment,
            timeout=args.seconds_per_target + 30,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
