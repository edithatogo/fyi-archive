"""Delegate authority-body enumeration to fyi-cli."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fyi_archive.catalog_fallback import (
    restore_latest_verified_catalog,
    validate_catalog_payload,
    write_catalog_provenance,
)


def discover_bodies_with_fyi_cli(
    *,
    base_url: str,
    output_path: Path,
    shared_rate_limit_db: Path,
    delay_seconds: float = 1.0,
    catalog_url: str | None = None,
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
        *(["--catalog-url", catalog_url] if catalog_url else []),
        "--delay-seconds",
        str(delay_seconds),
        "--db",
        str(shared_rate_limit_db),
        "--output",
        str(output_path),
    ]
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            break
        except subprocess.CalledProcessError as error:
            if attempt == attempts:
                detail = (error.stderr or error.stdout or "").strip()
                suffix = f": {detail[-4000:]}" if detail else ""
                raise RuntimeError(
                    f"fyi-cli body discovery failed after {attempts} attempts{suffix}"
                ) from error
            time.sleep(attempt * 10)
    return json.loads(output_path.read_text(encoding="utf-8"))


def discover_bodies_with_fallback(
    *,
    base_url: str,
    output_path: Path,
    provenance_path: Path,
    shared_rate_limit_db: Path,
    delay_seconds: float = 1.0,
    catalog_url: str | None = None,
    repository: str,
    workflow: str,
    github_token: str | None = None,
) -> dict[str, Any]:
    """Use live discovery first, then atomically restore a verified catalog artifact."""
    live_output = output_path.with_suffix(output_path.suffix + ".live.tmp")
    try:
        payload = discover_bodies_with_fyi_cli(
            base_url=base_url,
            catalog_url=catalog_url,
            output_path=live_output,
            shared_rate_limit_db=shared_rate_limit_db,
            delay_seconds=delay_seconds,
        )
        write_catalog_provenance(
            provenance_path,
            {"mode": "live", **dict(payload.get("provenance", {}))},
        )
        validate_catalog_payload(payload)
        live_output.replace(output_path)
        return payload  # noqa: TRY300
    except Exception as error:
        if live_output.exists():
            live_output.unlink()
        restore_latest_verified_catalog(
            output_path=output_path,
            provenance_path=provenance_path,
            repository=repository,
            workflow=workflow,
            token=github_token,
            failed_live_source_url=catalog_url
            or f"{base_url.rstrip('/')}/body/all-authorities.csv",
            failure_class=type(error).__name__,
            diagnostic=str(error),
        )
        return json.loads(output_path.read_text(encoding="utf-8"))
