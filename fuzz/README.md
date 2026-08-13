# Fuzzing

The harnesses call production parsers with untrusted bytes:

- `fuzz_catalog_archive.py`: bounded GitHub artifact ZIP and JSON parsing.
- `fuzz_archive_package.py`: package manifest, inventory, path, and NDJSON verification.
- `fuzz_historical_manifest.py`: historical status JSON, declared paths, and digests.

Run all targets with bounded resources:

```bash
uv sync --frozen
uv run --with atheris==3.1.0 python scripts/run_fuzzers.py --seconds-per-target 30
```

Crashes and timeouts are written below `fuzz/artifacts/`. Inputs must contain no
production data, credentials, or correspondence; CI retains only generated failure cases.
