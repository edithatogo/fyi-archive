"""Encode and decode FYI backfill controller state for issue storage."""

from __future__ import annotations

import base64
import json
import zlib
from typing import Any

STATE_FORMAT = "fyi-backfill-state.v1"


def encode_state(state: dict[str, Any]) -> dict[str, str]:
    """Encode a controller state object into a compact issue-body wrapper."""
    payload = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressed = zlib.compress(payload, level=9)
    return {
        "format": STATE_FORMAT,
        "encoding": "zlib+base64",
        "payload": base64.b64encode(compressed).decode("ascii"),
    }


def decode_state(body: str) -> dict[str, Any]:
    """Decode a controller state body, accepting encoded or plain JSON."""
    data = json.loads(body)
    if not isinstance(data, dict):
        msg = "backfill state issue body must be a JSON object"
        raise ValueError(msg)
    if data.get("format") == STATE_FORMAT and data.get("encoding") == "zlib+base64":
        payload = str(data.get("payload") or "")
        if not payload:
            msg = "backfill state wrapper is missing payload"
            raise ValueError(msg)
        decoded = zlib.decompress(base64.b64decode(payload))
        state = json.loads(decoded.decode("utf-8"))
        if not isinstance(state, dict):
            msg = "decoded backfill state must be a JSON object"
            raise ValueError(msg)
        return state
    return data


def state_body_from_state(state: dict[str, Any]) -> str:
    """Render a controller state wrapper suitable for GitHub issue bodies."""
    return json.dumps(encode_state(state), separators=(",", ":")) + "\n"
