from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def test_scheduled_indexes_are_explicitly_url_level_only() -> None:
    workflow = (WORKFLOWS / "alaveteli_historical_indexes.yml").read_text(encoding="utf-8")

    assert "CAPTURE_MODE: ${{ matrix.capture_mode }}" in workflow
    assert '--capture-mode "$CAPTURE_MODE"' in workflow
    assert "schedule:" in workflow


def test_all_capture_export_requires_manual_confirmation_and_does_not_replay() -> None:
    workflow = (WORKFLOWS / "alaveteli_historical_all_captures.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "EXPORT_ALL_CAPTURE_METADATA" in workflow
    assert "--capture-mode all_captures" in workflow
    assert "import_historical_sources.py" not in workflow
    assert "if: always()" in workflow


def test_historical_source_index_uses_fail_closed_paginator() -> None:
    workflow = (WORKFLOWS / "historical_source_indexes.yml").read_text(encoding="utf-8")

    assert "fetch_complete_internet_archive_cdx.py" in workflow
    assert "--capture-mode url_index" in workflow
    assert "internet_archive_retrieval.json" in workflow
