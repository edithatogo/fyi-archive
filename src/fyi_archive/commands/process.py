"""Process-event projection CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from fyi_archive.process_projection import build_process_projection, verify_process_projection

app = typer.Typer(name="process", help="Build public-safe process-mining projections.")


@app.command("project")
def project(
    events: Annotated[Path, typer.Option(help="fyi-cli process-events JSONL input.")],
    output_dir: Annotated[Path, typer.Option()] = Path("dist/process-events"),
    manifest: Annotated[Path | None, typer.Option()] = None,
    attachments: Annotated[Path | None, typer.Option()] = None,
    snapshot_revision: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Validate and materialize process events for archive publication."""
    try:
        result = build_process_projection(
            events_path=events,
            output_dir=output_dir,
            manifest_path=manifest,
            attachments_path=attachments,
            snapshot_revision=snapshot_revision,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("verify")
def verify(
    output_dir: Annotated[Path, typer.Option()] = Path("dist/process-events"),
) -> None:
    """Verify projection checksums before publication or ingestion."""
    try:
        verify_process_projection(output_dir)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps({"verified": True, "output_dir": str(output_dir)}))
