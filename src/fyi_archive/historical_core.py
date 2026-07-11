"""Extract core Alaveteli request metadata from archived HTML only."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from html import unescape
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup

_WHITESPACE = re.compile(r"\s+")
_STATUS_PATTERN = re.compile(
    r"(?:status|state)\s*[:\-]\s*(open|waiting[^,.;<]*|successful|rejected|"
    r"partially successful|gone|internal review)",
    re.IGNORECASE,
)


def clean_text(value: object) -> str:
    """Collapse markup-derived whitespace into a stable string."""
    return _WHITESPACE.sub(" ", unescape(str(value or ""))).strip()


def archive_replay_url(source_url: str, timestamp: str) -> str:
    """Build an Internet Archive replay URL without changing the source URL."""
    return f"https://web.archive.org/web/{timestamp}id_/{quote(source_url, safe=":/?#[]@!$&'()*+,;=%")}"


def _first_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = node.get("content") or node.get_text(" ", strip=True)
            if clean_text(value):
                return clean_text(value)
    return ""


def _extract_date(soup: BeautifulSoup, names: tuple[str, ...]) -> str | None:
    for name in names:
        node = soup.select_one(f'time[datetime][class*="{name}"], meta[name="{name}"]')
        if node:
            value = node.get("datetime") or node.get("content")
            if value:
                return clean_text(value)
    return None


def parse_archived_request(
    html: str,
    *,
    source_url: str,
    archive_url: str,
    archive_timestamp: str,
    archive_digest: str = "",
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Extract conservative core fields from one archived request page."""
    soup = BeautifulSoup(html, "html.parser")
    title = _first_text(soup, ("h1", "meta[property='og:title']", "title"))
    authority = _first_text(
        soup,
        ("a.public-body", "a[href*='/body/']", ".request-authority", ".public-body"),
    )
    state = _first_text(soup, (".request-status", ".request-state", ".status", ".state"))
    if not state:
        match = _STATUS_PATTERN.search(clean_text(soup.get_text(" ", strip=True)))
        state = clean_text(match.group(1)) if match else ""
    first_seen = _extract_date(soup, ("datePublished", "requested", "created", "first-seen"))
    last_updated = _extract_date(soup, ("dateModified", "updated", "last-updated"))
    request_key = source_url.rstrip("/").rsplit("/", 1)[-1]
    record: dict[str, Any] = {
        "source_url": source_url,
        "archive_url": archive_url,
        "archive_timestamp": archive_timestamp,
        "archive_digest": archive_digest,
        "request_key": request_key,
        "title": title,
        "authority": authority,
        "state": state,
        "first_seen": first_seen,
        "last_updated": last_updated,
        "extraction_status": "extracted",
        "content_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    if instance_id:
        record["instance_id"] = instance_id
    return record


def failed_archived_request(
    *,
    source_url: str,
    archive_url: str,
    archive_timestamp: str,
    archive_digest: str,
    diagnostic: str,
    instance_id: str | None = None,
) -> dict[str, Any]:
    """Represent an archived-page failure without inventing core values."""
    record: dict[str, Any] = {
        "source_url": source_url,
        "archive_url": archive_url,
        "archive_timestamp": archive_timestamp,
        "archive_digest": archive_digest,
        "request_key": source_url.rstrip("/").rsplit("/", 1)[-1],
        "title": "",
        "authority": "",
        "state": "",
        "first_seen": None,
        "last_updated": None,
        "extraction_status": "fetch_failed",
        "diagnostic": clean_text(diagnostic)[-500:],
    }
    if instance_id:
        record["instance_id"] = instance_id
    return record
