"""Build the normalized multi-country archive source graph with provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from fyi_archive.instances import list_instances
from fyi_archive.internet_archive_sites import ADDITIONAL_SITES, list_internet_archive_sites

SOURCE_GRAPH_CONFIG = Path("configs/archive_source_graph.json")
JURISDICTION_TARGETS = Path("configs/jurisdiction_archive_targets.json")
INSTANCE_REGISTRY = Path("src/fyi_archive/instances.py")
TRANSFORMATION_VERSION = "normalize-archive-sources-v1"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_source_graph(
    *,
    config_path: Path = SOURCE_GRAPH_CONFIG,
    targets_path: Path = JURISDICTION_TARGETS,
    additional_path: Path = ADDITIONAL_SITES,
    instance_registry_path: Path = INSTANCE_REGISTRY,
) -> dict[str, Any]:
    """Join source registries into one deterministic, evidence-carrying graph."""
    config = _read_json(config_path)
    if config.get("schema") != "fyi-archive.archive-source-graph.v1":
        raise ValueError("unsupported archive source graph schema")
    transformation = config.get("transformation")
    if not isinstance(transformation, dict) or transformation.get("id") != (TRANSFORMATION_VERSION):
        raise ValueError("source graph transformation is missing or unsupported")

    ledger = _read_json(targets_path)
    raw_targets = ledger.get("targets")
    if not isinstance(raw_targets, list):
        raise ValueError("jurisdiction target ledger must contain targets")
    targets = {
        str(row["target_id"]): row
        for row in raw_targets
        if isinstance(row, dict) and isinstance(row.get("target_id"), str)
    }
    if len(targets) != len(raw_targets):
        raise ValueError("jurisdiction target ids must be present and unique")

    archive_sites = {site.id: site for site in list_internet_archive_sites(additional_path)}
    instances = {instance.id: instance for instance in list_instances()}
    raw_sites = config.get("sites")
    if not isinstance(raw_sites, list):
        raise ValueError("source graph sites must be an array")
    configured_ids = {
        str(row["site_id"])
        for row in raw_sites
        if isinstance(row, dict) and isinstance(row.get("site_id"), str)
    }
    if configured_ids != set(archive_sites):
        missing = sorted(set(archive_sites) - configured_ids)
        extra = sorted(configured_ids - set(archive_sites))
        raise ValueError(f"source graph site mismatch; missing={missing}, extra={extra}")

    source_catalog_rows = config.get("preservation_sources")
    if not isinstance(source_catalog_rows, list):
        raise ValueError("preservation_sources must be an array")
    source_catalog = {
        str(row["id"]): row
        for row in source_catalog_rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    if len(source_catalog) != len(source_catalog_rows):
        raise ValueError("preservation source ids must be present and unique")
    defaults = config.get("default_preservation_source_ids")
    if not isinstance(defaults, list) or any(item not in source_catalog for item in defaults):
        raise ValueError("default preservation source ids must resolve")

    normalized_sites: list[dict[str, Any]] = []
    mapped_targets: list[str] = []
    for raw in raw_sites:
        if not isinstance(raw, dict):
            raise ValueError("source graph site entries must be objects")
        site_id = str(raw["site_id"])
        jurisdiction_ids = raw.get("jurisdiction_targets")
        additional_sources = raw.get("additional_preservation_source_ids")
        if (
            not isinstance(jurisdiction_ids, list)
            or not jurisdiction_ids
            or any(item not in targets for item in jurisdiction_ids)
        ):
            raise ValueError(f"{site_id} has unresolved jurisdiction targets")
        if not isinstance(additional_sources, list) or any(
            item not in source_catalog for item in additional_sources
        ):
            raise ValueError(f"{site_id} has unresolved preservation sources")
        mapped_targets.extend(str(item) for item in jurisdiction_ids)
        site = archive_sites[site_id]
        instance = instances.get(site_id)
        primary = {
            "status": instance.status if instance else "adapter_required",
            "base_url": instance.base_url if instance else None,
            "catalog_url": instance.catalog_url if instance else None,
            "source_modes": list(instance.source_modes) if instance else [],
        }
        source_ids = list(dict.fromkeys([*defaults, *additional_sources]))
        normalized_sites.append(
            {
                "site_id": site_id,
                "country": site.country,
                "platform": site.kind,
                "jurisdiction_targets": sorted(str(item) for item in jurisdiction_ids),
                "primary": primary,
                "internet_archive": {
                    "discovery_status": "configured",
                    "prospective_capture_status": "archive_it_or_equivalent_required",
                    "url_patterns": list(site.url_patterns),
                    "evidence_mode": "complete_cdx_inventory",
                    "origin_contacted": False,
                },
                "preservation_sources": [
                    {**source_catalog[source_id], "site_evidence_status": "not_probed"}
                    for source_id in source_ids
                ],
            }
        )

    if len(mapped_targets) != len(set(mapped_targets)):
        raise ValueError("jurisdiction targets must map to exactly one site")
    if set(mapped_targets) != set(targets):
        missing = sorted(set(targets) - set(mapped_targets))
        extra = sorted(set(mapped_targets) - set(targets))
        raise ValueError(f"jurisdiction mapping mismatch; missing={missing}, extra={extra}")

    normalized_sites.sort(key=lambda row: str(row["site_id"]))
    graph_payload = {
        "sites": normalized_sites,
        "jurisdiction_targets": [targets[key] for key in sorted(targets)],
        "preservation_source_catalog": [source_catalog[key] for key in sorted(source_catalog)],
    }
    input_paths = [instance_registry_path, additional_path, targets_path, config_path]
    return {
        "schema": "fyi-archive.normalized-archive-source-graph.v1",
        "transformation": {
            "id": TRANSFORMATION_VERSION,
            "description": transformation["description"],
            "lossless_join": True,
            "inference": "none",
        },
        "provenance": {
            "inputs": [{"path": path.as_posix(), "sha256": _sha256(path)} for path in input_paths],
            "payload_sha256": _canonical_sha256(graph_payload),
        },
        "counts": {
            "sites": len(normalized_sites),
            "jurisdiction_targets": len(targets),
            "preservation_sources": len(source_catalog),
        },
        **graph_payload,
    }


def write_source_graph(output: Path) -> dict[str, Any]:
    """Write the normalized graph without changing its deterministic payload."""
    graph = build_source_graph()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return graph
