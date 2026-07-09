"""Archive instance registry (orchestration config; capture stays in fyi-cli)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_INSTANCE_ID = "nz-fyi"


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
    seed_cap: int = 1000

    def capture_base_url(self) -> str:
        """Return base URL without trailing slash for fyi-cli --base-url."""
        return self.base_url.rstrip("/")


_INSTANCES: dict[str, ArchiveInstance] = {
    "nz-fyi": ArchiveInstance(
        id="nz-fyi",
        base_url="https://fyi.org.nz",
        country="NZ",
        locale="en-NZ",
        hf_repo_id="edithatogo/fyi-archive-nz",
        rate_limit_name="archive-discovery-nz-fyi",
        status="supported",
        title="fyi-archive (fyi.org.nz OIA register)",
        source="https://fyi.org.nz/",
    ),
    "au-rtk": ArchiveInstance(
        id="au-rtk",
        base_url="https://www.righttoknow.org.au",
        country="AU",
        locale="en-AU",
        hf_repo_id="edithatogo/rtk-archive-au",
        rate_limit_name="archive-discovery-au-rtk",
        status="experimental",
        title="rtk-archive (righttoknow.org.au FOI register)",
        source="https://www.righttoknow.org.au/",
    ),
    "uk-wdtk": ArchiveInstance(
        id="uk-wdtk",
        base_url="https://www.whatdotheyknow.com",
        country="GB",
        locale="en-GB",
        hf_repo_id="edithatogo/wdtk-archive-uk",
        rate_limit_name="archive-discovery-uk-wdtk",
        status="experimental",
        title="wdtk-archive (whatdotheyknow.com FOI register)",
        source="https://www.whatdotheyknow.com/",
    ),
    "ie-myrighttoknow": ArchiveInstance(
        id="ie-myrighttoknow",
        base_url="https://www.myrighttoknow.org",
        country="IE",
        locale="en-IE",
        hf_repo_id="edithatogo/mrtk-archive-ie",
        rate_limit_name="archive-discovery-ie-myrighttoknow",
        status="experimental",
        title="mrtk-archive (myrighttoknow.org FOI register)",
        source="https://www.myrighttoknow.org/",
    ),
}


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
