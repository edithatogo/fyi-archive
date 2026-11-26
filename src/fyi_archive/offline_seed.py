"""Import already acquired source evidence into the seed's local request store.

This explicitly selected adapter performs no acquisition and does not replace
the legacy capture command. The caller supplies the receipt verifier and all
evidence files. A private snapshot is verified before it is marked complete.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from fyi_archive.seed import SAFE_REQUEST_ID, CaptureError, SeedCaps, SeedRequest


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Five files produced for one source response by fyi-cli."""

    kind: str
    raw: Path
    result: Path
    receipt: Path
    wacz: Path
    link: Path


def _safe_locator(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("attachment URL is missing")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("attachment URL must name an HTTP origin")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or any(c.isspace() or ord(c) < 32 or c == "\\" for c in value)
    ):
        raise ValueError("attachment URL is not safe to persist")
    path = parsed.path
    for _ in range(4):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    if (
        "%" in path
        or any(c.isspace() or ord(c) < 32 or c == "\\" for c in path)
        or ("/attachments/" in path.lower() and "--" in path)
    ):
        raise ValueError("attachment URL contains a signed or ambiguous path")
    return value


def _copy_regular(source: Path, destination: Path, limit: int) -> None:
    if any(path.is_symlink() for path in (source, *source.parents)) or not source.is_file():
        raise ValueError("source evidence must be a regular, non-symlink file")
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as reader, destination.open("xb") as writer:
        metadata = os.fstat(reader.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError("source evidence is not a bounded regular file")
        copied = 0
        while chunk := reader.read(1024 * 1024):
            copied += len(chunk)
            if copied > limit:
                raise ValueError("source evidence exceeds the offline handoff limit")
            writer.write(chunk)


def capture_offline_evidence(
    request: SeedRequest,
    data_dir: Path,
    _dist_dir: Path,
    caps: SeedCaps,
    extra_args: Sequence[str],
    *,
    evidence: Sequence[SourceEvidence],
    verifier: Path,
) -> dict[str, Any]:
    """Verify and stage a single request's offline evidence for ``run_seed``.

    The derived request is a projection: its raw JSON is retained unchanged in
    evidence and attachment WARC identifiers are placed in the sidecar consumed
    by the Rust process-event exporter. Existing handoffs are never replaced.
    """
    request_id = str(request.request_id)
    if request_id in {".", ".."} or SAFE_REQUEST_ID.fullmatch(request_id) is None:
        raise ValueError("request_id must be a filename-safe identifier")
    if extra_args:
        raise ValueError("offline evidence import does not accept source CLI arguments")
    if not evidence or [item.kind for item in evidence[:2]] != ["request-json", "request-page"]:
        raise ValueError("offline handoff requires request JSON and page evidence first")
    if any(item.kind != "attachment" for item in evidence[2:]):
        raise ValueError("offline handoff contains an unexpected source kind")

    root = data_dir / "offline-seed"
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError("offline handoff path must not contain symlinks")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / request_id
    destination.mkdir(mode=0o700)  # fail rather than replacing an earlier capture
    try:
        snapshot = destination / "evidence"
        snapshot.mkdir(mode=0o700)
        resources: list[tuple[SourceEvidence, dict[str, Any], dict[str, Any], Path]] = []
        total_bytes = 0
        for index, item in enumerate(evidence):
            copied = {}
            for label in ("raw", "result", "receipt", "wacz", "link"):
                extension = "wacz" if label == "wacz" else "raw" if label == "raw" else "json"
                target = snapshot / f"{index}-{label}.{extension}"
                limit = 32 * 1024 * 1024
                if caps.max_bytes is not None:
                    limit = min(limit, max(0, caps.max_bytes - total_bytes))
                _copy_regular(getattr(item, label), target, limit)
                copied[label] = target
                total_bytes += target.stat().st_size
            checked = subprocess.run(  # noqa: S603 - explicit local verifier and fixed arguments
                [
                    str(verifier),
                    "verify-acquisition-receipt",
                    str(copied["receipt"]),
                    "--raw-file",
                    str(copied["raw"]),
                    "--result-file",
                    str(copied["result"]),
                    "--wacz",
                    str(copied["wacz"]),
                    "--archive-link",
                    str(copied["link"]),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
            if checked.returncode:
                raise ValueError("source receipt and archive verification failed")
            receipt = json.loads(copied["receipt"].read_bytes())
            link = json.loads(copied["link"].read_bytes())
            result = json.loads(copied["result"].read_bytes())
            if not all(isinstance(value, dict) for value in (receipt, link, result)):
                raise ValueError("source evidence metadata must be JSON objects")
            responses = receipt.get("responses")
            if (
                receipt.get("status") != "succeeded"
                or receipt.get("request_bounds", {}).get("kind") != item.kind
                or not isinstance(responses, list)
                or len(responses) != 1
            ):
                raise ValueError("source receipt does not describe one successful response")
            response = responses[0]
            if not isinstance(response, dict) or response.get("status") != 200:
                raise ValueError("source receipt does not describe a complete HTTP response")
            if (
                result.get("status") != "succeeded"
                or result.get("kind") != item.kind
                or result.get("sha256") != response.get("sha256")
                or result.get("bytes") != response.get("bytes")
            ):
                raise ValueError("source result does not describe the verified response")
            resources.append((item, receipt, link, copied["raw"]))

        json_url = urlsplit(_safe_locator(resources[0][1]["responses"][0]["url"]))
        page_url = urlsplit(_safe_locator(resources[1][1]["responses"][0]["url"]))
        if (
            json_url.scheme != page_url.scheme
            or json_url.netloc != page_url.netloc
            or json_url.path != page_url.path + ".json"
            or page_url.path.rsplit("/", 1)[-1] != quote(request.url_title, safe="")
        ):
            raise ValueError("request JSON and page do not describe the queued case")
        raw_request = json.loads(resources[0][3].read_bytes())
        if (
            not isinstance(raw_request, dict)
            or str(raw_request.get("id")) != request_id
            or raw_request.get("url_title") != request.url_title
        ):
            raise ValueError("request JSON does not match the seed queue")
        expected_attachments = raw_request.pop("attachments", [])
        if not isinstance(expected_attachments, list) or len(expected_attachments) != len(
            resources[2:]
        ):
            raise ValueError("request attachment inventory does not match source evidence")
        attachment_sidecar = []
        for original, (_, receipt, link, raw) in zip(
            expected_attachments, resources[2:], strict=True
        ):
            if not isinstance(original, dict):
                raise ValueError("invalid request attachment")
            locator = _safe_locator(original.get("url"))
            if locator != receipt["responses"][0].get("url"):
                raise ValueError("attachment URL does not match its verified receipt")
            attachment_sidecar.append({
                "content_type": original.get("content_type"),
                "size": raw.stat().st_size,
                "warc_record_id": link["record_id"],
            })
        derived_bytes = (json.dumps(raw_request, sort_keys=True) + "\n").encode("utf-8")
        sidecar_bytes = (json.dumps(attachment_sidecar, sort_keys=True) + "\n").encode("utf-8")
        total_bytes += len(derived_bytes) + len(sidecar_bytes)
        if caps.max_bytes is not None and total_bytes > caps.max_bytes:
            raise ValueError("offline evidence exceeds the seed byte cap")
        derived = destination / "request.json"
        derived.write_bytes(derived_bytes)
        (destination / "attachments.json").write_bytes(sidecar_bytes)
        return {"derived_path": str(derived), "bytes_written": total_bytes}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        shutil.rmtree(destination)
        raise CaptureError(
            request_id=request.request_id,
            command=["offline-evidence-import"],
            returncode=1,
            stdout="",
            stderr="offline evidence import failed verification or validation",
        ) from error
