"""Archive health and parity checks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from fyi_archive import __version__
from fyi_archive.health import manifest_count, mirror_counts_from_env, parity_report

app = typer.Typer(name="doctor", help="Check archive health and parity.")


def get_manifest_counts(
    manifest_path: Path = Path("manifests/latest_manifest.json"),
) -> dict[str, Any]:
    """Get counts from the manifest, returning zeroes when no manifest exists."""
    if not manifest_path.exists():
        return {"record_count": 0, "last_updated": None}

    try:
        count, generated_at = manifest_count(manifest_path)
    except (OSError, json.JSONDecodeError):
        return {"record_count": 0, "last_updated": None}

    return {"record_count": count, "last_updated": generated_at}


def get_mirror_counts() -> dict[str, dict[str, Any]]:
    """Get counts from each mirror."""
    return {
        name: {"count": count, "last_updated": None}
        for name, count in mirror_counts_from_env().items()
    }


def get_coverage_info() -> dict[str, int]:
    """Get test coverage information."""
    return {"percent_covered": 0, "target": 80}


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
    parity = parity_report(
        manifest_records=int(manifest["record_count"]),
        mirror_records={name: int(data["count"]) for name, data in mirrors.items()},
        tolerance=tolerance,
    )
    health_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": __version__,
        "manifest": manifest,
        "mirrors": mirrors,
        "parity": parity,
        "coverage": get_coverage_info(),
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
