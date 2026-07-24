from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
ACTION_REFERENCE = re.compile(r"^\s*-\s+uses:\s+(.+?)\s*$")
PINNED_ACTION = re.compile(r"^[^@\s]+@[0-9a-f]{40}(?:\s+#.*)?$")


def test_every_remote_github_action_is_pinned_to_a_full_commit() -> None:
    violations: list[str] = []
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
            match = ACTION_REFERENCE.fullmatch(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if not PINNED_ACTION.fullmatch(reference):
                violations.append(f"{workflow.relative_to(ROOT)}:{line_number}: {reference}")
    assert violations == []


def test_alerted_zenodo_workflow_uses_expected_pinned_actions() -> None:
    workflow = (ROOT / ".github" / "workflows" / "preserve-foi-process-zenodo.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count("actions/checkout@11d5960a326750d5838078e36cf38b85af677262") == 2
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in workflow
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in workflow
