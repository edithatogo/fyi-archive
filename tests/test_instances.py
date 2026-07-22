"""Tests for multi-instance archive registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fyi_archive.cli import app
from fyi_archive.instances import (
    DEFAULT_INSTANCE_ID,
    get_instance,
    known_sources,
    list_instances,
    resolve_instance,
)
from fyi_archive.manifest import assemble_manifest, build_manifest, validate_manifest
from fyi_archive.seed import SeedCaps, SeedRequest, capture_with_fyi_cli


def test_default_instance_is_nz() -> None:
    instance = get_instance()
    assert instance.id == DEFAULT_INSTANCE_ID
    assert instance.source == "https://fyi.org.nz/"
    assert instance.rate_limit_name == "archive-discovery-nz-fyi"


def test_au_rtk_instance_catalog_entry() -> None:
    instance = get_instance("au-rtk")
    assert instance.capture_base_url() == "https://www.righttoknow.org.au"
    assert instance.source == "https://www.righttoknow.org.au/"
    assert instance.hf_repo_id == "edithatogo/rtk-archive-au"
    assert instance.rate_limit_name == "archive-discovery-au-rtk"
    assert instance.source in known_sources()
    assert "authority_catalog" in instance.source_modes
    assert instance.search_feed_url().endswith("/search/all?output=json&page=1")


def test_unknown_instance_raises() -> None:
    with pytest.raises(ValueError, match="Unknown archive instance"):
        get_instance("no-such-instance")


def test_resolve_instance_base_url_override() -> None:
    instance = resolve_instance(
        instance_id="au-rtk",
        base_url="https://www.righttoknow.org.au/",
    )
    assert instance.id == "au-rtk"
    assert instance.capture_base_url() == "https://www.righttoknow.org.au"
    assert instance.source == "https://www.righttoknow.org.au/"


def test_list_instances_includes_nz_and_au() -> None:
    ids = {item.id for item in list_instances()}
    assert "nz-fyi" in ids
    assert "au-rtk" in ids


def test_historical_only_deployments_are_not_live_enabled() -> None:
    historical = [item for item in list_instances() if item.status == "historical-only"]
    assert len(historical) == 15
    assert all("internet_archive" in item.source_modes for item in historical)
    assert all("live_api" not in item.source_modes for item in historical)


@pytest.mark.parametrize(
    ("instance_id", "base_url", "catalog_url", "country", "locale"),
    [
        (
            "se-handlingar",
            "https://handlingar.se",
            "https://handlingar.se/body/all-authorities.csv",
            "SE",
            "sv-SE",
        ),
        (
            "ua-dostup",
            "https://dostup.org.ua",
            "https://dostup.org.ua/body/all-authorities.csv",
            "UA",
            "uk-UA",
        ),
        (
            "uy-quesabes",
            "https://quesabes.org",
            "https://quesabes.org/body/all-authorities.csv",
            "UY",
            "es-UY",
        ),
        (
            "ge-askgov",
            "https://askgov.ge",
            "https://askgov.ge/body/all-authorities.csv",
            "GE",
            "ka-GE",
        ),
    ],
)
def test_working_alaveteli_instance_catalog_entries(
    instance_id: str, base_url: str, catalog_url: str, country: str, locale: str
) -> None:
    instance = get_instance(instance_id)
    assert instance.capture_base_url() == base_url
    assert instance.catalog_url == catalog_url
    assert instance.country == country
    assert instance.locale == locale
    assert instance.status == "experimental"
    assert instance.source in known_sources()


def test_build_manifest_au_with_jurisdiction() -> None:
    records = [
        {
            "request_id": 1,
            "url_title": "request-1",
            "title": "t",
            "authority": "body",
            "state": "successful",
            "html_captured": False,
            "attachments": [],
            "warc_record_ids": [],
            "content_sha256": "a" * 64,
        }
    ]
    manifest = build_manifest(
        records,
        "1.0.0",
        instance_id="au-rtk",
        jurisdiction="nsw",
    )
    validate_manifest(manifest)
    assert manifest["meta"]["instance_id"] == "au-rtk"
    assert manifest["meta"]["source"] == "https://www.righttoknow.org.au/"
    assert manifest["meta"]["jurisdiction"] == "NSW"


def test_validate_legacy_nz_manifest_without_instance_id() -> None:
    manifest = {
        "meta": {
            "generated_at": "2026-07-01T00:00:00+00:00",
            "source": "https://fyi.org.nz/",
            "version": "0.5.3",
            "record_count": 1,
        },
        "requests": [
            {
                "request_id": 1,
                "url_title": "r-1",
                "content_sha256": "b" * 64,
            }
        ],
    }
    validate_manifest(manifest)


def test_validate_rejects_source_instance_mismatch() -> None:
    manifest = {
        "meta": {
            "generated_at": "2026-07-01T00:00:00+00:00",
            "source": "https://fyi.org.nz/",
            "instance_id": "au-rtk",
            "version": "0.5.3",
            "record_count": 0,
        },
        "requests": [],
    }
    with pytest.raises(ValueError, match="does not match instance"):
        validate_manifest(manifest)


def test_assemble_manifest_instance_id(tmp_path: Path) -> None:
    derived = tmp_path / "derived"
    derived.mkdir()
    (derived / "1.json").write_text(
        json.dumps({
            "request_id": 1,
            "url_title": "request-1",
            "title": "t",
            "authority": "A",
        }),
        encoding="utf-8",
    )
    manifest = assemble_manifest(
        derived_dir=derived,
        manifest_path=tmp_path / "m.json",
        parquet_path=tmp_path / "m.parquet",
        authorities_path=tmp_path / "a.json",
        fyi_cli_version="1.0.0",
        instance_id="au-rtk",
        jurisdiction="NSW",
    )
    assert manifest["meta"]["instance_id"] == "au-rtk"
    assert manifest["meta"]["jurisdiction"] == "NSW"


def test_seed_cli_dry_run_reports_au_instance(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "seed",
            "run",
            "--dry-run",
            "--max-requests",
            "1",
            "--instance",
            "au-rtk",
            "--ledger-path",
            str(tmp_path / "data" / "_state" / "test-au-ledger.jsonl"),
            "--data-dir",
            str(tmp_path / "data"),
            "--derived-dir",
            str(tmp_path / "data" / "derived" / "test-au"),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["instance_id"] == "au-rtk"
    assert payload["base_url"] == "https://www.righttoknow.org.au"
    assert payload["rate_limit_name"] == "archive-discovery-au-rtk"


def test_capture_with_fyi_cli_includes_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[list[str]] = []

    class Completed:
        pid = 1
        returncode = 0
        stdout = json.dumps({"derived_path": "data/raw/1/request.json"})

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            return self.stdout, ""

    def fake_popen(command: list[str], **kwargs: object) -> Completed:
        recorded.append(list(command))
        return Completed()

    monkeypatch.setattr("fyi_archive.seed.subprocess.Popen", fake_popen)
    summary = capture_with_fyi_cli(
        SeedRequest(request_id=42, url_title="r-42"),
        Path("data"),
        Path("dist"),
        SeedCaps(),
        ["--base-url", "https://www.righttoknow.org.au"],
    )
    assert summary["derived_path"] == "data/raw/1/request.json"
    base_url_index = recorded[0].index("--base-url")
    assert recorded[0][base_url_index + 1] == "https://www.righttoknow.org.au"


def test_instance_seed_cap_default() -> None:
    instance = get_instance("nz-fyi")
    assert instance.seed_cap == 1000


def test_instance_seed_cap_all_instances() -> None:
    for instance in list_instances():
        assert instance.seed_cap == 1000


def test_capture_with_fyi_cli_passes_rate_limiting_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[list[str]] = []

    class Completed:
        pid = 1
        returncode = 0
        stdout = json.dumps({"derived_path": "data/raw/1/request.json"})

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            return self.stdout, ""

    def fake_popen(command: list[str], **kwargs: object) -> Completed:
        recorded.append(list(command))
        return Completed()

    monkeypatch.setattr("fyi_archive.seed.subprocess.Popen", fake_popen)
    capture_with_fyi_cli(
        SeedRequest(request_id=1, url_title="r-1"),
        Path("data"),
        Path("dist"),
        SeedCaps(),
        [
            "--base-url",
            "https://fyi.org.nz",
            "--delay-seconds",
            "1.5",
            "--db",
            "capture.db",
            "--rate-limit-name",
            "archive-capture-nz-fyi",
        ],
    )
    cmd = recorded[0]
    assert cmd[cmd.index("--delay-seconds") + 1] == "1.5"
    assert cmd[cmd.index("--db") + 1] == "capture.db"
    assert cmd[cmd.index("--rate-limit-name") + 1] == "archive-capture-nz-fyi"


def test_seed_cli_dry_run_passes_rate_limiting(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "seed",
            "run",
            "--dry-run",
            "--max-requests",
            "1",
            "--min-interval",
            "2.0",
            "--concurrency",
            "4",
            "--ledger-path",
            str(tmp_path / "data" / "_state" / "test-rl-ledger.jsonl"),
            "--data-dir",
            str(tmp_path / "data"),
            "--derived-dir",
            str(tmp_path / "data" / "derived" / "test-rl"),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["processed"] == 1


@pytest.mark.parametrize(
    ("instance_id", "expected_url"),
    [
        ("au-rtk", "https://www.righttoknow.org.au"),
        ("uk-wdtk", "https://www.whatdotheyknow.com"),
        ("ie-myrighttoknow", "https://www.myrighttoknow.org"),
    ],
)
def test_seed_cli_dry_run_with_instances(
    tmp_path: Path, instance_id: str, expected_url: str
) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "seed",
            "run",
            "--dry-run",
            "--max-requests",
            "1",
            "--instance",
            instance_id,
            "--ledger-path",
            str(tmp_path / "data" / "_state" / f"test-{instance_id}-ledger.jsonl"),
            "--data-dir",
            str(tmp_path / "data"),
            "--derived-dir",
            str(tmp_path / "data" / "derived" / f"test-{instance_id}"),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["instance_id"] == instance_id
    assert payload["base_url"] == expected_url
