"""Backfill verification reporting commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from fyi_archive.backfill_verification import (
    build_backfill_verification_report,
    load_controller_state,
    remote_huggingface_record_count,
    remote_zenodo_record_count,
    write_backfill_report,
    write_versioned_backfill_report,
)
from fyi_archive.publish.zenodo_publish import ZENODO_API

app = typer.Typer(name="backfill", help="Inspect and verify historical backfill progress.")


def _mirror_targets(report_path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not report_path.exists():
        return None, None
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return None, None
    hf = None
    zenodo = None
    for item in data:
        if not isinstance(item, dict):
            continue
        mirror = item.get("mirror")
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        if mirror == "huggingface":
            hf = details
        elif mirror == "zenodo":
            zenodo = details
    return hf, zenodo


@app.command()
def report(
    repo: Annotated[str | None, typer.Option(envvar="GITHUB_REPOSITORY")] = None,
    state_label: Annotated[
        str, typer.Option(envvar="FYI_BACKFILL_STATE_LABEL")
    ] = "fyi-backfill-state",
    state_issue_number: Annotated[
        int | None, typer.Option(envvar="FYI_BACKFILL_STATE_ISSUE")
    ] = None,
    dry_run: Annotated[bool, typer.Option(envvar="DRY_RUN")] = False,
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    mirror_report_path: Annotated[Path, typer.Option()] = Path("dist/mirror_verification.json"),
    output_path: Annotated[Path, typer.Option()] = Path("dist/backfill_verification.json"),
    output_dir: Annotated[Path, typer.Option()] = Path("versions"),
    hf_token: Annotated[str | None, typer.Option(envvar="HF_TOKEN")] = None,
    hf_repo_id: Annotated[str | None, typer.Option(envvar="HF_REPO_ID")] = None,
    hf_revision: Annotated[str | None, typer.Option()] = None,
    zenodo_token: Annotated[str | None, typer.Option(envvar="ZENODO_TOKEN")] = None,
    zenodo_deposition_id: Annotated[int | None, typer.Option(envvar="ZENODO_DEPOSITION_ID")] = None,
    zenodo_api_url: Annotated[str, typer.Option(envvar="ZENODO_API_URL")] = ZENODO_API,
) -> None:
    """Build a cross-system count report for the historical backfill."""
    if repo is None:
        raise typer.BadParameter("GITHUB_REPOSITORY or --repo is required")

    state_info = load_controller_state(
        repo=repo, state_label=state_label, issue_number=state_issue_number
    )
    hf_details, zenodo_details = _mirror_targets(mirror_report_path)
    if hf_repo_id is None and isinstance(hf_details, dict):
        hf_repo_id = str(hf_details.get("repo_id") or "") or None
    if zenodo_deposition_id is None and isinstance(zenodo_details, dict):
        raw_id = zenodo_details.get("deposition_id")
        zenodo_deposition_id = int(raw_id) if raw_id is not None else None

    hf_info = None
    if hf_repo_id is not None and hf_token is not None:
        hf_info = remote_huggingface_record_count(
            repo_id=hf_repo_id,
            token=hf_token,
            revision=hf_revision,
        )

    zenodo_info = None
    if zenodo_deposition_id is not None and zenodo_token is not None:
        zenodo_info = remote_zenodo_record_count(
            token=zenodo_token,
            deposition_id=zenodo_deposition_id,
            api_url=zenodo_api_url,
        )

    report_data = build_backfill_verification_report(
        state_info=state_info,
        merged_manifest_path=manifest_path,
        hf_info=hf_info,
        zenodo_info=zenodo_info,
    )
    report_data["dry_run"] = dry_run
    write_backfill_report(output_path, report_data)
    write_versioned_backfill_report(report=report_data, output_dir=output_dir)
    typer.echo(json.dumps(report_data, indent=2, sort_keys=True))
    if not dry_run and not bool(report_data["comparison"]["fully_verified"]):
        raise typer.Exit(2)
