"""Validated site inventory for separate Internet Archive snapshots."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fyi_archive.instances import list_instances

SITE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ADDITIONAL_SITES = Path("configs/additional_foi_archive_sites.json")


@dataclass(frozen=True, slots=True)
class InternetArchiveSite:
    """One independently stored Internet Archive query target."""

    id: str
    kind: str
    country: str
    url_patterns: tuple[str, ...]


def _host_pattern(base_url: str) -> str:
    host = urlsplit(base_url).hostname
    if not host:
        raise ValueError(f"instance base URL has no host: {base_url}")
    return f"{host}/request/*"


def _additional_sites(path: Path) -> list[InternetArchiveSite]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != (
        "fyi-archive.additional-foi-sites.v1"
    ):
        raise ValueError("unsupported additional FOI site registry")
    raw_sites = document.get("sites")
    if not isinstance(raw_sites, list):
        raise ValueError("additional FOI sites must be an array")
    sites: list[InternetArchiveSite] = []
    for index, raw in enumerate(raw_sites):
        if not isinstance(raw, dict):
            raise ValueError(f"sites[{index}] must be an object")
        site_id = raw.get("id")
        kind = raw.get("kind")
        country = raw.get("country")
        patterns = raw.get("url_patterns")
        if not isinstance(site_id, str) or not SITE_ID.fullmatch(site_id):
            raise ValueError(f"sites[{index}] has invalid id")
        if not isinstance(kind, str) or not kind:
            raise ValueError(f"{site_id} requires kind")
        if not isinstance(country, str) or not country:
            raise ValueError(f"{site_id} requires country")
        if (
            not isinstance(patterns, list)
            or not patterns
            or any(not isinstance(pattern, str) or "://" in pattern for pattern in patterns)
        ):
            raise ValueError(f"{site_id} requires host-relative url_patterns")
        sites.append(
            InternetArchiveSite(
                id=site_id,
                kind=kind,
                country=country,
                url_patterns=tuple(str(pattern) for pattern in patterns),
            )
        )
    return sites


def list_internet_archive_sites(
    additional_path: Path = ADDITIONAL_SITES,
) -> list[InternetArchiveSite]:
    """Return every registered FOI site with a separate archive identity."""
    sites = [
        InternetArchiveSite(
            id=instance.id,
            kind="alaveteli",
            country=instance.country,
            url_patterns=(_host_pattern(instance.base_url),),
        )
        for instance in list_instances()
        if "internet_archive" in instance.source_modes
    ]
    sites.extend(_additional_sites(additional_path))
    ids = [site.id for site in sites]
    if len(ids) != len(set(ids)):
        raise ValueError("Internet Archive site ids must be unique")
    return sorted(sites, key=lambda site: site.id)


def internet_archive_matrix(
    additional_path: Path = ADDITIONAL_SITES,
) -> list[dict[str, Any]]:
    """Return a JSON-serializable GitHub Actions matrix."""
    matrix = [asdict(site) for site in list_internet_archive_sites(additional_path)]
    for row in matrix:
        row["url_patterns"] = list(row["url_patterns"])
    return matrix
