"""Tests for verified GitHub catalog recovery."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from fyi_archive import catalog_fallback


def test_restore_latest_verified_catalog_accepts_checksum_matched_artifact(
    monkeypatch, tmp_path: Path
) -> None:
    csv_payload = b"url_name,name,url\nagency,Agency,https://example.test/body/agency\n"
    digest = hashlib.sha256(csv_payload).hexdigest()
    payload = {
        "base_url": "https://www.righttoknow.org.au",
        "catalog_url": "https://mirror.example/au.csv",
        "count": 1,
        "bodies": [{"url_name": "agency", "name": "Agency"}],
        "provenance": {"payload_sha256": digest, "row_count": 1},
    }
    source_provenance = {"catalog_url": "https://mirror.example/au.csv", "payload_sha256": digest}
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("discovered_bodies.json", json.dumps(payload))
        bundle.writestr("discovered_bodies.provenance.json", json.dumps(source_provenance))

    monkeypatch.setattr(
        catalog_fallback,
        "_github_json",
        lambda url, token: (
            {"workflow_runs": [{"id": 42}]}
            if url.endswith("/runs?status=success&per_page=20")
            else {"artifacts": [{"id": 7, "name": "catalog-42", "archive_download_url": "https://gh.test/artifact"}]}
        ),
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return archive.getvalue()

    monkeypatch.setattr(catalog_fallback.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    output = tmp_path / "discovered_bodies.json"
    provenance = tmp_path / "discovered_bodies.provenance.json"
    result = catalog_fallback.restore_latest_verified_catalog(
        output_path=output,
        provenance_path=provenance,
        repository="example/archive",
        workflow="rollout.yml",
        token="token",
    )

    assert result["mode"] == "fallback"
    assert result["source_run_id"] == 42
    assert json.loads(output.read_text(encoding="utf-8"))["count"] == 1
    assert json.loads(provenance.read_text(encoding="utf-8"))["catalog_sha256"] == digest
