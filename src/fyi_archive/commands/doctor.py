"""Archive health and parity checks."""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from fyi_archive import __version__
from fyi_archive.health import live_mirror_counts, manifest_count, parity_report
from fyi_archive.instances import DEFAULT_INSTANCE_ID, get_instance

logger = logging.getLogger(__name__)

app = typer.Typer(name="doctor", help="Check archive health and parity.")


def get_manifest_counts(
    manifest_path: Path = Path("manifests/latest_manifest.json"),
    *,
    instance_id: str = DEFAULT_INSTANCE_ID,
    jurisdiction: str | None = None,
) -> dict[str, Any]:
    """Get counts from the local manifest, or fall back to Hugging Face."""
    if manifest_path.exists():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            meta = raw.get("meta", {})
            if meta.get("instance_id", DEFAULT_INSTANCE_ID) != instance_id:
                return {
                    "record_count": 0,
                    "last_updated": None,
                    "source": "scope-mismatch",
                    "path": manifest_path.as_posix(),
                }
            requested_jurisdiction = jurisdiction.upper() if jurisdiction else None
            if requested_jurisdiction and meta.get("jurisdiction") != requested_jurisdiction:
                return {
                    "record_count": 0,
                    "last_updated": None,
                    "source": "scope-mismatch",
                    "path": manifest_path.as_posix(),
                }
            count, generated_at = manifest_count(manifest_path)
            return {
                "record_count": count,
                "last_updated": generated_at,
                "source": "local",
                "path": manifest_path.as_posix(),
                "instance_id": instance_id,
                "jurisdiction": requested_jurisdiction,
            }
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load local manifest at %s, falling back to Hugging Face", manifest_path, exc_info=e)

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


def get_coverage_info(
    manifest_records: int, *, instance_id: str = DEFAULT_INSTANCE_ID
) -> dict[str, Any]:
    """Report coverage against an enumerated denominator or labelled planning horizon."""
    suffix = instance_id.upper().replace("-", "_")
    public_denominator_raw = os.environ.get(
        f"COVERAGE_PUBLIC_DENOMINATOR_{suffix}",
        os.environ.get("COVERAGE_PUBLIC_DENOMINATOR", ""),
    ).strip()
    planning_estimate = not public_denominator_raw
    if planning_estimate:
        denominator = int(
            os.environ.get(
                f"COVERAGE_ID_HORIZON_{suffix}",
                os.environ.get("COVERAGE_ID_HORIZON", "250000"),
            )
        )
        denominator_method = "planning_id_horizon"
        default_target = "60"
    else:
        denominator = int(public_denominator_raw)
        denominator_method = os.environ.get(
            f"COVERAGE_DENOMINATOR_METHOD_{suffix}",
            os.environ.get("COVERAGE_DENOMINATOR_METHOD", "enumerated_public_records"),
        )
        default_target = "100"
    target_percent = int(
        os.environ.get(
            f"COVERAGE_TARGET_PERCENT_{suffix}",
            os.environ.get("COVERAGE_TARGET_PERCENT", default_target),
        )
    )
    precision = 0 if planning_estimate else 4
    percent = (
        0 if denominator <= 0 else min(100, round(100 * manifest_records / denominator, precision))
    )
    target_records = (
        0
        if denominator <= 0 or target_percent <= 0
        else math.ceil(denominator * target_percent / 100)
    )
    return {
        "percent_covered": percent,
        "target": target_percent,
        "id_horizon": denominator if planning_estimate else None,
        "denominator": denominator,
        "denominator_method": denominator_method,
        "planning_estimate": planning_estimate,
        "instance_id": instance_id,
        "records": manifest_records,
        "target_records": target_records,
        "remaining_to_target": max(0, target_records - manifest_records),
        "target_met": manifest_records >= target_records,
    }


@app.command()
def check(
    tolerance: Annotated[
        int,
        typer.Option(help="Allowed mirror/manifest record skew."),
    ] = 5,
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    instance: Annotated[str, typer.Option()] = DEFAULT_INSTANCE_ID,
    jurisdiction: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Run health checks and output report."""
    get_instance(instance)
    manifest = get_manifest_counts(
        manifest_path,
        instance_id=instance,
        jurisdiction=jurisdiction,
    )
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
        "coverage": get_coverage_info(int(manifest["record_count"]), instance_id=instance),
        "status": "healthy" if parity["healthy"] else "drift",
        "scope": {
            "instance_id": instance,
            "jurisdiction": jurisdiction.upper() if jurisdiction else None,
        },
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
