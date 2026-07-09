"""OSF project/component publishing helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import sleep
from typing import Any

import httpx

from fyi_archive.publish.verification import RemoteArtifact

OSF_API = "https://api.osf.io/v2"
RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def auth_headers(token: str) -> dict[str, str]:
    """Build OSF bearer-token headers."""
    return {"Authorization": f"Bearer {token}"}


def request_with_retry(
    request: Callable[[], httpx.Response],
    *,
    attempts: int = 4,
    backoff_seconds: float = 2.0,
) -> httpx.Response:
    """Run an OSF request with bounded retry for transient storage/API failures."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = request()
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in RETRY_STATUS_CODES or attempt == attempts:
                raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt == attempts:
                raise
        else:
            return response
        sleep(backoff_seconds * attempt)
    if last_error is not None:
        raise last_error
    msg = "OSF request failed without an exception"
    raise RuntimeError(msg)


def create_project(*, token: str, title: str, api_url: str = OSF_API) -> dict[str, Any]:
    """Create an OSF project node."""
    response = httpx.post(
        f"{api_url}/nodes/",
        headers=auth_headers(token),
        json={"data": {"type": "nodes", "attributes": {"title": title, "category": "project"}}},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def create_component(
    *,
    token: str,
    parent_id: str,
    title: str,
    api_url: str = OSF_API,
) -> dict[str, Any]:
    """Create an OSF component under a project node."""
    response = httpx.post(
        f"{api_url}/nodes/{parent_id}/children/",
        headers=auth_headers(token),
        json={"data": {"type": "nodes", "attributes": {"title": title, "category": "data"}}},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def list_components(*, token: str, parent_id: str, api_url: str = OSF_API) -> list[dict[str, Any]]:
    """List OSF components under a project node."""
    response = httpx.get(
        f"{api_url}/nodes/{parent_id}/children/",
        headers=auth_headers(token),
        timeout=60,
    )
    response.raise_for_status()
    return list(response.json().get("data", []))


def ensure_component(
    *,
    token: str,
    parent_id: str,
    title: str,
    api_url: str = OSF_API,
) -> dict[str, Any]:
    """Return an existing component with the title or create it."""
    for component in list_components(token=token, parent_id=parent_id, api_url=api_url):
        attributes = component.get("attributes", {})
        if attributes.get("title") == title:
            return {"data": component}
    return create_component(token=token, parent_id=parent_id, title=title, api_url=api_url)


def upload_file(*, token: str, upload_url: str, path: Path) -> dict[str, Any]:
    """Upload one file to an OSF storage upload URL."""
    response = request_with_retry(
        lambda: httpx.put(
            upload_url,
            headers=auth_headers(token),
            params={"kind": "file", "name": path.name},
            content=path.read_bytes(),
            timeout=300,
        )
    )
    return response.json()


def get_osfstorage_upload_url(*, token: str, node_id: str, api_url: str = OSF_API) -> str:
    """Return the OSF Storage upload URL for a node."""
    response = httpx.get(
        f"{api_url}/nodes/{node_id}/files/",
        headers=auth_headers(token),
        timeout=60,
    )
    response.raise_for_status()
    for provider in response.json().get("data", []):
        provider_id = provider.get("id")
        attributes = provider.get("attributes", {})
        provider_name = attributes.get("provider")
        links = provider.get("links", {})
        if provider_id == "osfstorage" or provider_name == "osfstorage":
            upload_url = links.get("upload")
            if upload_url:
                return str(upload_url)
    msg = "OSF Storage upload URL was not found for node"
    raise ValueError(msg)


def list_files(*, token: str, node_id: str, api_url: str = OSF_API) -> list[RemoteArtifact]:
    """List OSF file evidence for a node."""
    response = request_with_retry(
        lambda: httpx.get(
            f"{api_url}/nodes/{node_id}/files/osfstorage/",
            headers=auth_headers(token),
            timeout=60,
        )
    )
    artifacts = []
    for file_data in response.json().get("data", []):
        attributes = file_data.get("attributes", {})
        links = file_data.get("links", {})
        name = str(attributes.get("name") or attributes.get("materialized_path") or "")
        if not name:
            continue
        artifacts.append(
            RemoteArtifact(
                name=Path(name).name,
                size=file_size(attributes),
                checksum=file_sha256(attributes),
                url=links.get("download") or links.get("html"),
            ),
        )
    return artifacts


def file_size(attributes: dict[str, Any]) -> int | None:
    """Extract OSF file size if available."""
    value = attributes.get("size")
    return int(value) if value is not None else None


def file_sha256(attributes: dict[str, Any]) -> str | None:
    """Extract OSF SHA-256 checksum if available."""
    hashes = attributes.get("extra", {}).get("hashes", {})
    sha256 = hashes.get("sha256") if isinstance(hashes, dict) else None
    return f"sha256:{sha256}" if sha256 else None
