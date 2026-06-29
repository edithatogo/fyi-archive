"""OSF project/component publishing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from fyi_archive.publish.verification import RemoteArtifact

OSF_API = "https://api.osf.io/v2"


def auth_headers(token: str) -> dict[str, str]:
    """Build OSF bearer-token headers."""
    return {"Authorization": f"Bearer {token}"}


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
    with path.open("rb") as handle:
        response = httpx.put(
            upload_url,
            headers=auth_headers(token),
            params={"kind": "file", "name": path.name},
            content=handle,
            timeout=300,
        )
    response.raise_for_status()
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
    response = httpx.get(
        f"{api_url}/nodes/{node_id}/files/osfstorage/",
        headers=auth_headers(token),
        timeout=60,
    )
    response.raise_for_status()
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
