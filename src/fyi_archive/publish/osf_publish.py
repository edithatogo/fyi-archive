"""OSF project/component publishing helpers."""

from __future__ import annotations

from typing import Any

import httpx

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
