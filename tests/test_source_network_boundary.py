from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Add production paths here as each source transport is migrated to fyi-cli.
MIGRATED_CDX_PATHS = (ROOT / ".github/workflows/all_instance_historical_indexes.yml",)

DIRECT_CDX_CLIENTS = (
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\b(?:requests|httpx|urllib)\b", re.IGNORECASE),
    re.compile(r"fetch_(?:complete_)?internet_archive_cdx\.py"),
)


def test_migrated_production_paths_do_not_implement_direct_cdx_clients() -> None:
    violations: list[str] = []
    for path in MIGRATED_CDX_PATHS:
        content = path.read_text(encoding="utf-8")
        for pattern in DIRECT_CDX_CLIENTS:
            if pattern.search(content):
                violations.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")

    assert violations == []


def test_migrated_cdx_workflow_uses_exact_pinned_adapter_commit() -> None:
    workflow = MIGRATED_CDX_PATHS[0].read_text(encoding="utf-8")

    assert "FYI_CLI_COMMIT: e2364d5221c67b69c2c4aca0a959d713eff4ec01" in workflow
    assert (
        'uv tool install "git+https://github.com/edithatogo/fyi-cli.git@${FYI_CLI_COMMIT}"'
        in workflow
    )
    assert "fyi internet-archive-cdx" in workflow
    assert "--checkpoint" in workflow
    assert "--receipt" in workflow
    assert '"revision": __import__("os").environ["FYI_CLI_COMMIT"]' in workflow
