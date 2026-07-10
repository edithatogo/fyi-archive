"""NSW-specific queue planning for the AU RTK seed workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fyi_archive.jurisdictions import jurisdiction_for_body_tag


def select_nsw_authorities(
    bodies: list[dict[str, Any]],
    *,
    rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Select and deduplicate authority rows classified as NSW."""
    selected: dict[str, dict[str, Any]] = {}
    for body in bodies:
        slug = str(
            body.get("url_name") or body.get("URL name") or body.get("slug") or body.get("id") or ""
        ).strip()
        label = str(
            body.get("name") or body.get("Name") or body.get("authority_name") or slug
        ).strip()
        tags = (
            body.get("tags")
            or body.get("Tags")
            or body.get("tag")
            or body.get("jurisdiction")
            or label
        )
        candidates = tags if isinstance(tags, list) else str(tags).split()
        if not any(jurisdiction_for_body_tag(str(tag), rules) == "NSW" for tag in candidates):
            continue
        if slug:
            normalized = {
                key: value for key, value in body.items() if key not in {"URL name", "Name", "Tags"}
            }
            selected[slug] = {
                **normalized,
                "slug": slug,
                "name": label,
                "jurisdiction": "NSW",
            }
    return [selected[slug] for slug in sorted(selected)]


def write_nsw_authority_queue(
    *,
    bodies_path: Path,
    output_path: Path,
    rules: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Write an auditable NSW authority queue from body-discovery JSON."""
    document = json.loads(bodies_path.read_text(encoding="utf-8"))
    bodies = document.get("bodies", document) if isinstance(document, dict) else document
    if not isinstance(bodies, list) or not all(isinstance(body, dict) for body in bodies):
        raise ValueError("body discovery output must contain a list of body objects")
    authorities = select_nsw_authorities(bodies, rules=rules)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "instance_id": "au-rtk",
                "jurisdiction": "NSW",
                "authority_count": len(authorities),
                "authorities": authorities,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return authorities
