from __future__ import annotations

from fyi_archive.dataset_card import render


def snapshot_summary() -> dict[str, object]:
    return {
        "generated_at": "2026-07-21T06:00:00+00:00",
        "record_count": 33217,
        "manifest_sha256": "a" * 64,
        "verified": True,
    }


def test_render_inserts_verified_metadata_without_rewriting_card() -> None:
    rendered = render("# Card\n\nStable explanation.\n", snapshot_summary())
    assert "Stable explanation." in rendered
    assert "Snapshot records: **33,217**" in rendered
    assert "Manifest SHA-256: `" + "a" * 64 + "`" in rendered
    assert rendered.count("fyi-archive:generated-metadata:start") == 1


def test_render_replaces_existing_generated_block() -> None:
    card = "# Card\n\n" + "\n".join([
        "<!-- fyi-archive:generated-metadata:start -->",
        "old",
        "<!-- fyi-archive:generated-metadata:end -->",
        "\nStable explanation.",
    ])
    rendered = render(card, snapshot_summary())
    assert "old" not in rendered
    assert rendered.count("Stable explanation.") == 1


def test_render_fails_closed_for_incomplete_summary() -> None:
    try:
        render("# Card", {"record_count": 1})
    except KeyError as error:
        assert error.args[0] == "verified"
    else:
        raise AssertionError("incomplete metadata must fail closed")
