"""Archive health and parity checks."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from fyi_archive import __version__
from fyi_archive.health import live_mirror_counts, manifest_count, parity_report

app = typer.Typer(name="doctor", help="Check archive health and parity.")


def get_manifest_counts(
    manifest_path: Path = Path("manifests/latest_manifest.json"),
) -> dict[str, Any]:
    """Get counts from the local manifest, or fall back to Hugging Face."""
    if manifest_path.exists():
        try:
            count, generated_at = manifest_count(manifest_path)
            return {
                "record_count": count,
                "last_updated": generated_at,
                "source": "local",
                "path": manifest_path.as_posix(),
            }
        except (OSError, json.JSONDecodeError):
            pass

    # Fall back to the live HF dataset when local manifests are absent (monitor checkout).
    mirrors = live_mirror_counts()
    hf = mirrors.get("huggingface") or {}
    if int(hf.get("count") or 0) > 0 and hf.get("source") == "huggingface":
        return {
            "record_count": int(hf["count"]),
            "last_updated": hf.get("last_updated"),
            "source": "huggingface",
            "repo_id": hf.get("repo_id"),
        }
    return {"record_count": 0, "last_updated": None, "source": "missing"}


def get_mirror_counts() -> dict[str, dict[str, Any]]:
    """Get counts from each mirror (live when credentials exist)."""
    return live_mirror_counts()


def get_coverage_info(manifest_records: int) -> dict[str, Any]:
    """Estimate coverage against the configured ID horizon / target."""
    # Historical controller default horizon is 1..250000 inclusive when complete.
    target_percent = int(os.environ.get("COVERAGE_TARGET_PERCENT", "60"))
    id_horizon = int(os.environ.get("COVERAGE_ID_HORIZON", "250000"))
    percent = 0 if id_horizon <= 0 else min(100, round(100 * manifest_records / id_horizon))
    return {
        "percent_covered": percent,
        "target": target_percent,
        "id_horizon": id_horizon,
        "records": manifest_records,
    }


@app.command()
def check(
    tolerance: Annotated[
        int,
        typer.Option(help="Allowed mirror/manifest record skew."),
    ] = 5,
) -> None:
    """Run health checks and output report."""
    manifest = get_manifest_counts()
    mirrors = get_mirror_counts()
    # Only parity-check mirrors that returned a live or env count (skip pure unavailable).
    parity_inputs = {
        name: int(data.get("count") or 0)
        for name, data in mirrors.items()
        if data.get("source") not in {None, "unavailable"} or int(data.get("count") or 0) > 0
    }
    # If nothing resolved, still report zeros so the schema stays stable.
    if not parity_inputs:
        parity_inputs = dict.fromkeys(mirrors, 0)
    parity = parity_report(
        manifest_records=int(manifest["record_count"]),
        mirror_records=parity_inputs,
        tolerance=tolerance,
    )
    health_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": __version__,
        "manifest": manifest,
        "mirrors": mirrors,
        "parity": parity,
        "coverage": get_coverage_info(int(manifest["record_count"])),
        "status": "healthy" if parity["healthy"] else "drift",
    }

    typer.echo(json.dumps(health_data, indent=2))

    output_path = Path("conductor/archive_health.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(health_data, indent=2) + "\n", encoding="utf-8")

    typer.echo("Health check completed and saved to conductor/archive_health.json")
    if not parity["healthy"]:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
