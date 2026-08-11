"""CLI contracts for NZ real-backfill controller state."""

import json
import subprocess
import sys

from fyi_archive.backfill_state_codec import decode_state, state_body_from_state
from fyi_archive.nz_backfill_state import new_state


def test_controller_cli_reserves_completes_and_reports_next(tmp_path) -> None:
    body = tmp_path / "body.json"
    reserved = tmp_path / "reserved.json"
    receipt = tmp_path / "receipt.json"
    completed = tmp_path / "completed.json"
    body.write_text(state_body_from_state(new_state(queue_count=1000)), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "scripts/nz_backfill_controller.py",
            "reserve",
            "--body",
            str(body),
            "--output",
            str(reserved),
            "--start-offset",
            "0",
            "--batch-size",
            "100",
            "--run-id",
            "42",
        ],
        check=True,
    )
    receipt.write_text(json.dumps({"start_offset": 0, "batch_size": 100}), encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "scripts/nz_backfill_controller.py",
            "complete",
            "--body",
            str(reserved),
            "--output",
            str(completed),
            "--receipt",
            str(receipt),
            "--run-id",
            "42",
        ],
        check=True,
    )
    state = decode_state(completed.read_text(encoding="utf-8"))
    assert state["completed"][0]["end_offset"] == 100

    result = subprocess.run(
        [sys.executable, "scripts/nz_backfill_controller.py", "next", "--body", str(completed)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "100"
