"""Prospective sync CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from fyi_archive.instances import DEFAULT_INSTANCE_ID, resolve_instance
from fyi_archive.sync import run_sync, write_sync_health

app = typer.Typer(name="sync", help="Run prospective incremental sync.")


@app.command()
def run(
    state_path: Annotated[Path, typer.Option()] = Path("data/_state/sync_state.json"),
    derived_dir: Annotated[Path, typer.Option()] = Path("data/raw/requests"),
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    parquet_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.parquet"),
    authorities_path: Annotated[Path, typer.Option()] = Path("manifests/authorities.json"),
    changes_path: Annotated[Path, typer.Option()] = Path("manifests/latest_changes.json"),
    fyi_cli_version: Annotated[str, typer.Option()] = "1.0.0",
    hf_repo_id: Annotated[str | None, typer.Option()] = None,
    hf_token: Annotated[str | None, typer.Option(envvar="HF_TOKEN")] = None,
    health_path: Annotated[Path | None, typer.Option()] = None,
    dry_run: Annotated[bool, typer.Option()] = False,
    instance: Annotated[
        str,
        typer.Option(help="Archive instance id.", envvar="FYI_ARCHIVE_INSTANCE"),
    ] = DEFAULT_INSTANCE_ID,
    base_url: Annotated[
        str | None,
        typer.Option(
            help="Override Alaveteli base URL (forwarded to fyi-cli when capturing).",
            envvar="FYI_ARCHIVE_BASE_URL",
        ),
    ] = None,
    jurisdiction: Annotated[
        str | None,
        typer.Option(help="Optional within-instance jurisdiction (e.g. NSW)."),
    ] = None,
) -> None:
    """Run one prospective sync cycle."""
    try:
        archive_instance = resolve_instance(instance_id=instance, base_url=base_url)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    # fyi-cli `diff` is local-only and does not accept --base-url; instance
    # identity is applied when assembling the manifest. Capture of new IDs is
    # driven by seed/backfill with --base-url.
    _ = archive_instance.capture_base_url()
    summary = run_sync(
        state_path=state_path,
        derived_dir=derived_dir,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        authorities_path=authorities_path,
        changes_path=changes_path,
        fyi_cli_version=fyi_cli_version,
        hf_repo_id=hf_repo_id,
        hf_token=hf_token,
        dry_run=dry_run,
        instance_id=archive_instance.id,
        jurisdiction=jurisdiction,
    )
    if health_path is not None:
        write_sync_health(health_path, summary)
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))
