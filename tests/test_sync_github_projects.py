"""Tests for the GitHub Projects sync and best-practices helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path


def load_script():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "sync_github_projects.py"
    spec = importlib.util.spec_from_file_location("sync_github_projects", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sync_github_projects.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_model_report_marks_expected_workflows(monkeypatch) -> None:
    script = load_script()
    snapshots = {
        1: {
            "id": "project-1",
            "title": "rulespec-nz coverage ledger",
            "shortDescription": "rulespec board",
            "views": {"totalCount": 1, "nodes": [{"name": "View 1"}]},
            "workflows": {
                "totalCount": 6,
                "nodes": [{"name": name} for name in script.EXPECTED_WORKFLOWS],
            },
            "statusUpdates": {"totalCount": 2},
            "fields": {"nodes": [{"name": "Title"}, {"name": "Status"}]},
        },
        3: {
            "id": "project-3",
            "title": "nlp-policy-nz Conductor Roadmap",
            "shortDescription": "nlp board",
            "views": {"totalCount": 2, "nodes": [{"name": "View 1"}, {"name": "Roadmap"}]},
            "workflows": {
                "totalCount": 6,
                "nodes": [{"name": name} for name in script.EXPECTED_WORKFLOWS],
            },
            "statusUpdates": {"totalCount": 1},
            "fields": {"nodes": [{"name": "Title"}, {"name": "Status"}]},
        },
        4: {
            "id": "project-4",
            "title": "Rare Insights on Open Policy from Aotearoa",
            "shortDescription": "RIOPA umbrella board",
            "views": {"totalCount": 1, "nodes": [{"name": "View 1"}]},
            "workflows": {
                "totalCount": 6,
                "nodes": [{"name": name} for name in script.EXPECTED_WORKFLOWS],
            },
            "statusUpdates": {"totalCount": 0},
            "fields": {"nodes": [{"name": "Title"}, {"name": "Mirror source"}]},
        },
    }

    monkeypatch.setattr(script, "load_project_snapshot", lambda owner, number: snapshots[number])

    report = script.project_model_report(owner="edithatogo", project_numbers=(1, 3, 4))

    assert report[0]["has_expected_workflows"] is True
    assert report[1]["view_count"] == 2
    assert report[2]["field_count"] == 2
    assert report[2]["status_updates"] == 0


def test_graphql_field_and_status_mutations_are_used(monkeypatch) -> None:
    script = load_script()
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_run_graphql(query: str, **variables: object) -> dict[str, object]:
        calls.append((query, variables))
        return {}

    monkeypatch.setattr(script, "run_graphql", fake_run_graphql)

    script.set_item_single_select_field(
        project_id="project-id",
        item_id="item-id",
        field_id="field-id",
        option_id="option-id",
    )
    script.create_project_status_update(
        project_id="project-id",
        body="sync complete",
        status="ON_TRACK",
    )

    assert "updateProjectV2ItemFieldValue" in calls[0][0]
    assert calls[0][1]["optionId"] == "option-id"
    assert "createProjectV2StatusUpdate" in calls[1][0]
    assert calls[1][1]["status"] == "ON_TRACK"


def test_main_writes_report_and_status_update(tmp_path: Path, monkeypatch) -> None:
    script = load_script()
    report_path = tmp_path / "project-sync-report.json"
    project_items: dict[int, list[dict[str, object]]] = {
        1: [{"content": {"url": "https://example.com/rulespec-1"}}],
        3: [{"content": {"url": "https://example.com/nlp-1"}}],
        4: [{"id": "target-1", "content": {"url": "https://example.com/rulespec-1"}}],
    }
    added: list[str] = []
    tagged: list[tuple[str, str]] = []
    metadata_calls: list[str] = []
    status_updates: list[str] = []

    monkeypatch.setattr(
        script,
        "parse_args",
        lambda: Namespace(
            owner="edithatogo",
            target_project=4,
            source_projects=[1, 3],
            source_repos=["edithatogo/fyi-archive"],
            apply=True,
            no_metadata=False,
            status_update=True,
            report_output=str(report_path),
        ),
    )
    monkeypatch.setattr(script, "load_project_id", lambda owner, number: "project-id")
    monkeypatch.setattr(
        script,
        "ensure_single_select_field",
        lambda **kwargs: (
            "field-id",
            {
                "rulespec-nz": "option-rulespec",
                "nlp-policy-nz": "option-nlp",
                "fyi-archive": "option-fyi",
                "other": "option-other",
            },
        ),
    )
    monkeypatch.setattr(
        script,
        "load_project_items",
        lambda owner, number: project_items[number],
    )
    monkeypatch.setattr(
        script,
        "load_repo_issue_urls",
        lambda repo: ["https://example.com/fyi-1"],
    )
    monkeypatch.setattr(
        script,
        "load_repo_pull_request_urls",
        lambda repo: ["https://example.com/fyi-pr-1"],
    )
    monkeypatch.setattr(
        script,
        "project_model_report",
        lambda **kwargs: [{"project_number": 4, "view_count": 1, "workflow_count": 6}],
    )

    def fake_add_item_to_project(*, owner: str, project: int, url: str) -> None:
        added.append(url)
        project_items[project].append({"id": f"new-{len(added)}", "content": {"url": url}})

    def fake_set_item_single_select_field(
        *, project_id: str, item_id: str, field_id: str, option_id: str
    ) -> None:
        _ = (project_id, item_id, field_id)
        tagged.append((item_id, option_id))

    def fake_ensure_project_metadata(*, project_id: str) -> None:
        metadata_calls.append(project_id)

    def fake_create_project_status_update(
        *, project_id: str, body: str, status: str = "ON_TRACK"
    ) -> None:
        _ = project_id
        status_updates.append(f"{status}:{body}")

    monkeypatch.setattr(script, "add_item_to_project", fake_add_item_to_project)
    monkeypatch.setattr(script, "set_item_single_select_field", fake_set_item_single_select_field)
    monkeypatch.setattr(script, "ensure_project_metadata", fake_ensure_project_metadata)
    monkeypatch.setattr(script, "create_project_status_update", fake_create_project_status_update)

    exit_code = script.main()

    assert exit_code == 0
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["missing_count"] == 3
    assert report["project_model"][0]["view_count"] == 1
    assert added == [
        "https://example.com/nlp-1",
        "https://example.com/fyi-1",
        "https://example.com/fyi-pr-1",
    ]
    assert tagged
    assert metadata_calls == ["project-id"]
    assert len(status_updates) == 1
    assert status_updates[0].startswith("ON_TRACK:")
