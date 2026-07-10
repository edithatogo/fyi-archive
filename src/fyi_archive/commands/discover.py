"""Read-only discovery commands delegated to fyi-cli."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from fyi_archive.body_discovery import discover_bodies_with_fallback, discover_bodies_with_fyi_cli
from fyi_archive.catalog_fallback import write_catalog_provenance
from fyi_archive.instances import DEFAULT_INSTANCE_ID, resolve_instance

app = typer.Typer(name="discover", help="Discover archive metadata via fyi-cli.")


@app.command("bodies")
def bodies(
    output: Annotated[Path, typer.Option()] = Path("data/_state/discovered_bodies.json"),
    shared_rate_limit_db: Annotated[Path, typer.Option()] = Path("data/_state/fyi-cli.db"),
    delay_seconds: Annotated[float, typer.Option()] = 2.0,
    instance: Annotated[str, typer.Option()] = DEFAULT_INSTANCE_ID,
    base_url: Annotated[str | None, typer.Option()] = None,
    catalog_url: Annotated[str | None, typer.Option()] = None,
    provenance: Annotated[Path | None, typer.Option()] = None,
    fallback: Annotated[
        bool,
        typer.Option(help="Restore the latest verified GitHub catalog on live failure."),
    ] = False,
    repository: Annotated[str | None, typer.Option()] = None,
    workflow: Annotated[str, typer.Option()] = "au_jurisdiction_rollout.yml",
) -> None:
    """Enumerate public authority bodies without implementing fetch logic here."""
    try:
        archive_instance = resolve_instance(instance_id=instance, base_url=base_url)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if fallback:
        if not repository:
            raise typer.BadParameter("--repository is required with --fallback")
        payload = discover_bodies_with_fallback(
            base_url=archive_instance.capture_base_url(),
            output_path=output,
            provenance_path=provenance or output.with_name("discovered_bodies.provenance.json"),
            shared_rate_limit_db=shared_rate_limit_db,
            delay_seconds=delay_seconds,
            catalog_url=catalog_url,
            repository=repository,
            workflow=workflow,
        )
    else:
        payload = discover_bodies_with_fyi_cli(
            base_url=archive_instance.capture_base_url(),
            output_path=output,
            shared_rate_limit_db=shared_rate_limit_db,
            delay_seconds=delay_seconds,
            catalog_url=catalog_url,
        )
    if provenance:
        write_catalog_provenance(provenance, payload.get("provenance", {}))
    payload["instance_id"] = archive_instance.id
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))
