"""Tests for the non-publishing live projection benchmark entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_benchmark_process_projection_verifies_fixture_output(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "event_id": "event-1",
                "case_id": "case-1",
                "activity": "RequestReceived",
                "source_index": 1,
                "contract_version": "1.0.0",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"meta": {"record_count": 1}, "requests": []}), encoding="utf-8"
    )
    output = tmp_path / "output"
    script = Path(__file__).parents[1] / "scripts" / "benchmark_process_projection.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--events",
            str(events),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
            "--revision",
            "fixture-benchmark-1",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["source_revision"] == "fixture-benchmark-1"
    assert report["coverage"]["event_count"] == 1
    assert report["publication"] == "none"
