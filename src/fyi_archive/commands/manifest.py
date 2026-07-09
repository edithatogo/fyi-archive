"""Manifest assembly CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from fyi_archive.instances import DEFAULT_INSTANCE_ID
from fyi_archive.manifest import assemble_manifest, merge_manifests

app = typer.Typer(name="manifest", help="Assemble archive manifests.")


@app.command()
def build(
    derived_dir: Annotated[Path, typer.Option()] = Path("data/derived/requests"),
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    parquet_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.parquet"),
    authorities_path: Annotated[Path, typer.Option()] = Path("manifests/authorities.json"),
    fyi_cli_version: Annotated[str, typer.Option()] = "unknown",
    instance: Annotated[
        str,
        typer.Option(help="Archive instance id.", envvar="FYI_ARCHIVE_INSTANCE"),
    ] = DEFAULT_INSTANCE_ID,
    jurisdiction: Annotated[
        str | None,
        typer.Option(help="Optional within-instance jurisdiction (e.g. NSW)."),
    ] = None,
) -> None:
    """Build latest manifest outputs from derived request records."""
    try:
        manifest = assemble_manifest(
            derived_dir=derived_dir,
            manifest_path=manifest_path,
            parquet_path=parquet_path,
            authorities_path=authorities_path,
            fyi_cli_version=fyi_cli_version,
            instance_id=instance,
            jurisdiction=jurisdiction,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(manifest["meta"], indent=2, sort_keys=True))


@app.command()
def merge(
    input_manifest: Annotated[
        list[Path],
        typer.Option("--input-manifest", help="Manifest JSON to merge; repeatable."),
    ],
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    parquet_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.parquet"),
    authorities_path: Annotated[Path, typer.Option()] = Path("manifests/authorities.json"),
    fyi_cli_version: Annotated[str, typer.Option()] = "unknown",
    instance: Annotated[
        str,
        typer.Option(help="Archive instance id.", envvar="FYI_ARCHIVE_INSTANCE"),
    ] = DEFAULT_INSTANCE_ID,
    jurisdiction: Annotated[
        str | None,
        typer.Option(help="Optional within-instance jurisdiction (e.g. NSW)."),
    ] = None,
) -> None:
    """Merge chunk manifests into consolidated manifest outputs."""
    if not input_manifest:
        raise typer.BadParameter("at least one --input-manifest is required")
    try:
        manifest = merge_manifests(
            manifest_paths=input_manifest,
            manifest_path=manifest_path,
            parquet_path=parquet_path,
            authorities_path=authorities_path,
            fyi_cli_version=fyi_cli_version,
            instance_id=instance,
            jurisdiction=jurisdiction,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(manifest["meta"], indent=2, sort_keys=True))
