"""Delegate authority-body enumeration to fyi-cli."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def discover_bodies_with_fyi_cli(
    *,
    base_url: str,
    output_path: Path,
    shared_rate_limit_db: Path,
    delay_seconds: float = 1.0,
) -> dict[str, Any]:
    """Run fyi-cli's read-only, rate-limited body discovery command."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shared_rate_limit_db.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "fyi_system.cli",
        "discover-bodies",
        "--base-url",
        base_url,
        "--delay-seconds",
        str(delay_seconds),
        "--db",
        str(shared_rate_limit_db),
        "--output",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(output_path.read_text(encoding="utf-8"))
