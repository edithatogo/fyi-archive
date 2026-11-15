"""Regression coverage for unobserved backfill mirror comparisons."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive import backfill_verification


@pytest.mark.parametrize(
    (
        "captured_records",
        "hf_records",
        "zenodo_records",
        "expected_hf",
        "expected_zenodo",
        "expected_verified",
    ),
    [
        pytest.param(3, None, None, None, None, True, id="both-unobserved"),
        pytest.param(3, 3, None, True, None, True, id="huggingface-only-matched"),
        pytest.param(3, None, 3, None, True, True, id="zenodo-only-matched"),
        pytest.param(3, 3, 3, True, True, True, id="both-matched"),
        pytest.param(3, 2, 3, False, True, False, id="huggingface-mismatched"),
        pytest.param(3, 3, 2, True, False, False, id="zenodo-mismatched"),
        pytest.param(3, 0, None, False, None, False, id="huggingface-observed-empty"),
        pytest.param(3, None, 0, None, False, False, id="zenodo-observed-empty"),
        pytest.param(0, None, None, None, None, False, id="capture-missing-without-mirrors"),
        pytest.param(0, 3, 3, True, True, False, id="capture-missing-with-matched-mirrors"),
    ],
)
def test_backfill_mirror_observations_preserve_aggregate_policy(
    tmp_path: Path,
    captured_records: int,
    hf_records: int | None,
    zenodo_records: int | None,
    expected_hf: bool | None,
    expected_zenodo: bool | None,
    expected_verified: bool,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"meta": {"record_count": 3}, "requests": []}\n',
        encoding="utf-8",
    )
    hf_info = None if hf_records is None else {"record_count": hf_records}
    zenodo_info = None if zenodo_records is None else {"record_count": zenodo_records}

    report = backfill_verification.build_backfill_verification_report(
        state_info={
            "issue_number": 9,
            "issue_url": "",
            "issue_title": "",
            "state": {"summary": {"captured_records": captured_records}},
        },
        merged_manifest_path=manifest,
        hf_info=hf_info,
        zenodo_info=zenodo_info,
    )
    report_path = tmp_path / "report.json"
    backfill_verification.write_backfill_report(report_path, report)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert saved_report["published"] == {"huggingface": hf_info, "zenodo": zenodo_info}
    assert saved_report["comparison"]["merged_matches_huggingface"] is expected_hf
    assert saved_report["comparison"]["merged_matches_zenodo"] is expected_zenodo
    assert saved_report["comparison"]["fully_verified"] is expected_verified
