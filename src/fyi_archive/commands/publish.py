"""Publication verification CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from fyi_archive.publish.evidence import (
    existing_artifact_paths,
    verify_huggingface_dataset,
    verify_osf_node,
    verify_zenodo_deposition,
    write_versioned_verification_bundle,
)
from fyi_archive.publish.verification import (
    ArtifactVerification,
    MirrorVerification,
    write_verification_report,
)
from fyi_archive.publish.zenodo_publish import ZENODO_API

app = typer.Typer(name="publish", help="Publish and verify archive mirrors.")


@app.command()
def verify(
    root: Annotated[Path, typer.Option(help="Repository root for relative artifacts.")] = Path(),
    manifest_path: Annotated[Path, typer.Option()] = Path("manifests/latest_manifest.json"),
    output_dir: Annotated[Path, typer.Option()] = Path("versions"),
    report_path: Annotated[Path, typer.Option()] = Path("dist/mirror_verification.json"),
    artifact: Annotated[
        list[Path] | None,
        typer.Option("--artifact", help="Artifact path to verify; repeatable."),
    ] = None,
    hf_repo_id: Annotated[str | None, typer.Option(envvar="HF_REPO_ID")] = None,
    hf_token: Annotated[str | None, typer.Option(envvar="HF_TOKEN")] = None,
    hf_revision: Annotated[str | None, typer.Option()] = None,
    zenodo_deposition_id: Annotated[int | None, typer.Option(envvar="ZENODO_DEPOSITION_ID")] = None,
    zenodo_token: Annotated[str | None, typer.Option(envvar="ZENODO_TOKEN")] = None,
    zenodo_api_url: Annotated[str, typer.Option(envvar="ZENODO_API_URL")] = ZENODO_API,
    osf_node_id: Annotated[str | None, typer.Option(envvar="OSF_NODE_ID")] = None,
    osf_token: Annotated[str | None, typer.Option(envvar="OSF_TOKEN")] = None,
    osf_api_url: Annotated[str, typer.Option(envvar="OSF_API_URL")] = "https://api.osf.io/v2",
) -> None:
    """Verify remote mirror contents and store versioned evidence."""
    root = root.resolve()
    resolved_manifest = manifest_path if manifest_path.is_absolute() else root / manifest_path
    artifacts = existing_artifact_paths(root=root, artifact_paths=artifact)
    if not resolved_manifest.exists():
        raise typer.BadParameter(f"manifest does not exist: {resolved_manifest}")
    if not artifacts:
        raise typer.BadParameter("no local artifacts exist to verify")

    reports: list[MirrorVerification] = []
    if hf_repo_id is not None:
        reports.append(
            verify_huggingface_dataset(
                repo_id=hf_repo_id,
                token=hf_token,
                revision=hf_revision,
                local_artifacts=artifacts,
                manifest_path=resolved_manifest,
                repo_root=root,
            ),
        )
    if zenodo_deposition_id is not None:
        if zenodo_token is None:
            raise typer.BadParameter("ZENODO_TOKEN is required with Zenodo verification")
        reports.append(
            verify_zenodo_deposition(
                token=zenodo_token,
                deposition_id=zenodo_deposition_id,
                local_artifacts=artifacts,
                manifest_path=resolved_manifest,
                api_url=zenodo_api_url,
            ),
        )
    if osf_node_id is not None:
        if osf_token is None:
            raise typer.BadParameter("OSF_TOKEN is required with OSF verification")
        reports.append(
            verify_osf_node(
                token=osf_token,
                node_id=osf_node_id,
                local_artifacts=artifacts,
                manifest_path=resolved_manifest,
                api_url=osf_api_url,
            ),
        )
    if not reports:
        raise typer.BadParameter(
            "set at least one mirror target: HF_REPO_ID, ZENODO_DEPOSITION_ID, or OSF_NODE_ID"
        )

    resolved_report = report_path if report_path.is_absolute() else root / report_path
    resolved_output = output_dir if output_dir.is_absolute() else root / output_dir
    merged_reports = merge_reports(resolved_report, reports)
    write_verification_report(resolved_report, merged_reports)
    bundle = write_versioned_verification_bundle(
        reports=merged_reports,
        manifest_path=resolved_manifest,
        output_dir=resolved_output,
    )
    typer.echo(json.dumps(bundle, indent=2, sort_keys=True))
    if not bool(bundle["verified"]):
        raise typer.Exit(2)


def merge_reports(path: Path, reports: list[MirrorVerification]) -> list[MirrorVerification]:
    """Merge newly verified mirror reports with an existing JSON report."""
    if not path.exists():
        return reports
    existing_data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(existing_data, list):
        return reports
    report_by_mirror = {report.mirror: report for report in reports}
    merged: list[MirrorVerification] = []
    for item in existing_data:
        if not isinstance(item, dict):
            continue
        mirror = item.get("mirror")
        if not isinstance(mirror, str) or mirror in report_by_mirror:
            continue
        merged.append(report_from_json(item))
    merged.extend(reports)
    return merged


def report_from_json(data: dict[str, Any]) -> MirrorVerification:
    """Deserialize the subset needed to preserve existing mirror reports."""
    artifacts_data = data.get("artifacts")
    artifacts = (
        [artifact_from_json(item) for item in artifacts_data if isinstance(item, dict)]
        if isinstance(artifacts_data, list)
        else []
    )
    details_data = data.get("details")
    details: dict[str, Any] = details_data if isinstance(details_data, dict) else {}
    return MirrorVerification(
        mirror=str(data["mirror"]),
        verified=bool(data.get("verified")),
        record_count=int(data.get("record_count") or 0),
        artifacts=artifacts,
        details=details,
    )


def artifact_from_json(data: dict[str, Any]) -> ArtifactVerification:
    """Deserialize artifact verification evidence from JSON."""
    return ArtifactVerification(
        name=str(data["name"]),
        present=bool(data.get("present")),
        size_matches=data.get("size_matches")
        if isinstance(data.get("size_matches"), bool)
        else None,
        checksum_matches=(
            data.get("checksum_matches") if isinstance(data.get("checksum_matches"), bool) else None
        ),
        local_sha256=str(data.get("local_sha256") or ""),
        remote_checksum=(
            str(data["remote_checksum"]) if isinstance(data.get("remote_checksum"), str) else None
        ),
        remote_url=str(data["remote_url"]) if isinstance(data.get("remote_url"), str) else None,
    )
