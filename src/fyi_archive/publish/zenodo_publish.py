"""Zenodo draft-first publishing helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from fyi_archive.publish.verification import RemoteArtifact

ZENODO_API = "https://zenodo.org/api"
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"


def load_metadata(path: Path = Path(".zenodo.json")) -> dict[str, Any]:
    """Load Zenodo metadata from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def create_draft(
    *,
    token: str,
    metadata: dict[str, Any],
    api_url: str = ZENODO_API,
) -> dict[str, Any]:
    """Create a Zenodo draft deposition."""
    response = httpx.post(
        f"{api_url}/deposit/depositions",
        params={"access_token": token},
        json={"metadata": metadata},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def upload_file(*, token: str, bucket_url: str, path: Path) -> dict[str, Any]:
    """Upload one file to a Zenodo deposition bucket."""
    with path.open("rb") as handle:
        response = httpx.put(
            f"{bucket_url}/{path.name}",
            params={"access_token": token},
            content=handle,
            timeout=300,
        )
    response.raise_for_status()
    return response.json()


def publish_draft(
    *,
    token: str,
    deposition_id: int,
    confirm: str,
    api_url: str = ZENODO_API,
) -> dict[str, Any]:
    """Publish a Zenodo draft only with the explicit production confirm string."""
    if confirm != "publish-zenodo-doi":
        msg = "Publishing requires confirm='publish-zenodo-doi'"
        raise ValueError(msg)
    response = httpx.post(
        f"{api_url}/deposit/depositions/{deposition_id}/actions/publish",
        params={"access_token": token},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_deposition(*, token: str, deposition_id: int, api_url: str = ZENODO_API) -> dict[str, Any]:
    """Fetch one Zenodo deposition with its uploaded file evidence."""
    response = httpx.get(
        f"{api_url}/deposit/depositions/{deposition_id}",
        params={"access_token": token},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def deposition_artifacts(deposition: dict[str, Any]) -> list[RemoteArtifact]:
    """Normalize Zenodo deposition files into remote artifact evidence."""
    artifacts = []
    for file_data in deposition.get("files", []):
        filename = str(file_data.get("filename") or file_data.get("key") or "")
        if not filename:
            continue
        links = file_data.get("links") if isinstance(file_data.get("links"), dict) else {}
        artifacts.append(
            RemoteArtifact(
                name=Path(filename).name,
                size=file_size(file_data),
                checksum=file_checksum(file_data),
                url=links.get("self") or links.get("download"),
            ),
        )
    return artifacts


def file_size(file_data: dict[str, Any]) -> int | None:
    """Extract Zenodo file size if available."""
    value = file_data.get("filesize") or file_data.get("size")
    return int(value) if value is not None else None


def file_checksum(file_data: dict[str, Any]) -> str | None:
    """Extract Zenodo checksum if available."""
    checksum = file_data.get("checksum")
    return str(checksum) if checksum else None
