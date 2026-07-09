#!/usr/bin/env python3
"""Mirror issue and pull-request items into the RIOPA umbrella project.

GitHub Projects v2 cannot nest projects. This script keeps the umbrella project
synced by mirroring issue / PR URLs from the source projects into the target
project. It is idempotent and can run in dry-run mode for verification.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

DEFAULT_OWNER = "edithatogo"
DEFAULT_TARGET_PROJECT = 4
DEFAULT_SOURCE_PROJECTS = (1, 3)
DEFAULT_SOURCE_REPOS = ("edithatogo/fyi-archive",)
DEFAULT_MIRROR_FIELD_NAME = "Mirror source"
DEFAULT_MIRROR_FIELD_OPTIONS = ("rulespec-nz", "nlp-policy-nz", "fyi-archive", "other")
DEFAULT_PROJECT_README = (
    "# RIOPA\n\n"
    "Umbrella project for Rare Insights on Open Policy from Aotearoa.\n\n"
    "This board mirrors issue and pull-request items from the fyi-archive repo "
    "board and the sibling project boards for nlp-policy-nz and rulespec-nz. "
    "GitHub Projects does not support true nested projects, so synchronization "
    "is done at the item level. Built-in project workflows handle auto-add, "
    "auto-close, and auto-archive; the custom sync is limited to cross-project "
    "portfolio mirroring plus GraphQL field and status updates."
)
DEFAULT_PROJECT_DESCRIPTION = (
    "RIOPA umbrella board mirroring fyi-archive plus sibling project boards; "
    "GitHub Projects cannot nest projects, so this board is kept in sync by "
    "mirrored issue and PR items. GitHub-native workflows and status updates "
    "cover lifecycle management; the custom sync only handles portfolio sync."
)
EXPECTED_WORKFLOWS = (
    "Auto-add sub-issues to project",
    "Auto-close issue",
    "Item added to project",
    "Item closed",
    "Pull request linked to issue",
    "Pull request merged",
)


@dataclass(frozen=True)
class SyncSource:
    """One logical source of mirrored project item URLs."""

    label: str
    urls: tuple[str, ...]


def run_gh(args: list[str]) -> str:
    env = os.environ.copy()
    env.setdefault("GH_PAGER", "cat")
    env.setdefault("GH_NO_UPDATE_NOTIFIER", "1")
    completed = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return completed.stdout


def run_graphql(query: str, **variables: object) -> dict[str, object]:
    args = ["api", "graphql", "-f", f"query={' '.join(query.split())}"]
    for key, value in variables.items():
        rendered = ("true" if value else "false") if isinstance(value, bool) else str(value)
        args.extend(["-F", f"{key}={rendered}"])
    payload = json.loads(run_gh(args))
    errors = payload.get("errors")
    if errors:
        raise RuntimeError(f"GraphQL request failed: {errors}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("GraphQL response missing data")
    return data


def mapping_or_empty(value: object) -> dict[str, object]:
    """Return value as a JSON object mapping when possible."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def list_or_empty(value: object) -> list[object]:
    """Return value as a JSON array when possible."""
    return cast("list[object]", value) if isinstance(value, list) else []


def load_project_items(*, owner: str, number: int) -> list[dict[str, object]]:
    payload = run_gh(
        [
            "project",
            "item-list",
            str(number),
            "--owner",
            owner,
            "--limit",
            "1000",
            "--format",
            "json",
        ]
    )
    data = json.loads(payload)
    return list(data.get("items", []))


def load_project_snapshot(*, owner: str, number: int) -> dict[str, object]:
    data = run_graphql(
        """
        query($login: String!, $number: Int!) {
          user(login: $login) {
            projectV2(number: $number) {
              id
              title
              shortDescription
              readme
              views(first: 20) {
                totalCount
                nodes {
                  id
                  name
                  layout
                  number
                }
              }
              workflows(first: 20) {
                totalCount
                nodes {
                  id
                  name
                  enabled
                  number
                }
              }
              statusUpdates(first: 20) {
                totalCount
                nodes {
                  id
                  body
                  status
                  createdAt
                }
              }
              fields(first: 50) {
                nodes {
                  __typename
                  ... on ProjectV2FieldCommon {
                    name
                  }
                  ... on ProjectV2SingleSelectField {
                    name
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """,
        login=owner,
        number=number,
    )
    user = mapping_or_empty(data.get("user"))
    project = user.get("projectV2")
    if not isinstance(project, dict):
        raise RuntimeError(f"Project {number} not found for {owner}")
    return cast("dict[str, object]", project)


def load_project_id(*, owner: str, number: int) -> str:
    payload = run_gh(["project", "view", str(number), "--owner", owner, "--format", "json"])
    data = json.loads(payload)
    return str(data["id"])


def load_project_fields(*, owner: str, number: int) -> list[dict[str, object]]:
    payload = run_gh(["project", "field-list", str(number), "--owner", owner, "--format", "json"])
    data = json.loads(payload)
    return list(data.get("fields", []))


def load_repo_issue_urls(*, repo: str) -> list[str]:
    payload = run_gh(
        [
            "issue",
            "list",
            "-R",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "url",
        ]
    )
    data = json.loads(payload)
    return [str(item["url"]) for item in data if item.get("url")]


def load_repo_pull_request_urls(*, repo: str) -> list[str]:
    payload = run_gh(
        [
            "pr",
            "list",
            "-R",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "url",
        ]
    )
    data = json.loads(payload)
    return [str(item["url"]) for item in data if item.get("url")]


def extract_content_url(item: dict[str, object]) -> str | None:
    content = item.get("content")
    if isinstance(content, dict):
        url = content.get("url")
        if isinstance(url, str) and url:
            return url
    return None


def ensure_single_select_field(
    *, owner: str, project: int, field_name: str, options: tuple[str, ...]
) -> tuple[str, dict[str, str]]:
    fields = load_project_fields(owner=owner, number=project)
    for field in fields:
        if field.get("name") == field_name:
            options_data = list_or_empty(field.get("options"))
            option_map = {
                str(option.get("name")): str(option.get("id"))
                for option in options_data
                if isinstance(option, dict) and option.get("name") and option.get("id")
            }
            return str(field["id"]), option_map

    run_gh(
        [
            "project",
            "field-create",
            str(project),
            "--owner",
            owner,
            "--name",
            field_name,
            "--data-type",
            "SINGLE_SELECT",
            "--single-select-options",
            ",".join(options),
        ]
    )
    fields = load_project_fields(owner=owner, number=project)
    for field in fields:
        if field.get("name") == field_name:
            options_data = list_or_empty(field.get("options"))
            option_map = {
                str(option.get("name")): str(option.get("id"))
                for option in options_data
                if isinstance(option, dict) and option.get("name") and option.get("id")
            }
            return str(field["id"]), option_map
    raise RuntimeError(f"Unable to create or locate project field {field_name!r}")


def add_item_to_project(*, owner: str, project: int, url: str) -> None:
    run_gh(["project", "item-add", str(project), "--owner", owner, "--url", url])


def set_item_single_select_field(
    *, project_id: str, item_id: str, field_id: str, option_id: str
) -> None:
    run_graphql(
        """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(
            input: {
              projectId: $projectId
              itemId: $itemId
              fieldId: $fieldId
              value: { singleSelectOptionId: $optionId }
            }
          ) {
            projectV2Item {
              id
            }
          }
        }
        """,
        projectId=project_id,
        itemId=item_id,
        fieldId=field_id,
        optionId=option_id,
    )


def ensure_project_metadata(*, project_id: str) -> None:
    run_graphql(
        """
        mutation($projectId: ID!, $shortDescription: String!, $readme: String!, $public: Boolean!) {
          updateProjectV2(
            input: {
              projectId: $projectId
              shortDescription: $shortDescription
              readme: $readme
              public: $public
            }
          ) {
            projectV2 {
              id
            }
          }
        }
        """,
        projectId=project_id,
        shortDescription=DEFAULT_PROJECT_DESCRIPTION,
        readme=DEFAULT_PROJECT_README,
        public=False,
    )


def create_project_status_update(*, project_id: str, body: str, status: str = "ON_TRACK") -> None:
    run_graphql(
        """
        mutation($projectId: ID!, $body: String!, $status: ProjectV2StatusUpdateStatus!) {
          createProjectV2StatusUpdate(
            input: {
              projectId: $projectId
              body: $body
              status: $status
            }
          ) {
            statusUpdate {
              id
            }
          }
        }
        """,
        projectId=project_id,
        body=body,
        status=status,
    )


def build_sources(
    *, owner: str, source_projects: Iterable[int], source_repos: Iterable[str]
) -> list[SyncSource]:
    sources: list[SyncSource] = []
    for project in source_projects:
        urls = tuple(
            url
            for item in load_project_items(owner=owner, number=project)
            if (url := extract_content_url(item)) is not None
        )
        label = {1: "rulespec-nz", 3: "nlp-policy-nz"}.get(project, f"project-{project}")
        sources.append(SyncSource(label=label, urls=urls))
    for repo in source_repos:
        source_label = repo.split("/", 1)[-1]
        repo_urls = tuple(
            dict.fromkeys(
                [*load_repo_issue_urls(repo=repo), *load_repo_pull_request_urls(repo=repo)],
            ),
        )
        sources.append(SyncSource(label=source_label, urls=repo_urls))
    return sources


def unique_urls(sources: Iterable[SyncSource]) -> tuple[list[str], dict[str, str]]:
    seen: set[str] = set()
    ordered: list[str] = []
    source_by_url: dict[str, str] = {}
    for source in sources:
        for url in source.urls:
            if url not in seen:
                seen.add(url)
                ordered.append(url)
                source_by_url[url] = source.label
    return ordered, source_by_url


def project_model_report(*, owner: str, project_numbers: Iterable[int]) -> list[dict[str, object]]:
    report = []
    for project_number in project_numbers:
        snapshot = load_project_snapshot(owner=owner, number=project_number)
        workflows_data = mapping_or_empty(snapshot.get("workflows"))
        views_data = mapping_or_empty(snapshot.get("views"))
        fields_data = mapping_or_empty(snapshot.get("fields"))
        status_updates_data = mapping_or_empty(snapshot.get("statusUpdates"))
        workflows = [
            str(item.get("name"))
            for item in list_or_empty(workflows_data.get("nodes"))
            if isinstance(item, dict) and item.get("name")
        ]
        views = [
            str(item.get("name"))
            for item in list_or_empty(views_data.get("nodes"))
            if isinstance(item, dict) and item.get("name")
        ]
        fields = [
            str(item.get("name"))
            for item in list_or_empty(fields_data.get("nodes"))
            if isinstance(item, dict) and item.get("name")
        ]
        report.append(
            {
                "project_number": project_number,
                "project_id": snapshot.get("id"),
                "title": snapshot.get("title"),
                "short_description": snapshot.get("shortDescription"),
                "views": views,
                "view_count": views_data.get("totalCount", len(views)),
                "workflows": workflows,
                "workflow_count": workflows_data.get("totalCount", len(workflows)),
                "fields": fields,
                "field_count": len(fields),
                "status_updates": status_updates_data.get("totalCount", 0),
                "has_expected_workflows": all(name in workflows for name in EXPECTED_WORKFLOWS),
            }
        )
    return report


def build_status_update_body(
    *, target_project: int, mirrored_count: int, remaining_count: int
) -> str:
    lines = [
        f"RIOPA sync report for project {target_project}",
        f"- mirrored items: {mirrored_count}",
        f"- remaining gaps: {remaining_count}",
        "- GraphQL handles field updates and status updates; the custom script is limited to cross-project portfolio sync.",
        "- GitHub-native auto-add, auto-close, and auto-archive workflows remain the lifecycle layer.",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--target-project", type=int, default=DEFAULT_TARGET_PROJECT)
    parser.add_argument(
        "--source-project",
        type=int,
        action="append",
        dest="source_projects",
        help="Source project number to mirror. Repeatable.",
    )
    parser.add_argument(
        "--source-repo",
        action="append",
        dest="source_repos",
        help="Source repository whose issues should be mirrored. Repeatable.",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Write missing items into the target project."
    )
    parser.add_argument(
        "--no-metadata", action="store_true", help="Skip project description/readme updates."
    )
    parser.add_argument(
        "--status-update",
        action="store_true",
        help="Create a GitHub Projects status update after apply.",
    )
    parser.add_argument("--report-output", help="Write a JSON project report to this path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_projects = tuple(args.source_projects or DEFAULT_SOURCE_PROJECTS)
    source_repos = tuple(args.source_repos or DEFAULT_SOURCE_REPOS)

    sources = build_sources(
        owner=args.owner, source_projects=source_projects, source_repos=source_repos
    )
    target_project_id = load_project_id(owner=args.owner, number=args.target_project)
    mirror_field_id, mirror_option_ids = ensure_single_select_field(
        owner=args.owner,
        project=args.target_project,
        field_name=DEFAULT_MIRROR_FIELD_NAME,
        options=DEFAULT_MIRROR_FIELD_OPTIONS,
    )
    target_items = load_project_items(owner=args.owner, number=args.target_project)
    target_urls = {url for item in target_items if (url := extract_content_url(item)) is not None}
    desired_urls, source_by_url = unique_urls(sources)
    missing_urls = [url for url in desired_urls if url not in target_urls]
    report = {
        "target_project": args.target_project,
        "mirrored_count": len(target_urls),
        "source_counts": {source.label: len(source.urls) for source in sources},
        "unique_source_count": len(desired_urls),
        "missing_count": len(missing_urls),
        "source_projects": source_projects,
        "source_repos": list(source_repos),
        "project_model": project_model_report(
            owner=args.owner, project_numbers=(1, 3, args.target_project)
        ),
    }

    print(f"Target project {args.target_project}: {len(target_urls)} mirrored items")
    for source in sources:
        print(f"{source.label}: {len(source.urls)} items")
    print(f"Unique source URLs: {len(desired_urls)}")
    print(f"Missing from target: {len(missing_urls)}")

    if args.report_output:
        out_path = Path(args.report_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(out_path)

    if not args.apply:
        for url in missing_urls:
            print(f"DRY-RUN add {url}")
        return 0

    if not args.no_metadata:
        ensure_project_metadata(project_id=target_project_id)

    added = 0
    for url in missing_urls:
        add_item_to_project(owner=args.owner, project=args.target_project, url=url)
        added += 1
        print(f"ADDED {url}")

    final_items = load_project_items(owner=args.owner, number=args.target_project)
    item_id_by_url = {}
    for item in final_items:
        content = item.get("content")
        if not isinstance(content, dict):
            continue
        url = content.get("url")
        if isinstance(url, str) and url:
            item_id_by_url[url] = str(item["id"])

    for url in desired_urls:
        item_id = item_id_by_url.get(url)
        source_label = source_by_url.get(url, "other")
        option_id = mirror_option_ids.get(source_label, mirror_option_ids.get("other"))
        if not item_id or not option_id:
            print(f"SKIP FIELD {url}")
            continue
        set_item_single_select_field(
            project_id=target_project_id,
            item_id=item_id,
            field_id=mirror_field_id,
            option_id=option_id,
        )
        print(f"TAGGED {url} -> {source_label}")

    final_urls = {url for item in final_items if (url := extract_content_url(item)) is not None}
    remaining = [url for url in desired_urls if url not in final_urls]

    print(f"Added: {added}")
    print(f"Final target count: {len(final_urls)}")
    print(f"Remaining gaps: {len(remaining)}")
    if args.status_update:
        create_project_status_update(
            project_id=target_project_id,
            body=build_status_update_body(
                target_project=args.target_project,
                mirrored_count=len(final_urls),
                remaining_count=len(remaining),
            ),
        )
        print("PROJECT STATUS UPDATE POSTED")
    if remaining:
        for url in remaining:
            print(f"UNSYNCED {url}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
