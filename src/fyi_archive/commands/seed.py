"""Historical seed CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from fyi_archive.seed import (
    SeedCaps,
    requests_from_id_range,
    requests_from_jsonl,
    run_seed,
    synthetic_requests,
)

app = typer.Typer(name="seed", help="Run a capped, resumable historical seed.")


@app.command()
def run(
    requests_file: Annotated[
        Path | None,
        typer.Option(help="JSONL request queue from fyi-cli."),
    ] = None,
    ledger_path: Annotated[Path, typer.Option()] = Path("data/_state/ledger.jsonl"),
    data_dir: Annotated[Path, typer.Option()] = Path("data"),
    dist_dir: Annotated[Path, typer.Option()] = Path("dist"),
    derived_dir: Annotated[Path, typer.Option()] = Path("data/derived/requests"),
    date_from: Annotated[str | None, typer.Option()] = None,
    date_to: Annotated[str | None, typer.Option()] = None,
    id_from: Annotated[int | None, typer.Option(help="First FYI request ID for fallback queueing.")] = None,
    id_to: Annotated[int | None, typer.Option(help="Last FYI request ID for fallback queueing.")] = None,
    allow_undiscovered: Annotated[
        bool,
        typer.Option(help="Allow capture from request IDs when discovery metadata is unavailable."),
    ] = False,
    max_requests: Annotated[int | None, typer.Option()] = None,
    max_bytes: Annotated[int | None, typer.Option()] = None,
    max_runtime_minutes: Annotated[float | None, typer.Option()] = None,
    max_disk_gb: Annotated[float | None, typer.Option()] = None,
    dry_run: Annotated[bool, typer.Option()] = False,
) -> None:
    """Run historical seed orchestration."""
    if requests_file is not None:
        requests = requests_from_jsonl(requests_file)
    elif allow_undiscovered and id_from is not None and id_to is not None:
        requests = requests_from_id_range(id_from, id_to)
    elif dry_run:
        requests = synthetic_requests(max_requests)
    else:
        msg = (
            "Non-dry-run seed requires --requests-file, or "
            "--id-from/--id-to with --allow-undiscovered."
        )
        raise typer.BadParameter(msg)

    summary = run_seed(
        requests=requests,
        ledger_path=ledger_path,
        data_dir=data_dir,
        derived_dir=derived_dir,
        caps=SeedCaps(
            max_requests=max_requests,
            max_bytes=max_bytes,
            max_runtime_minutes=max_runtime_minutes,
            max_disk_gb=max_disk_gb,
        ),
        dry_run=dry_run,
        dist_dir=dist_dir,
        date_from=date_from,
        date_to=date_to,
    )
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))
