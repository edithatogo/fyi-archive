from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.instances import list_instances
from fyi_archive.internet_archive_sites import (
    internet_archive_matrix,
    list_internet_archive_sites,
)


def test_site_inventory_covers_registered_and_non_alaveteli_sites() -> None:
    sites = list_internet_archive_sites()
    ids = {site.id for site in sites}
    registered = {
        instance.id for instance in list_instances() if "internet_archive" in instance.source_modes
    }
    assert registered <= ids
    assert {
        "ca-federal-atip",
        "us-federal-foia",
        "za-paia",
        "de-fragdenstaat",
        "es-tuderechoasaber",
        "ar-information-publica",
    } <= ids
    assert len(ids) == len(sites)
    assert all("://" not in pattern for site in sites for pattern in site.url_patterns)


def test_site_matrix_is_json_serializable_and_separate() -> None:
    matrix = internet_archive_matrix()
    assert json.loads(json.dumps(matrix)) == matrix
    assert all(row["id"] and row["url_patterns"] for row in matrix)


def test_site_matrix_can_select_one_site() -> None:
    matrix = internet_archive_matrix(site_id="au-rtk")
    assert [row["id"] for row in matrix] == ["au-rtk"]


def test_site_matrix_can_select_a_bounded_batch_in_configured_order() -> None:
    matrix = internet_archive_matrix(site_ids=("nz-fyi", "ca-federal-atip"))
    assert [row["id"] for row in matrix] == ["ca-federal-atip", "nz-fyi"]


def test_site_matrix_rejects_unknown_site() -> None:
    with pytest.raises(ValueError, match=r"configured ids:.*au-rtk"):
        internet_archive_matrix(site_id="not-configured")


@pytest.mark.parametrize(
    ("site_id", "site_ids", "message"),
    [
        ("au-rtk", ("nz-fyi",), "mutually exclusive"),
        (None, (), "at least one"),
        (None, ("nz-fyi", "nz-fyi"), "must be unique"),
    ],
)
def test_site_matrix_rejects_ambiguous_or_empty_target_batches(
    site_id: str | None, site_ids: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        internet_archive_matrix(site_id=site_id, site_ids=site_ids)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"schema": "wrong", "sites": []}, "unsupported"),
        ({"schema": "fyi-archive.additional-foi-sites.v1"}, "array"),
        (
            {"schema": "fyi-archive.additional-foi-sites.v1", "sites": ["bad"]},
            "must be an object",
        ),
        (
            {
                "schema": "fyi-archive.additional-foi-sites.v1",
                "sites": [{"id": "../bad", "kind": "x", "country": "X", "url_patterns": ["x/*"]}],
            },
            "invalid id",
        ),
        (
            {
                "schema": "fyi-archive.additional-foi-sites.v1",
                "sites": [{"id": "good", "kind": "", "country": "X", "url_patterns": ["x/*"]}],
            },
            "requires kind",
        ),
        (
            {
                "schema": "fyi-archive.additional-foi-sites.v1",
                "sites": [{"id": "good", "kind": "x", "country": "", "url_patterns": ["x/*"]}],
            },
            "requires country",
        ),
        (
            {
                "schema": "fyi-archive.additional-foi-sites.v1",
                "sites": [
                    {
                        "id": "good",
                        "kind": "x",
                        "country": "X",
                        "url_patterns": ["https://example.test/*"],
                    }
                ],
            },
            "host-relative",
        ),
    ],
)
def test_invalid_additional_site_registry_fails_closed(
    tmp_path: Path, document: dict[str, object], message: str
) -> None:
    path = tmp_path / "sites.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        list_internet_archive_sites(path)


def test_duplicate_site_ids_fail_closed(tmp_path: Path) -> None:
    known_id = list_instances()[0].id
    path = tmp_path / "sites.json"
    path.write_text(
        json.dumps(
            {
                "schema": "fyi-archive.additional-foi-sites.v1",
                "sites": [
                    {
                        "id": known_id,
                        "kind": "non_alaveteli",
                        "country": "X",
                        "url_patterns": ["example.test/*"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        list_internet_archive_sites(path)


def test_workflow_is_scheduled_separate_and_origin_free() -> None:
    workflow = Path(".github/workflows/foi_site_internet_archive.yml").read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "internet_archive_matrix" in workflow
    assert "site_ids:" in workflow
    assert "foi-site-wayback-${{ matrix.site.id }}-${{ github.run_id }}" in workflow
    assert "origin_contacted" in workflow
    assert "contents: read" in workflow
    assert "HF_TOKEN" not in workflow
