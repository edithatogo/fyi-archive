from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from fyi_archive.source_graph import (
    JURISDICTION_TARGETS,
    SOURCE_GRAPH_CONFIG,
    _read_json,
    build_source_graph,
)


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _config() -> dict[str, Any]:
    return json.loads(SOURCE_GRAPH_CONFIG.read_text(encoding="utf-8"))


def _targets() -> dict[str, Any]:
    return json.loads(JURISDICTION_TARGETS.read_text(encoding="utf-8"))


def test_json_inputs_must_be_objects(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        _read_json(_write(tmp_path / "array.json", []))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(schema="unsupported"), "unsupported archive source"),
        (
            lambda value: value.update(transformation={"id": "unsupported"}),
            "transformation is missing",
        ),
        (lambda value: value.update(sites={}), "sites must be an array"),
        (
            lambda value: value.update(preservation_sources={}),
            "preservation_sources must be an array",
        ),
        (
            lambda value: value.update(default_preservation_source_ids=["missing"]),
            "default preservation source ids",
        ),
    ],
)
def test_source_graph_rejects_invalid_top_level_config(
    tmp_path: Path, mutation, message: str
) -> None:
    config = _config()
    mutation(config)
    path = _write(tmp_path / "config.json", config)
    with pytest.raises(ValueError, match=message):
        build_source_graph(config_path=path)


def test_source_graph_rejects_missing_and_duplicate_targets(tmp_path: Path) -> None:
    missing = _targets()
    missing["targets"] = {}
    with pytest.raises(ValueError, match="must contain targets"):
        build_source_graph(targets_path=_write(tmp_path / "missing.json", missing))

    duplicate = _targets()
    rows = cast(list[dict[str, Any]], duplicate["targets"])
    assert isinstance(rows, list)
    rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError, match="present and unique"):
        build_source_graph(targets_path=_write(tmp_path / "duplicate.json", duplicate))


def test_source_graph_rejects_registry_and_source_mismatches(tmp_path: Path) -> None:
    config = _config()
    sites = cast(list[dict[str, Any]], config["sites"])
    assert isinstance(sites, list)
    sites.pop()
    with pytest.raises(ValueError, match="site mismatch"):
        build_source_graph(config_path=_write(tmp_path / "sites.json", config))

    config = _config()
    sources = cast(list[dict[str, Any]], config["preservation_sources"])
    assert isinstance(sources, list)
    sources.append(deepcopy(sources[0]))
    with pytest.raises(ValueError, match="source ids must be present and unique"):
        build_source_graph(config_path=_write(tmp_path / "sources.json", config))


def test_source_graph_rejects_unresolved_and_duplicate_mappings(tmp_path: Path) -> None:
    config = _config()
    sites = cast(list[dict[str, Any]], config["sites"])
    assert isinstance(sites, list)
    first = sites[0]
    assert isinstance(first, dict)
    first["jurisdiction_targets"] = ["missing"]
    with pytest.raises(ValueError, match="unresolved jurisdiction targets"):
        build_source_graph(config_path=_write(tmp_path / "target.json", config))

    config = _config()
    sites = cast(list[dict[str, Any]], config["sites"])
    assert isinstance(sites, list)
    first, second = sites[:2]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    first_targets = first["jurisdiction_targets"]
    second_targets = second["jurisdiction_targets"]
    assert isinstance(first_targets, list)
    assert isinstance(second_targets, list)
    second_targets.append(first_targets[0])
    with pytest.raises(ValueError, match="exactly one site"):
        build_source_graph(config_path=_write(tmp_path / "duplicate-map.json", config))

    config = _config()
    sites = cast(list[dict[str, Any]], config["sites"])
    assert isinstance(sites, list)
    assert isinstance(sites[0], dict)
    sites[0]["additional_preservation_source_ids"] = ["missing"]
    with pytest.raises(ValueError, match="unresolved preservation sources"):
        build_source_graph(config_path=_write(tmp_path / "source-map.json", config))
