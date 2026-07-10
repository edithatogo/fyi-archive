"""Run the capped, sequential AU discovery/capture/manifest pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fyi_archive.body_discovery import discover_bodies_with_fallback
from fyi_archive.jurisdictions import jurisdiction_for_body_tag, load_jurisdiction_rules
from fyi_archive.manifest import (
    build_manifest,
    load_derived_records,
    merge_manifests,
    write_manifest_outputs,
)
from fyi_archive.rollout import load_rollout_config, write_rollout_state
from fyi_archive.seed import requests_from_jsonl, run_seed


def _authority_slug(row: dict[str, Any]) -> str:
    return str(row.get("url_name") or row.get("URL name") or row.get("slug") or "").strip()


def _body_jurisdiction(row: dict[str, Any], rules: dict[str, Any]) -> str:
    tags = row.get("tags") or row.get("Tags") or row.get("tag") or row.get("jurisdiction")
    candidates = tags if isinstance(tags, list) else str(tags or "").split()
    for tag in candidates:
        resolved = jurisdiction_for_body_tag(str(tag), rules)
        if resolved != "OTHER":
            return resolved
    return "OTHER"


def discover_request_queue(
    *,
    authorities: list[dict[str, Any]],
    base_url: str,
    db_path: Path,
    delay_seconds: float,
    output_path: Path,
) -> None:
    """Discover requests authority-by-authority using the shared fyi-cli limiter."""
    rows: dict[int, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory() as temporary:
        for authority in authorities:
            slug = _authority_slug(authority)
            if not slug:
                continue
            authority_output = Path(temporary) / f"{slug}.jsonl"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "fyi_system.cli",
                    "discover",
                    "--base-url",
                    base_url,
                    "--authority",
                    slug,
                    "--delay-seconds",
                    str(delay_seconds),
                    "--db",
                    str(db_path),
                    "--output",
                    str(authority_output),
                ],
                check=True,
            )
            if authority_output.exists():
                for line in authority_output.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        row = json.loads(line)
                        rows[int(row["request_id"])] = row
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(rows[key], sort_keys=True) + "\n" for key in sorted(rows)),
        encoding="utf-8",
    )


def run_live_rollout(args: argparse.Namespace) -> dict[str, Any]:
    config = load_rollout_config(args.config)
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)
    state = {
        "instance_id": config["instance_id"],
        "shared_rate_limit_name": config["shared_rate_limit_name"],
        "mode": "live",
        "catalog_provenance": str(args.provenance),
        "jurisdictions": {},
        "national_manifest": {"status": "pending"},
    }
    catalog_path = root / "discovered_bodies.json"
    discover_bodies_with_fallback(
        base_url=args.capture_base_url,
        catalog_url=args.catalog_url,
        output_path=catalog_path,
        provenance_path=args.provenance,
        shared_rate_limit_db=args.rate_limit_db,
        delay_seconds=args.delay_seconds,
        repository=args.repository,
        workflow=args.workflow,
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    bodies = catalog.get("bodies", [])
    rules = load_jurisdiction_rules()
    grouped = {jurisdiction: [] for jurisdiction in config["jurisdictions"]}
    for body in bodies:
        if isinstance(body, dict):
            grouped.setdefault(_body_jurisdiction(body, rules), []).append(body)

    manifest_paths: list[Path] = []
    for jurisdiction in config["jurisdictions"]:
        jurisdiction_root = root / jurisdiction.lower()
        jurisdiction_root.mkdir(parents=True, exist_ok=True)
        queue_path = jurisdiction_root / "discovered_requests.jsonl"
        discover_request_queue(
            authorities=grouped.get(jurisdiction, []),
            base_url=args.capture_base_url,
            db_path=args.rate_limit_db,
            delay_seconds=args.delay_seconds,
            output_path=queue_path,
        )
        summary = run_seed(
            requests=requests_from_jsonl(queue_path),
            ledger_path=jurisdiction_root / "ledger.jsonl",
            data_dir=jurisdiction_root / "data",
            derived_dir=jurisdiction_root / "derived" / "requests",
            dist_dir=jurisdiction_root / "dist",
            caps=args.seed_caps,
            dry_run=False,
            fyi_cli_args=[
                "--base-url",
                args.capture_base_url,
                "--min-interval",
                str(args.delay_seconds),
                "--concurrency",
                "1",
            ],
            continue_on_error=args.continue_on_error,
        )
        manifest = build_manifest(
            load_derived_records(jurisdiction_root / "derived" / "requests"),
            args.fyi_cli_version,
            instance_id="au-rtk",
            jurisdiction=jurisdiction,
        )
        manifest_path = jurisdiction_root / "manifest.json"
        write_manifest_outputs(
            manifest=manifest,
            manifest_path=manifest_path,
            parquet_path=jurisdiction_root / "manifest.parquet",
            authorities_path=jurisdiction_root / "authorities.json",
            instance_id="au-rtk",
        )
        manifest_paths.append(manifest_path)
        state["jurisdictions"][jurisdiction] = {"status": "complete", "seed": summary}
        write_rollout_state(args.state, state)

    national_path = root / "national_manifest.json"
    national = merge_manifests(
        manifest_paths=manifest_paths,
        manifest_path=national_path,
        parquet_path=root / "national_manifest.parquet",
        authorities_path=root / "national_authorities.json",
        fyi_cli_version=args.fyi_cli_version,
        instance_id="au-rtk",
    )
    state["national_manifest"] = {
        "status": "complete",
        "record_count": national["meta"]["record_count"],
        "path": str(national_path),
        "provenance": str(args.provenance),
    }
    write_rollout_state(args.state, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--rate-limit-db", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow", default="au_jurisdiction_rollout.yml")
    parser.add_argument("--capture-base-url", required=True)
    parser.add_argument("--catalog-url")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--fyi-cli-version", required=True)
    parser.add_argument("--max-requests", type=int, default=50)
    parser.add_argument("--max-runtime-minutes", type=float, default=30.0)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    from fyi_archive.seed import SeedCaps

    args.seed_caps = SeedCaps(
        max_requests=args.max_requests,
        max_runtime_minutes=args.max_runtime_minutes,
    )
    print(json.dumps(run_live_rollout(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
