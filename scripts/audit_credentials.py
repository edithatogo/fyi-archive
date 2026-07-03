#!/usr/bin/env python3
"""Build a redacted credential inventory for live archive publication.

The report intentionally records only presence, source kind, and public metadata.
It never writes secret values or value hashes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_SERVICES = [
    {"name": "HF_TOKEN", "label": "Hugging Face token"},
    {"name": "HF_REPO_ID", "label": "Hugging Face repository id"},
    {"name": "ZENODO_TOKEN", "label": "Zenodo production token"},
    {"name": "OSF_TOKEN", "label": "OSF token"},
    {"name": "OSF_PARENT_ID", "label": "OSF parent project id"},
]

OPTIONAL_SERVICES = [
    {"name": "ZENODO_SANDBOX_TOKEN", "label": "Zenodo sandbox token"},
    {"name": "GITHUB_TOKEN", "label": "GitHub token"},
]

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".swarm",
    ".venv",
    "__pycache__",
    "node_modules",
}

PLACEHOLDERS = {"", "changeme", "change-me", "example", "placeholder", "todo", "xxx"}


def classify_value(value: str | None) -> str:
    """Classify a credential-like value without returning the value itself."""
    if value is None:
        return "missing"
    normalized = value.strip()
    if not normalized:
        return "empty"
    if normalized.lower() in PLACEHOLDERS or normalized.endswith("_HERE"):
        return "placeholder"
    return "present"


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from env-like files."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def candidate_files(root: Path) -> list[Path]:
    """Return likely credential/config files under a root."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        name = path.name.lower()
        if (
            name.startswith(".env")
            or "secret" in name
            or name.endswith((".env.example", ".yml", ".yaml", ".toml"))
        ):
            files.append(path)
    return files


def scan_files(root: Path, service_labels: dict[str, str]) -> list[dict[str, str]]:
    """Find credential names in local files without storing values."""
    findings: list[dict[str, str]] = []
    names = list(service_labels)
    for path in candidate_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matched_names = sorted(name for name in names if name in text)
        if not matched_names:
            continue
        parsed = parse_env_file(path) if path.name.lower().startswith(".env") else {}
        for name in matched_names:
            findings.append(
                {
                    "service": service_labels[name],
                    "path": path.as_posix(),
                    "value_status": classify_value(parsed.get(name)) if parsed else "mentioned",
                },
            )
    return findings


def gh_json(args: list[str]) -> list[dict[str, Any]]:
    """Run gh and return JSON output; return [] when gh is unavailable or unauthenticated."""
    if shutil.which("gh") is None:
        return []
    try:
        completed = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    if not completed.stdout.strip():
        return []
    return json.loads(completed.stdout)


def build_inventory(repo: str, scan_roots: list[Path]) -> dict[str, Any]:
    """Build the full redacted credential inventory."""
    service_labels = {
        item["name"]: item["label"] for item in [*REQUIRED_SERVICES, *OPTIONAL_SERVICES]
    }
    env_status = {
        item["label"]: {
            "required": item in REQUIRED_SERVICES,
            "value_status": classify_value(os.environ.get(item["name"])),
        }
        for item in [*REQUIRED_SERVICES, *OPTIONAL_SERVICES]
    }
    github_secrets = gh_json(["secret", "list", "--repo", repo, "--json", "name,updatedAt"])
    github_vars = gh_json(["variable", "list", "--repo", repo, "--json", "name,updatedAt"])
    file_findings = []
    for root in scan_roots:
        if root.exists():
            file_findings.extend(scan_files(root, service_labels))
    configured = {
        item["label"]
        for item in REQUIRED_SERVICES
        if any(entry.get("name") == item["name"] for entry in github_secrets + github_vars)
    }
    missing_for_live_publish = sorted(
        item["label"] for item in REQUIRED_SERVICES if item["label"] not in configured
    )
    return {
        "inventory_schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "repository": repo,
        "policy": "No secret values or value hashes are stored in this report.",
        "required_services": [item["label"] for item in REQUIRED_SERVICES],
        "optional_services": [item["label"] for item in OPTIONAL_SERVICES],
        "environment": env_status,
        "github_actions": {
            "secret_count": len(github_secrets),
            "variable_count": len(github_vars),
            "missing_for_live_publish": missing_for_live_publish,
        },
        "local_file_mentions": file_findings,
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="edithatogo/fyi-archive")
    parser.add_argument("--scan-root", action="append", default=[])
    parser.add_argument("--output", default="conductor/credential_inventory.json")
    args = parser.parse_args()

    scan_roots = [Path(root).resolve() for root in args.scan_root] or [Path("..").resolve()]
    inventory = build_inventory(args.repo, scan_roots)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    if inventory["github_actions"]["missing_for_live_publish"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
