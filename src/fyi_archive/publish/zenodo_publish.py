"""Zenodo draft-first publishing helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

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
