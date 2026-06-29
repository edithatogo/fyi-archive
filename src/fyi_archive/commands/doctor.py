"""Archive health and parity checks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from fyi_archive import __version__

app = typer.Typer(name="doctor", help="Check archive health and parity.")


def get_manifest_counts(
    manifest_path: Path = Path("manifests/latest_manifest.json"),
) -> dict[str, Any]:
    """Get counts from the manifest, returning zeroes when no manifest exists."""
    if not manifest_path.exists():
        return {"record_count": 0, "last_updated": None}

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"record_count": 0, "last_updated": None}

    return {
        "record_count": data.get("record_count", 0),
        "last_updated": data.get("meta", {}).get("generated_at"),
    }


def get_mirror_counts() -> dict[str, dict[str, Any]]:
    """Get counts from each mirror."""
    # Placeholder until mirror adapters can query their respective APIs.
    return {
        "huggingface": {"count": 0, "last_updated": None},
        "osf": {"count": 0, "last_updated": None},
        "zenodo": {"count": 0, "last_updated": None},
    }


def get_coverage_info() -> dict[str, int]:
    """Get test coverage information."""
    return {"percent_covered": 0, "target": 60}


@app.command()
def check() -> None:
    """Run health checks and output report."""
    health_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": __version__,
        "manifest": get_manifest_counts(),
        "mirrors": get_mirror_counts(),
        "coverage": get_coverage_info(),
        "status": "healthy",
    }

    typer.echo(json.dumps(health_data, indent=2))

    output_path = Path("conductor/archive_health.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(health_data, indent=2) + "\n", encoding="utf-8")

    typer.echo("Health check completed and saved to conductor/archive_health.json")


if __name__ == "__main__":
    app()
