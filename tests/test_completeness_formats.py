from __future__ import annotations

import json
from pathlib import Path

import pytest

from fyi_archive.completeness import load_inventory, normalize_url


def test_inventory_accepts_jsonl_wrappers_single_objects_and_strings(tmp_path: Path) -> None:
    jsonl = tmp_path / "rows.jsonl"
    jsonl.write_text(
        '{"url":"https://example.test/one"}\n{"url":"https://example.test/two","state":"test"}\n',
        encoding="utf-8",
    )
    inventory = load_inventory(jsonl)
    assert inventory.urls == frozenset({"https://example.test/one"})
    assert inventory.synthetic_urls == frozenset({"https://example.test/two"})

    for key in ("records", "requests", "rows", "items"):
        path = tmp_path / f"{key}.json"
        path.write_text(
            json.dumps({key: [{"url": f"https://example.test/{key}"}]}),
            encoding="utf-8",
        )
        assert load_inventory(path).urls == frozenset({f"https://example.test/{key}"})

    single = tmp_path / "single.json"
    single.write_text(json.dumps({"url": "https://example.test/single"}), encoding="utf-8")
    assert load_inventory(single).urls == frozenset({"https://example.test/single"})

    string_row = tmp_path / "strings.json"
    string_row.write_text(json.dumps(["https://example.test/string"]), encoding="utf-8")
    assert load_inventory(string_row).urls == frozenset({"https://example.test/string"})


def test_inventory_rejects_scalar_payload_and_normalizes_ports(tmp_path: Path) -> None:
    scalar = tmp_path / "scalar.json"
    scalar.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array, object, or JSONL"):
        load_inventory(scalar)

    assert normalize_url("HTTPS://EXAMPLE.TEST:8443/path/#fragment") == (
        "https://example.test:8443/path"
    )
