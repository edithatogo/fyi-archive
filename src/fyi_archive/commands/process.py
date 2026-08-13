"""Process-event projection CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from fyi_archive.archive_package import (
    PackageInputs,
    build_archive_package,
    verify_archive_package,
    verify_package_store,
)
from fyi_archive.au_corpus_readiness import load_sampling_frame
from fyi_archive.derived_layer import validate_derived_manifest
from fyi_archive.derived_publication import package_derived_layer, verify_derived_bundle
from fyi_archive.jurisdiction_archive import load_target_registry
from fyi_archive.process_projection import (
    build_process_projection,
    merge_process_event_logs,
    verify_process_projection,
)

app = typer.Typer(name="process", help="Build public-safe process-mining projections.")


@app.command("package-archive")
def package_archive(
    instance: Annotated[str, typer.Option(help="Registered archive instance id.")],
    archive_revision: Annotated[int, typer.Option(help="Positive immutable revision number.")],
    repository: Annotated[str, typer.Option(help="HTTPS durable archive repository URI.")],
    repository_revision: Annotated[
        str, typer.Option(help="Full immutable 40-character repository commit.")
    ],
    cases: Annotated[Path, typer.Option(help="Case NDJSON produced from captured records.")],
    events: Annotated[Path, typer.Option(help="Ordered fyi-cli process-event NDJSON.")],
    attachments: Annotated[Path, typer.Option(help="Attachment metadata NDJSON.")],
    takedown_inventory: Annotated[Path, typer.Option(help="Versioned takedown inventory NDJSON.")],
    provenance: Annotated[Path, typer.Option(help="Source and transformation provenance JSON.")],
    retention: Annotated[Path, typer.Option(help="Retention status JSON.")],
    output_root: Annotated[Path, typer.Option()] = Path("dist/archive-packages"),
    package_kind: Annotated[str, typer.Option(help="snapshot or delta")] = "snapshot",
    base_archive_revision: Annotated[
        int | None, typer.Option(help="Latest indexed revision required by a delta.")
    ] = None,
) -> None:
    """Build an immutable local package and atomically update its indexes."""
    if package_kind not in {"snapshot", "delta"}:
        raise typer.BadParameter("--package-kind must be snapshot or delta")
    try:
        result = build_archive_package(
            PackageInputs(
                instance_id=instance,
                archive_revision=archive_revision,
                repository=repository,
                repository_revision=repository_revision,
                cases_path=cases,
                events_path=events,
                attachments_path=attachments,
                takedown_inventory_path=takedown_inventory,
                provenance_path=provenance,
                retention_path=retention,
                package_kind=cast("Literal['snapshot', 'delta']", package_kind),
                base_archive_revision=base_archive_revision,
            ),
            output_root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("verify-archive-package")
def verify_archive_package_command(
    package_dir: Annotated[Path, typer.Option(help="Immutable package revision directory.")],
) -> None:
    """Verify one immutable package without network access."""
    try:
        result = verify_archive_package(package_dir)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("verify-archive-package-store")
def verify_archive_package_store_command(
    output_root: Annotated[Path, typer.Option()] = Path("dist/archive-packages"),
) -> None:
    """Verify every indexed package, latest pointer, and catalogue entry."""
    try:
        result = verify_package_store(output_root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("project")
def project(
    events: Annotated[Path, typer.Option(help="fyi-cli process-events JSONL input.")],
    output_dir: Annotated[Path, typer.Option()] = Path("dist/process-events"),
    manifest: Annotated[Path | None, typer.Option()] = None,
    attachments: Annotated[Path | None, typer.Option()] = None,
    takedown: Annotated[
        Path | None, typer.Option(help="JSONL stable IDs excluded from derived output.")
    ] = None,
    source_reconciliation: Annotated[
        Path | None, typer.Option(help="Historical candidate reconciliation JSON.")
    ] = None,
    snapshot_revision: Annotated[str | None, typer.Option()] = None,
    require_live_manifest: Annotated[
        bool, typer.Option(help="Reject dry-run rows when building a full-corpus projection.")
    ] = False,
) -> None:
    """Validate and materialize process events for archive publication."""
    try:
        result = build_process_projection(
            events_path=events,
            output_dir=output_dir,
            manifest_path=manifest,
            attachments_path=attachments,
            takedown_path=takedown,
            source_reconciliation_path=source_reconciliation,
            snapshot_revision=snapshot_revision,
            require_live_manifest=require_live_manifest,
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


@app.command("merge")
def merge(
    inputs: Annotated[list[Path], typer.Argument(help="Event-log JSONL shards to merge.")],
    output: Annotated[Path, typer.Option(help="Merged deterministic JSONL output.")] = Path(
        "merged-process-events.ndjson"
    ),
) -> None:
    """Merge resumed/backfill event shards without guessing conflicts."""
    try:
        rows = merge_process_event_logs(inputs)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps({"merged": len(rows), "output": str(output)}, sort_keys=True))


@app.command("validate-derived")
def validate_derived(
    manifest: Annotated[Path, typer.Option(help="FOI-O derived-layer manifest JSON.")],
) -> None:
    """Validate a separately versioned FOI-O candidate manifest."""
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    if not isinstance(document, dict):
        raise typer.BadParameter("derived manifest must be a JSON object")
    result = validate_derived_manifest(document)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command("package-derived")
def package_derived(
    manifest: Annotated[Path, typer.Option(help="Pinned FOI-O derived manifest JSON.")],
    candidates: Annotated[Path, typer.Option(help="Candidate-only NDJSON records.")],
    output_dir: Annotated[Path, typer.Option()] = Path("dist/foi-o-derived"),
    baseline: Annotated[
        Path | None, typer.Option(help="Optional prior candidate NDJSON for delta reporting.")
    ] = None,
) -> None:
    """Build a deterministic local bundle without publishing it."""
    try:
        result = package_derived_layer(
            manifest_path=manifest,
            candidates_path=candidates,
            output_dir=output_dir,
            baseline_path=baseline,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("verify-derived-bundle")
def verify_derived(
    output_dir: Annotated[Path, typer.Option()] = Path("dist/foi-o-derived"),
) -> None:
    """Verify local bundle digests, candidate count, and manifest contract."""
    try:
        result = verify_derived_bundle(output_dir)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("validate-au-sampling-frame")
def validate_au_sampling_frame(
    path: Annotated[Path, typer.Option()] = Path("configs/au/corpus_sampling_frame.json"),
) -> None:
    """Validate the fail-closed Australian pilot sampling contract."""
    try:
        document = load_sampling_frame(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        json.dumps(
            {
                "valid": True,
                "capture_authorized": document["capture_authorized"],
                "publication_authorized": document["publication_authorized"],
            },
            sort_keys=True,
        )
    )


@app.command("validate-jurisdiction-targets")
def validate_jurisdiction_targets(
    path: Annotated[Path, typer.Option()] = Path("configs/jurisdiction_archive_targets.json"),
) -> None:
    """Validate explicit archive status and evidence for every roadmap target."""
    try:
        document = load_target_registry(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        json.dumps(
            {
                "valid": True,
                "target_count": len(document["targets"]),
                "publication_allowed": document["publication_allowed"],
            },
            sort_keys=True,
        )
    )
