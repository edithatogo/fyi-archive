"""Capture the authorized AU-NSW frame in uploaded, resumable tranches.

This controller is designed solely for GitHub Actions.  It keeps source payloads
on the ephemeral runner, and advances to the next tranche only once the previous
tranche's payload, manifest, source receipt, and upload receipt are on a private
Hugging Face dataset repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download

from fyi_archive.au_corpus_readiness import load_sampling_frame
from fyi_archive.body_discovery import discover_bodies_with_fallback
from fyi_archive.jurisdictions import jurisdiction_for_body_tag, load_jurisdiction_rules
from fyi_archive.manifest import build_manifest, load_derived_records, write_manifest_outputs
from fyi_archive.publish.hf_publish import publish_folder_to_hf, sha256_file
from fyi_archive.seed import SeedCaps, requests_from_jsonl, run_seed

CONFIRMATION = "I_CONFIRM_FULL_AU_NSW_PRIVATE_HF_CAPTURE"
CONTROL_ROOT = "au-nsw/restricted/control"
TRANCHE_ROOT = "au-nsw/restricted/tranches"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _body_jurisdiction(row: dict[str, Any], rules: dict[str, Any]) -> str:
    tags = row.get("tags") or row.get("Tags") or row.get("tag") or row.get("jurisdiction")
    candidates = tags if isinstance(tags, list) else str(tags or "").split()
    for tag in candidates:
        resolved = jurisdiction_for_body_tag(str(tag), rules)
        if resolved != "OTHER":
            return resolved
    return "OTHER"


def _authority_slug(row: dict[str, Any]) -> str:
    return str(row.get("url_name") or row.get("URL name") or row.get("slug") or "").strip()


def discover_nsw_queue(*, bodies: list[dict[str, Any]], base_url: str, db_path: Path, delay: float, output: Path) -> None:
    """Discover the exact NSW queue using fyi-cli's shared rate-limit database."""
    rows: dict[int, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory() as temporary:
        for body in bodies:
            slug = _authority_slug(body)
            if not slug:
                continue
            authority_output = Path(temporary) / f"{slug}.jsonl"
            subprocess.run(
                [
                    sys.executable, "-m", "fyi_system.cli", "discover", "--base-url", base_url,
                    "--authority", slug, "--delay-seconds", str(delay), "--db", str(db_path),
                    "--output", str(authority_output),
                ],
                check=True,
            )
            if authority_output.exists():
                for line in authority_output.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        row = json.loads(line)
                        rows[int(row["request_id"])] = row
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(rows[key], sort_keys=True) + "\n" for key in sorted(rows)), encoding="utf-8")


def _download_control(*, repo_id: str, token: str, relative_path: str, destination: Path) -> bool:
    try:
        remote = hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=relative_path, token=token)
    except Exception as error:  # The initial run has no control state.
        if getattr(getattr(error, "response", None), "status_code", None) == 404:
            return False
        if error.__class__.__name__ in {"EntryNotFoundError", "LocalEntryNotFoundError"}:
            return False
        raise
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(Path(remote).read_bytes())
    return True


def _assert_private_dataset(*, repo_id: str, token: str) -> None:
    info = HfApi(token=token).repo_info(repo_id=repo_id, repo_type="dataset", token=token)
    if not bool(getattr(info, "private", False)):
        raise RuntimeError(f"refusing to retain restricted AU payload in non-private dataset {repo_id}")


def _upload_control(*, folder: Path, repo_id: str, token: str) -> object:
    return publish_folder_to_hf(
        folder_path=folder,
        repo_id=repo_id,
        token=token,
        path_in_repo=CONTROL_ROOT,
        clean_stale=False,
        commit_message="chore(au-nsw): checkpoint private capture control state",
    )


def _upload_file(*, path: Path, repo_id: str, token: str, path_in_repo: str, message: str) -> object:
    return HfApi(token=token).upload_file(
        path_or_fileobj=path,
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type="dataset",
        token=token,
        commit_message=message,
    )


def _verify_remote_file(*, path: Path, repo_id: str, token: str, path_in_repo: str) -> None:
    remote = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=path_in_repo,
        token=token,
        force_download=True,
    )
    if sha256_file(path) != sha256_file(Path(remote)):
        raise RuntimeError(f"remote checksum mismatch for {path_in_repo}")


def _source_receipt(tranche_dir: Path, *, index: int, request_ids: list[int]) -> dict[str, Any]:
    files = {
        path.relative_to(tranche_dir).as_posix(): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(tranche_dir.rglob("*"))
        if path.is_file()
    }
    return {
        "schema": "fyi-archive.au-nsw-source-receipt.v1",
        "tranche": index,
        "request_ids": request_ids,
        "captured_at": _now(),
        "files": files,
    }


def _commit_fields(result: object) -> dict[str, str | None]:
    return {
        "oid": getattr(result, "oid", None) or getattr(result, "commit_oid", None),
        "url": getattr(result, "commit_url", None) or getattr(result, "url", None),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.confirm != CONFIRMATION:
        raise ValueError("explicit full AU-NSW private-HF confirmation is required")
    frame = load_sampling_frame(args.frame)
    if frame["publication_authorized"] is not False or frame["private_hf_retention_authorized"] is not True:
        raise ValueError("sampling frame does not authorize private retention only")
    _assert_private_dataset(repo_id=args.hf_repo_id, token=args.hf_token)

    nsw = next(item for item in frame["strata"] if item["jurisdiction"] == "NSW")
    request_total = int(nsw["request_cap"])
    root = args.output_dir
    control = root / "control"
    state_path = control / "capture_state.json"
    selection_path = control / "selection.jsonl"
    _download_control(repo_id=args.hf_repo_id, token=args.hf_token, relative_path=f"{CONTROL_ROOT}/capture_state.json", destination=state_path)
    _download_control(repo_id=args.hf_repo_id, token=args.hf_token, relative_path=f"{CONTROL_ROOT}/selection.jsonl", destination=selection_path)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"completed_tranches": []}

    if not selection_path.exists():
        catalog = discover_bodies_with_fallback(
            base_url=args.base_url, catalog_url=args.catalog_url, output_path=control / "bodies.json",
            provenance_path=control / "bodies.provenance.json", shared_rate_limit_db=args.rate_limit_db,
            delay_seconds=args.delay, repository=args.repository, workflow=args.workflow,
        )
        rules = load_jurisdiction_rules()
        nsw_bodies = [body for body in catalog.get("bodies", []) if isinstance(body, dict) and _body_jurisdiction(body, rules) == "NSW"]
        queue = control / "discovered_nsw_requests.jsonl"
        discover_nsw_queue(bodies=nsw_bodies, base_url=args.base_url, db_path=args.rate_limit_db, delay=args.delay, output=queue)
        rows = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows) != request_total:
            raise RuntimeError(f"pinned AU-NSW frame requires exactly {request_total} discovered requests, found {len(rows)}")
        selection_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        state = {"schema": "fyi-archive.au-nsw-private-hf-state.v1", "selection_sha256": _sha256_text(selection_path), "completed_tranches": []}
        _write_json(state_path, state)
        _upload_control(folder=control, repo_id=args.hf_repo_id, token=args.hf_token)

    if state.get("selection_sha256") != _sha256_text(selection_path):
        raise RuntimeError("remote AU-NSW selection checksum does not match resumed control state")
    selected = requests_from_jsonl(selection_path)
    if len(selected) != request_total:
        raise RuntimeError("resumed AU-NSW selection is not the approved 179-record frame")

    completed = {int(value) for value in state.get("completed_tranches", [])}
    tranche_count = (request_total + args.tranche_size - 1) // args.tranche_size
    for index in range(1, tranche_count + 1):
        if index in completed:
            continue
        tranche_requests = selected[(index - 1) * args.tranche_size : index * args.tranche_size]
        request_ids = [int(item.request_id) for item in tranche_requests]
        tranche_dir = root / "tranches" / f"tranche-{index:03d}"
        summary = run_seed(
            requests=tranche_requests, ledger_path=tranche_dir / "ledger.jsonl", data_dir=tranche_dir / "data",
            derived_dir=tranche_dir / "derived" / "requests", dist_dir=tranche_dir / "dist",
            caps=SeedCaps(max_requests=len(tranche_requests), max_runtime_minutes=args.max_runtime_minutes, max_disk_gb=args.max_disk_gb),
            dry_run=False,
            fyi_cli_args=["--base-url", args.base_url, "--delay-seconds", str(args.delay), "--db", str(args.rate_limit_db), "--rate-limit-name", "archive-capture-au-rtk"],
            min_interval_seconds=args.delay,
        )
        if summary["processed"] != len(tranche_requests) or summary["failed"]:
            raise RuntimeError(f"tranche {index} did not complete cleanly: {summary}")
        manifest = build_manifest(load_derived_records(tranche_dir / "data" / "raw" / "requests"), args.fyi_cli_version, instance_id="au-rtk", jurisdiction="NSW")
        if manifest["meta"]["record_count"] != len(tranche_requests):
            raise RuntimeError(f"tranche {index} manifest count does not match selection")
        write_manifest_outputs(manifest=manifest, manifest_path=tranche_dir / "manifest.json", parquet_path=tranche_dir / "manifest.parquet", authorities_path=tranche_dir / "authorities.json", instance_id="au-rtk")
        _write_json(tranche_dir / "source_receipt.json", _source_receipt(tranche_dir, index=index, request_ids=request_ids))
        payload_commit = publish_folder_to_hf(folder_path=tranche_dir, repo_id=args.hf_repo_id, token=args.hf_token, path_in_repo=f"{TRANCHE_ROOT}/tranche-{index:03d}", clean_stale=False, commit_message=f"data(au-nsw): retain tranche {index:03d}")
        _write_json(tranche_dir / "upload_receipt.json", {"schema": "fyi-archive.huggingface-upload-receipt.v1", "tranche": index, "uploaded_at": _now(), "repo_id": args.hf_repo_id, "path": f"{TRANCHE_ROOT}/tranche-{index:03d}", "payload_commit": _commit_fields(payload_commit), "source_receipt_sha256": sha256_file(tranche_dir / "source_receipt.json")})
        _upload_file(
            path=tranche_dir / "upload_receipt.json",
            repo_id=args.hf_repo_id,
            token=args.hf_token,
            path_in_repo=f"{TRANCHE_ROOT}/tranche-{index:03d}/upload_receipt.json",
            message=f"docs(au-nsw): add tranche {index:03d} upload receipt",
        )
        for filename in ("manifest.json", "source_receipt.json", "upload_receipt.json"):
            _verify_remote_file(
                path=tranche_dir / filename,
                repo_id=args.hf_repo_id,
                token=args.hf_token,
                path_in_repo=f"{TRANCHE_ROOT}/tranche-{index:03d}/{filename}",
            )
        completed.add(index)
        state["completed_tranches"] = sorted(completed)
        state["updated_at"] = _now()
        _write_json(state_path, state)
        _upload_control(folder=control, repo_id=args.hf_repo_id, token=args.hf_token)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--frame", type=Path, default=Path("configs/au/corpus_sampling_frame.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/au-rtk/nsw-private-hf"))
    parser.add_argument("--rate-limit-db", type=Path, default=Path("data/_state/au-rtk/nsw-private-hf.db"))
    parser.add_argument("--hf-repo-id", required=True)
    parser.add_argument("--hf-token", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", default="au_nsw_full_private_hf_capture.yml")
    parser.add_argument("--base-url", default="https://www.righttoknow.org.au")
    parser.add_argument("--catalog-url")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--tranche-size", type=int, default=10)
    parser.add_argument("--max-runtime-minutes", type=float, default=30.0)
    parser.add_argument("--max-disk-gb", type=float, default=5.0)
    parser.add_argument("--fyi-cli-version", default="1.2.1")
    args = parser.parse_args()
    if args.tranche_size < 1:
        parser.error("--tranche-size must be positive")
    print(json.dumps(run(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
