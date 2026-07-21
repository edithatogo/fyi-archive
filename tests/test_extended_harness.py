"""High-signal edge and integration coverage for the archive harness."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from fyi_archive.backfill_state_codec import decode_state, encode_state, state_body_from_state
from fyi_archive.cli import app
from fyi_archive.commands import backfill as backfill_command
from fyi_archive.commands import discover as discover_command
from fyi_archive.commands import doctor as doctor_command
from fyi_archive.commands import publish as publish_command
from fyi_archive.commands import sync as sync_command
from fyi_archive.manifest import (
    build_manifest,
    load_derived_records,
    normalize_authority,
    normalize_request_record,
    validate_manifest,
    write_manifest_outputs,
)
from fyi_archive.nsw_seed import select_nsw_authorities, write_nsw_authority_queue
from fyi_archive.publish import osf_publish
from fyi_archive.publish.verification import (
    MirrorVerification,
    RemoteArtifact,
    append_verification_report,
    build_local_artifacts,
    checksum_matches_local,
    compare_artifacts,
    mirror_verified,
    write_verification_report,
)
from fyi_archive.seed import (
    CaptureError,
    SeedCaps,
    SeedRequest,
    cap_exceeded,
    is_transient_capture_error,
    load_ledger,
    requests_from_id_range,
    requests_from_jsonl,
    synthetic_requests,
    tail_text,
)
from fyi_archive.sync import (
    SyncState,
    changes_have_records,
    dry_run_materialize_changes,
    empty_changes,
    fyi_diff_content_sha256,
    load_changes,
    load_sync_state,
    restore_hf_dataset,
    run_fyi_cli_diff,
    run_sync,
    validate_change_entry,
    validate_changes,
    write_changes,
    write_diff_baseline_manifest,
    write_sync_state,
)


@pytest.mark.unit
def test_backfill_state_codec_round_trip_and_plain_json() -> None:
    state = {"next_id": 42, "batches": [{"label": "1-10", "status": "merged"}]}
    encoded = encode_state(state)
    assert decode_state(json.dumps(encoded)) == state
    assert decode_state(json.dumps(state)) == state
    assert json.loads(state_body_from_state(state)) == encoded


@pytest.mark.edge
@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("[]", "must be a JSON object"),
        ('{"format":"fyi-backfill-state.v1","encoding":"zlib+base64"}', "missing payload"),
    ],
)
def test_backfill_state_codec_rejects_malformed_wrappers(body: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        decode_state(body)


@pytest.mark.edge
def test_backfill_state_codec_rejects_non_object_decoded_payload() -> None:
    import base64
    import zlib

    encoded = {
        "format": "fyi-backfill-state.v1",
        "encoding": "zlib+base64",
        "payload": base64.b64encode(zlib.compress(b"[]")).decode("ascii"),
    }
    with pytest.raises(ValueError, match="decoded backfill state"):
        decode_state(json.dumps(encoded))


@pytest.mark.unit
def test_manifest_normalization_covers_scalar_defaults_and_authority_objects() -> None:
    record = normalize_request_record({"id": 7, "authority": {"name": "Ministry"}})
    assert record["request_id"] == 7
    assert record["authority"] == "Ministry"
    assert record["title"] == ""
    assert normalize_authority({"id": 12}) == "12"
    assert normalize_authority(None) == ""


@pytest.mark.integration
def test_manifest_outputs_support_au_authority_summary_and_missing_sidecars(tmp_path: Path) -> None:
    manifest = build_manifest(
        [normalize_request_record({"id": 1, "authority": "Council", "body_tag": "nsw"})],
        "1.0.0",
        instance_id="au-rtk",
        jurisdiction="nsw",
    )
    manifest_path = tmp_path / "manifest.json"
    parquet_path = tmp_path / "manifest.parquet"
    authorities_path = tmp_path / "authorities.json"
    write_manifest_outputs(
        manifest=manifest,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        authorities_path=authorities_path,
        instance_id="au-rtk",
    )
    validate_manifest(manifest)
    assert manifest["meta"]["jurisdiction"] == "NSW"
    assert json.loads(authorities_path.read_text(encoding="utf-8"))["authorities"]

    derived = tmp_path / "derived"
    request_dir = derived / "authority" / "1"
    request_dir.mkdir(parents=True)
    (request_dir / "request.json").write_text('{"id": 1, "title": "x"}', encoding="utf-8")
    assert load_derived_records(derived)[0]["html_captured"] is False


@pytest.mark.unit
def test_publication_verification_comparison_edges(tmp_path: Path) -> None:
    artifact = tmp_path / "one.bin"
    artifact.write_bytes(b"archive")
    local = build_local_artifacts([artifact])
    assert local[0].size == 7
    digest = local[0].sha256
    assert checksum_matches_local(f"sha256:{digest.upper()}", digest) is True
    assert checksum_matches_local("md5:bad", digest) is None
    assert checksum_matches_local(None, digest) is None

    results = compare_artifacts(
        local_artifacts=local,
        remote_artifacts=[RemoteArtifact(name="one.bin", size=7, checksum=digest)],
    )
    assert mirror_verified(results) is True
    missing = compare_artifacts(local_artifacts=local, remote_artifacts=[])
    assert mirror_verified(missing) is False
    assert results[0].remote_checksum == digest


@pytest.mark.integration
def test_publication_reports_append_and_replace_mirrors(tmp_path: Path) -> None:
    report_path = tmp_path / "dist/report.json"
    first = MirrorVerification(mirror="huggingface", verified=True, record_count=1)
    second = MirrorVerification(mirror="zenodo", verified=False, record_count=0)
    write_verification_report(report_path, [first])
    append_verification_report(report_path, second)
    append_verification_report(
        report_path,
        MirrorVerification(mirror="huggingface", verified=False, record_count=0),
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert {item["mirror"] for item in payload} == {"huggingface", "zenodo"}
    assert next(item for item in payload if item["mirror"] == "huggingface")["verified"] is False


@pytest.mark.unit
def test_sync_state_changes_and_validation_edges(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state = SyncState(last_successful_sync="now", last_manifest_sha256="a" * 64, record_count=2)
    write_sync_state(state_path, state)
    assert load_sync_state(state_path) == state
    assert load_sync_state(tmp_path / "missing.json") == SyncState()
    changes = empty_changes(None)
    assert changes_have_records(changes) is False
    entry = {"request_id": 1, "content_sha256": "a" * 64, "previous_sha256": None}
    validate_change_entry(entry)
    changes["added"].append(entry)
    validate_changes(changes)
    assert changes_have_records(changes) is True
    changes_path = tmp_path / "changes.json"
    write_changes(changes_path, changes)
    assert load_changes(changes_path, None)["added"] == [entry]
    with pytest.raises(ValueError, match="positive integer"):
        validate_change_entry({"request_id": 0, "content_sha256": "a" * 64})


@pytest.mark.integration
def test_sync_dry_run_materializes_added_and_updated_records(tmp_path: Path) -> None:
    generated = "2026-07-10T00:00:00+00:00"
    changes = {
        "meta": {"generated_at": generated, "since": None, "version": "0.6.0"},
        "added": [{"request_id": 1, "content_sha256": "a" * 64}],
        "updated": [{"request_id": 2, "content_sha256": "b" * 64, "url_title": "custom"}],
        "removed": [],
    }
    assert dry_run_materialize_changes(changes, tmp_path) == 2
    assert json.loads((tmp_path / "1.json").read_text(encoding="utf-8"))["state"] == "added"
    assert json.loads((tmp_path / "2.json").read_text(encoding="utf-8"))["url_title"] == "custom"


@pytest.mark.edge
def test_seed_queue_and_cap_boundaries(tmp_path: Path, monkeypatch) -> None:
    queue = tmp_path / "queue.jsonl"
    queue.write_text('\n{"request_id": 3, "title": "Three"}\n', encoding="utf-8")
    assert requests_from_jsonl(queue)[0] == SeedRequest(3, "request-3", "Three", "")
    assert [item.request_id for item in synthetic_requests(None)] == [1]
    assert [item.request_id for item in requests_from_id_range(2, 3)] == [2, 3]
    with pytest.raises(ValueError, match="positive and ordered"):
        requests_from_id_range(0, 1)
    with pytest.raises(ValueError, match="positive and ordered"):
        requests_from_id_range(3, 2)
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        '{"request_id": 1, "status": "completed"}\n{"status": "failed"}\n', encoding="utf-8"
    )
    assert load_ledger(ledger) == {1}
    assert load_ledger(tmp_path / "missing.jsonl") == set()
    assert tail_text("x" * 5, 3) == "xxx"
    assert (
        cap_exceeded(processed=1, bytes_written=0, started_at=0, caps=SeedCaps(max_requests=1))
        == "max_requests"
    )
    assert (
        cap_exceeded(processed=0, bytes_written=2, started_at=0, caps=SeedCaps(max_bytes=2))
        == "max_bytes"
    )
    monkeypatch.setattr("fyi_archive.seed.time.monotonic", lambda: 60.0)
    assert (
        cap_exceeded(
            processed=0, bytes_written=0, started_at=0, caps=SeedCaps(max_runtime_minutes=1)
        )
        == "max_runtime_minutes"
    )
    error = CaptureError(request_id=1, command=["fyi"], returncode=1, stdout="", stderr="HTTP 503")
    assert is_transient_capture_error(error) is True


@pytest.mark.integration
def test_osf_adapters_cover_listing_and_metadata_paths(monkeypatch, tmp_path: Path) -> None:
    assert osf_publish.auth_headers("token") == {"Authorization": "Bearer token"}
    responses = {
        "https://osf.test/nodes/p/children/": httpx.Response(
            200, json={"data": [{"attributes": {"title": "existing"}, "id": "c1"}]}
        ),
        "https://osf.test/nodes/p/files/": httpx.Response(
            200, json={"data": [{"id": "osfstorage", "links": {"upload": "https://upload"}}]}
        ),
        "https://osf.test/nodes/p/files/osfstorage/": httpx.Response(
            200,
            json={
                "data": [
                    {
                        "attributes": {
                            "name": "folder/a.txt",
                            "size": 4,
                            "extra": {"hashes": {"sha256": "abc"}},
                        },
                        "links": {
                            "download": "https://download",
                            "upload": "https://upload-existing",
                        },
                    },
                    {"attributes": {}, "links": {}},
                ]
            },
        ),
    }

    def with_request(response: httpx.Response, url: str) -> httpx.Response:
        response.request = httpx.Request("GET", url)
        return response

    def fake_get(url: str, **_: object) -> httpx.Response:
        return with_request(responses[url], url)

    monkeypatch.setattr(osf_publish.httpx, "get", fake_get)
    monkeypatch.setattr(
        osf_publish.httpx,
        "post",
        lambda url, **_: with_request(httpx.Response(200, json={"data": {"id": "new"}}), url),
    )
    assert (
        osf_publish.list_components(token="t", parent_id="p", api_url="https://osf.test")[0]["id"]
        == "c1"
    )
    assert (
        osf_publish.ensure_component(
            token="t", parent_id="p", title="existing", api_url="https://osf.test"
        )["data"]["id"]
        == "c1"
    )
    assert (
        osf_publish.ensure_component(
            token="t", parent_id="p", title="new", api_url="https://osf.test"
        )["data"]["id"]
        == "new"
    )
    assert (
        osf_publish.get_osfstorage_upload_url(token="t", node_id="p", api_url="https://osf.test")
        == "https://upload"
    )
    artifacts = osf_publish.list_files(token="t", node_id="p", api_url="https://osf.test")
    assert artifacts[0].name == "a.txt"
    assert artifacts[0].checksum == "sha256:abc"
    assert osf_publish.file_size({}) is None
    assert osf_publish.file_sha256({}) is None
    assert (
        osf_publish.find_file_upload_url(
            token="t", files_url="https://osf.test/nodes/p/files/osfstorage/", name="a.txt"
        )
        == "https://upload-existing"
    )
    path = tmp_path / "a.txt"
    path.write_text("data", encoding="utf-8")
    monkeypatch.setattr(
        osf_publish,
        "request_with_retry",
        lambda request: with_request(httpx.Response(200, json={"ok": True}), "https://upload"),
    )
    assert osf_publish.upload_file(token="t", upload_url="https://upload", path=path) == {
        "ok": True
    }


@pytest.mark.edge
@pytest.mark.regression
def test_changes_schema_rejects_each_invalid_shape(tmp_path: Path) -> None:
    valid = empty_changes(None)
    cases = [
        ({"added": []}, "meta"),
        (
            {
                "meta": {"generated_at": 1, "version": "x"},
                "added": [],
                "updated": [],
                "removed": [],
            },
            "generated_at",
        ),
        (
            {
                "meta": {"generated_at": "x", "version": 1},
                "added": [],
                "updated": [],
                "removed": [],
            },
            "version",
        ),
        (
            {
                "meta": {"generated_at": "x", "version": "x", "since": 1},
                "added": [],
                "updated": [],
                "removed": [],
            },
            "since",
        ),
        ({**valid, "added": {}}, "added"),
        ({**valid, "added": ["bad"]}, "Change entry"),
        ({**valid, "added": [{"request_id": 1, "content_sha256": "Z" * 64}]}, "lowercase"),
        (
            {
                **valid,
                "added": [
                    {"request_id": 1, "content_sha256": "a" * 64, "previous_sha256": "Z" * 64}
                ],
            },
            "previous_sha256",
        ),
    ]
    for changes, message in cases:
        with pytest.raises(ValueError, match=message):
            validate_changes(changes)
    assert load_changes(tmp_path / "missing.json", "later")["meta"]["since"] == "later"


@pytest.mark.integration
def test_sync_baseline_restore_and_subprocess_contract(tmp_path: Path, monkeypatch) -> None:
    derived = tmp_path / "derived" / "authority" / "1"
    derived.mkdir(parents=True)
    (derived / "request.json").write_text('{"id": 1, "title": "A"}', encoding="utf-8")
    baseline = write_diff_baseline_manifest(
        derived_dir=tmp_path / "derived", output_path=tmp_path / "baseline.json"
    )
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    assert payload["requests"][0]["content_sha256"] == fyi_diff_content_sha256({
        "id": 1,
        "title": "A",
    })

    snapshot = tmp_path / "snapshot"
    (snapshot / "manifests").mkdir(parents=True)
    (snapshot / "data/raw/requests").mkdir(parents=True)
    (snapshot / "manifests/latest_manifest.json").write_text("{}", encoding="utf-8")
    (snapshot / "data/raw/requests/1.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("fyi_archive.sync.snapshot_download", lambda **_: str(snapshot))
    restore_hf_dataset(
        repo_id="owner/data",
        token=None,
        manifest_dir=tmp_path / "restored-manifests",
        derived_dir=tmp_path / "restored",
    )
    assert (tmp_path / "restored-manifests/latest_manifest.json").exists()
    assert (tmp_path / "restored/1.json").exists()

    calls: list[list[str]] = []
    monkeypatch.setattr(
        "fyi_archive.sync.subprocess.run", lambda command, **_: calls.append(command)
    )
    run_fyi_cli_diff(
        since="now",
        derived_dir=tmp_path / "derived",
        previous_manifest=baseline,
        output_path=tmp_path / "changes.json",
        extra_args=("--strict",),
    )
    assert calls[0][-3:] == ["--since", "now", "--strict"]


@pytest.mark.e2e
def test_run_sync_non_dry_path_advances_verified_state(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"meta": {"record_count": 0}, "requests": []}', encoding="utf-8")
    changes_path = tmp_path / "changes.json"
    changes = empty_changes(None)
    monkeypatch.setattr(
        "fyi_archive.sync.run_fyi_cli_diff", lambda **_: write_changes(changes_path, changes)
    )
    result = run_sync(
        state_path=tmp_path / "state.json",
        derived_dir=tmp_path / "derived",
        manifest_path=manifest,
        parquet_path=tmp_path / "manifest.parquet",
        authorities_path=tmp_path / "authorities.json",
        changes_path=changes_path,
        fyi_cli_version="1.0.0",
        dry_run=False,
    )
    assert result["verified"] is True
    assert load_sync_state(tmp_path / "state.json").record_count == 0


@pytest.mark.edge
def test_manifest_validation_rejects_malformed_documents() -> None:
    base = {"meta": {"source": "https://fyi.org.nz/", "record_count": 0}, "requests": []}
    invalid = [
        ({}, "object 'meta'"),
        ({**base, "meta": {**base["meta"], "source": "https://unknown"}}, "one of"),
        ({**base, "meta": {**base["meta"], "instance_id": 1}}, "must be a string"),
        ({**base, "meta": {**base["meta"], "jurisdiction": 1}}, "jurisdiction"),
        ({**base, "meta": {**base["meta"], "record_count": 1}}, "record_count"),
        (
            {
                **base,
                "meta": {**base["meta"], "record_count": 1},
                "requests": [{"request_id": 0, "content_sha256": "a" * 64}],
            },
            "positive integer",
        ),
        (
            {
                **base,
                "meta": {**base["meta"], "record_count": 1},
                "requests": [{"request_id": 1, "content_sha256": "bad"}],
            },
            "64-character",
        ),
    ]
    for manifest, message in invalid:
        with pytest.raises(ValueError, match=message):
            validate_manifest(manifest)


@pytest.mark.integration
def test_publish_verify_command_handles_targets_and_validation_errors(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"meta": {"record_count": 0}, "requests": []}', encoding="utf-8")
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"x")
    with pytest.raises(Exception, match="at least one mirror"):
        publish_command.verify(root=tmp_path, manifest_path=manifest, artifact=[artifact])

    with pytest.raises(Exception, match="ZENODO_TOKEN"):
        publish_command.verify(
            root=tmp_path,
            manifest_path=manifest,
            artifact=[artifact],
            zenodo_deposition_id=1,
        )
    with pytest.raises(Exception, match="OSF_TOKEN"):
        publish_command.verify(
            root=tmp_path,
            manifest_path=manifest,
            artifact=[artifact],
            osf_node_id="node",
        )

    report = MirrorVerification(mirror="huggingface", verified=True, record_count=0)
    monkeypatch.setattr(publish_command, "verify_huggingface_dataset", lambda **_: report)
    monkeypatch.setattr(
        publish_command,
        "write_versioned_verification_bundle",
        lambda **_: {"verified": True, "mirrors": []},
    )
    publish_command.verify(
        root=tmp_path,
        manifest_path=manifest,
        artifact=[artifact],
        hf_repo_id="owner/data",
        report_path=tmp_path / "report.json",
        output_dir=tmp_path / "versions",
    )


@pytest.mark.integration
def test_targeted_publish_verification_ignores_stale_other_mirror_failure(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"meta": {"record_count": 1}, "requests": []}', encoding="utf-8")
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"x")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        '[{"mirror": "huggingface", "verified": false, "record_count": 1, '
        '"artifacts": [], "details": {}}]\n',
        encoding="utf-8",
    )
    current = MirrorVerification(mirror="osf", verified=True, record_count=1)
    monkeypatch.setattr(publish_command, "verify_osf_node", lambda **_: current)

    publish_command.verify(
        root=tmp_path,
        manifest_path=manifest,
        artifact=[artifact],
        osf_node_id="node",
        osf_token="token",
        report_path=report_path,
        output_dir=tmp_path / "versions",
    )

    aggregate = json.loads(report_path.read_text(encoding="utf-8"))
    assert {item["mirror"] for item in aggregate} == {"huggingface", "osf"}
    latest = json.loads(
        (tmp_path / "versions" / "latest_mirror_verification.json").read_text(encoding="utf-8")
    )
    assert latest["verified"] is True
    assert [item["mirror"] for item in latest["mirrors"]] == ["osf"]


def test_osf_workflow_step_clears_inherited_hf_target() -> None:
    workflow = Path(".github/workflows/publish_archives.yml").read_text(encoding="utf-8")
    osf_step = workflow[workflow.index("- name: Verify OSF mirror") :]
    osf_step = osf_step[: osf_step.index("- name: Build deterministic dry-run verification report")]
    assert 'HF_REPO_ID: ""' in osf_step


@pytest.mark.edge
def test_manifest_command_rejects_empty_merge_and_build_errors(monkeypatch) -> None:
    from fyi_archive.commands import manifest as manifest_command

    with pytest.raises(Exception, match="at least one"):
        manifest_command.merge(input_manifest=[])
    monkeypatch.setattr(
        "fyi_archive.commands.manifest.assemble_manifest",
        lambda **_: (_ for _ in ()).throw(ValueError("bad manifest")),
    )
    with pytest.raises(Exception, match="bad manifest"):
        manifest_command.build()


@pytest.mark.unit
def test_osf_retry_retries_transient_http_errors(monkeypatch) -> None:
    calls = 0

    def request() -> httpx.Response:
        nonlocal calls
        calls += 1
        response = httpx.Response(503, request=httpx.Request("GET", "https://osf.test"))
        response.raise_for_status()
        return response

    monkeypatch.setattr(osf_publish, "sleep", lambda _: None)
    with pytest.raises(httpx.HTTPStatusError):
        osf_publish.request_with_retry(request, attempts=2, backoff_seconds=0)
    assert calls == 2


@pytest.mark.integration
def test_nsw_queue_selection_is_deduplicated_and_scoped(tmp_path: Path) -> None:
    bodies = [
        {"url_name": "council", "name": "Council", "tags": ["NSW"]},
        {"slug": "council", "name": "Council duplicate", "jurisdiction": "nsw"},
        {"url_name": "victoria", "name": "Victoria", "tags": ["VIC"]},
    ]
    selected = select_nsw_authorities(bodies)
    assert [row["slug"] for row in selected] == ["council"]
    csv_style = select_nsw_authorities([
        {"URL name": "nsw-health", "Name": "NSW Health", "Tags": "state-government-nsw"}
    ])
    assert [row["slug"] for row in csv_style] == ["nsw-health"]
    assert set(csv_style[0]) == {"slug", "name", "jurisdiction"}
    bodies_path = tmp_path / "bodies.json"
    queue_path = tmp_path / "queue.json"
    bodies_path.write_text(json.dumps({"bodies": bodies}), encoding="utf-8")
    queued = write_nsw_authority_queue(bodies_path=bodies_path, output_path=queue_path)
    assert len(queued) == 1
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    assert payload["instance_id"] == "au-rtk"
    assert payload["jurisdiction"] == "NSW"


@pytest.mark.smoke
def test_cli_help_is_a_system_smoke() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "fyi-archive" in result.stdout


@pytest.mark.system
def test_command_adapters_forward_instance_and_write_outputs(tmp_path: Path, monkeypatch) -> None:
    class Instance:
        id = "test-instance"
        rate_limit_name = "test-limit"

        def capture_base_url(self) -> str:
            return "https://foi.example"

    monkeypatch.setattr(discover_command, "resolve_instance", lambda **_: Instance())
    monkeypatch.setattr(
        discover_command,
        "discover_bodies_with_fyi_cli",
        lambda **kwargs: {"count": 2, "output": str(kwargs["output_path"])},
    )
    discover_command.bodies(output=tmp_path / "bodies.json", instance="test-instance")

    monkeypatch.setattr(sync_command, "resolve_instance", lambda **_: Instance())
    monkeypatch.setattr(
        sync_command,
        "run_sync",
        lambda **kwargs: {"verified": True, "instance_id": kwargs["instance_id"]},
    )
    health = tmp_path / "health.json"
    sync_command.run(health_path=health, instance="test-instance", dry_run=True)
    assert json.loads(health.read_text(encoding="utf-8"))["sync"]["verified"] is True


@pytest.mark.edge
def test_doctor_fallbacks_and_coverage_boundaries(tmp_path: Path, monkeypatch) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(
        doctor_command,
        "live_mirror_counts",
        lambda: {"huggingface": {"count": 3, "source": "huggingface", "repo_id": "x/y"}},
    )
    fallback = doctor_command.get_manifest_counts(invalid)
    assert fallback["source"] == "huggingface"
    monkeypatch.setenv("COVERAGE_ID_HORIZON", "0")
    assert doctor_command.get_coverage_info(3)["percent_covered"] == 0


@pytest.mark.integration
def test_backfill_and_publish_report_helpers_cover_existing_report_paths(tmp_path: Path) -> None:
    mirror_path = tmp_path / "mirror.json"
    mirror_path.write_text(
        json.dumps(
            [
                {"mirror": "huggingface", "details": {"repo_id": "owner/data"}},
                {"mirror": "zenodo", "details": {"deposition_id": 12}},
                "ignored",
            ],
        ),
        encoding="utf-8",
    )
    hf, zenodo = backfill_command._mirror_targets(mirror_path)
    assert hf == {"repo_id": "owner/data"}
    assert zenodo == {"deposition_id": 12}
    assert backfill_command._mirror_targets(tmp_path / "missing.json") == (None, None)

    existing = tmp_path / "reports.json"
    existing.write_text(
        json.dumps(
            [
                {
                    "mirror": "old",
                    "verified": True,
                    "record_count": 1,
                    "artifacts": [],
                    "details": {"source": "test"},
                },
            ],
        ),
        encoding="utf-8",
    )
    replacement = MirrorVerification(mirror="old", verified=False, record_count=2)
    merged = publish_command.merge_reports(existing, [replacement])
    assert merged == [replacement]
    decoded = publish_command.report_from_json(
        {
            "mirror": "old",
            "verified": True,
            "record_count": 1,
            "artifacts": [
                {
                    "name": "x",
                    "present": True,
                    "size_matches": None,
                    "checksum_matches": None,
                    "local_sha256": "a",
                }
            ],
            "details": {"source": "test"},
        },
    )
    assert decoded.artifacts[0].name == "x"
