"""Archive instance registry (orchestration config; capture stays in fyi-cli)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import TypedDict, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

DEFAULT_INSTANCE_ID = "nz-fyi"
_CONFIG_RESOURCE = "config/archive_instances.json"
_SCHEMA_RESOURCE = "schemas/archive-instances.schema.json"


class _InstanceRow(TypedDict):
    id: str
    base_url: str
    country: str
    locale: str
    hf_repo_id: str
    rate_limit_name: str
    status: str
    title: str
    source: str
    catalog_url: str | None
    source_modes: list[str]
    seed_cap: int


@dataclass(frozen=True, slots=True)
class ArchiveInstance:
    """One Alaveteli site archive configuration."""

    id: str
    base_url: str
    country: str
    locale: str
    hf_repo_id: str
    rate_limit_name: str
    status: str
    title: str
    source: str
    catalog_url: str | None = None
    source_modes: tuple[str, ...] = ("live_api", "atom_feed", "internet_archive")
    seed_cap: int = 1000

    def capture_base_url(self) -> str:
        """Return base URL without trailing slash for fyi-cli --base-url."""
        return self.base_url.rstrip("/")

    def search_feed_url(self) -> str:
        """Return fyi-cli's read-only Alaveteli JSON search-feed entry point."""
        return f"{self.capture_base_url()}/search/all?output=json&page=1"


def _read_packaged_json(resource: str) -> object:
    packaged = files("fyi_archive").joinpath(resource)
    if packaged.is_file():
        content = packaged.read_text(encoding="utf-8")
    else:
        content = (Path(__file__).resolve().parents[2] / resource).read_text(encoding="utf-8")
    return cast("object", json.loads(content))


def _parse_registry(document: object, schema: object) -> dict[str, ArchiveInstance]:
    """Validate and materialize one declarative registry document."""
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)  # pyright: ignore[reportUnknownMemberType, reportArgumentType]
    except (ValidationError, TypeError) as error:
        msg = f"Invalid archive instance registry: {error.message if isinstance(error, ValidationError) else error}"
        raise ValueError(msg) from error

    if not isinstance(document, dict):
        raise ValueError("Invalid archive instance registry: root must be an object")
    registry = cast("dict[str, object]", document)
    rows = registry.get("instances")
    if not isinstance(rows, list):
        raise ValueError("Invalid archive instance registry: instances must be an array")
    instances: dict[str, ArchiveInstance] = {}
    for row in cast("list[object]", rows):
        if not isinstance(row, dict):
            raise ValueError("Invalid archive instance registry: instance must be an object")
        typed_row = cast("_InstanceRow", row)
        instance_id = typed_row["id"]
        if instance_id in instances:
            raise ValueError(f"Invalid archive instance registry: duplicate id {instance_id!r}")
        base_url = typed_row["base_url"].rstrip("/")
        source = typed_row["source"]
        if source != f"{base_url}/":
            raise ValueError(
                f"Invalid archive instance registry: source for {instance_id!r} "
                "must equal base_url with one trailing slash"
            )
        instances[instance_id] = ArchiveInstance(
            id=instance_id,
            base_url=base_url,
            country=typed_row["country"],
            locale=typed_row["locale"],
            hf_repo_id=typed_row["hf_repo_id"],
            rate_limit_name=typed_row["rate_limit_name"],
            status=typed_row["status"],
            title=typed_row["title"],
            source=source,
            catalog_url=typed_row["catalog_url"],
            source_modes=tuple(typed_row["source_modes"]),
            seed_cap=typed_row["seed_cap"],
        )
    if DEFAULT_INSTANCE_ID not in instances:
        raise ValueError(
            f"Invalid archive instance registry: default {DEFAULT_INSTANCE_ID!r} is missing"
        )
    return instances


def _load_instances() -> dict[str, ArchiveInstance]:
    return _parse_registry(
        _read_packaged_json(_CONFIG_RESOURCE),
        _read_packaged_json(_SCHEMA_RESOURCE),
    )


_INSTANCES = _load_instances()


def list_instances() -> list[ArchiveInstance]:
    """Return all registered archive instances in stable id order."""
    return [_INSTANCES[key] for key in sorted(_INSTANCES)]


def get_instance(instance_id: str | None = None) -> ArchiveInstance:
    """Resolve an instance by id (default nz-fyi)."""
    resolved = (instance_id or DEFAULT_INSTANCE_ID).strip()
    try:
        return _INSTANCES[resolved]
    except KeyError as error:
        known = ", ".join(sorted(_INSTANCES))
        msg = f"Unknown archive instance {resolved!r}; known: {known}"
        raise ValueError(msg) from error


def resolve_instance(
    *,
    instance_id: str | None = None,
    base_url: str | None = None,
) -> ArchiveInstance:
    """Resolve instance from id and optional base_url override.

    When ``base_url`` is set, the catalog entry is copied with an overridden URL
    and derived ``source`` (trailing slash). Unknown overrides still require a
    known instance_id for HF/rate-limit identity.
    """
    instance = get_instance(instance_id)
    if base_url is None or not str(base_url).strip():
        env_base = os.environ.get("FYI_ARCHIVE_BASE_URL", "").strip()
        if not env_base:
            return instance
        base_url = env_base

    cleaned = str(base_url).strip().rstrip("/")
    if not cleaned:
        return instance
    source = cleaned + "/"
    return ArchiveInstance(
        id=instance.id,
        base_url=cleaned,
        country=instance.country,
        locale=instance.locale,
        hf_repo_id=instance.hf_repo_id,
        rate_limit_name=instance.rate_limit_name,
        status=instance.status,
        title=instance.title,
        source=source,
        catalog_url=instance.catalog_url,
        source_modes=instance.source_modes,
        seed_cap=instance.seed_cap,
    )


def source_for_instance(instance_id: str | None = None) -> str:
    """Return canonical source URL for an instance."""
    return get_instance(instance_id).source


def known_sources() -> frozenset[str]:
    """Return all catalog source URLs (trailing slash)."""
    return frozenset(item.source for item in _INSTANCES.values())


def instance_id_for_source(source: str) -> str | None:
    """Map a manifest source URL to an instance id when known."""
    normalized = source if source.endswith("/") else f"{source}/"
    for item in _INSTANCES.values():
        if item.source == normalized:
            return item.id
    return None
