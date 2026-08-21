"""Run the AU jurisdiction controller's deterministic smoke path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.manifest import (
    build_manifest,
    merge_manifests,
    normalize_request_record,
    write_manifest_outputs,
)
from fyi_archive.rollout import initial_rollout_state, load_rollout_config, write_rollout_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fyi-cli-version", default="unknown")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run:
        raise SystemExit(
            "live rollout requires a capture worker; use --dry-run for controller verification"
        )

    config = load_rollout_config(args.config) if args.config else load_rollout_config()
    state = initial_rollout_state(config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[Path] = []
    for index, jurisdiction in enumerate(config["jurisdictions"], start=1):
        state["jurisdictions"][jurisdiction]["status"] = "complete"
        record = {
            "request_id": index,
            "url_title": f"rollout-smoke-{jurisdiction.lower()}",
            "title": f"AU rollout smoke {jurisdiction}",
            "authority": f"smoke-{jurisdiction.lower()}",
            "body_tag": jurisdiction.lower(),
            "state": "smoke",
            "html_captured": False,
        }
        manifest = build_manifest(
            [normalize_request_record(record)],
            args.fyi_cli_version,
            instance_id=config["instance_id"],
            jurisdiction=jurisdiction,
        )
        manifest_path = args.output_dir / f"manifest_{jurisdiction.lower()}.json"
        write_manifest_outputs(
            manifest=manifest,
            manifest_path=manifest_path,
            parquet_path=manifest_path.with_suffix(".parquet"),
            authorities_path=manifest_path.with_name(f"authorities_{jurisdiction.lower()}.json"),
            instance_id=config["instance_id"],
        )
        manifests.append(manifest_path)

    national = merge_manifests(
        manifest_paths=manifests,
        manifest_path=args.output_dir / "national_manifest.json",
        parquet_path=args.output_dir / "national_manifest.parquet",
        authorities_path=args.output_dir / "national_authorities.json",
        fyi_cli_version=args.fyi_cli_version,
        instance_id=config["instance_id"],
    )
    state["national_manifest"] = {
        "status": "complete",
        "record_count": national["meta"]["record_count"],
    }
    write_rollout_state(args.state, state)
    print(
        json.dumps({
            "jurisdictions": config["jurisdictions"],
            "record_count": national["meta"]["record_count"],
        })
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
