"""Validate the repository-side archive registry readiness contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "registry-readiness.md"
README = ROOT / "README.md"
LICENSE = ROOT / "LICENSE"
EVIDENCE = ROOT / "conductor" / "registry_evidence.json"


def check() -> None:
    text = DOC.read_text(encoding="utf-8") if DOC.is_file() else ""
    required = (
        "repository_ready_external_gates_pending",
        "#227",
        "#228",
        "Source-declared",
        "Zenodo",
        "FAIRsharing",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise AssertionError("Archive registry readiness document missing: " + ", ".join(missing))
    if not README.is_file() or "Zenodo" not in README.read_text(encoding="utf-8"):
        raise AssertionError("README does not document the Zenodo archive surface")
    if not LICENSE.is_file():
        raise AssertionError("Missing repository code licence")
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    zenodo = evidence.get("zenodo", {})
    if (
        zenodo.get("status") != "published_verified"
        or zenodo.get("doi") != "10.5281/zenodo.21338285"
        or zenodo.get("file_count", 0) < 1
    ):
        raise AssertionError("Zenodo registry evidence is not independently recorded")
    fairsharing = evidence.get("fairsharing", {})
    if fairsharing.get("status") != "candidate_not_submitted":
        raise AssertionError("FAIRsharing status must remain candidate_not_submitted")
    if fairsharing.get("submission_authorized") is not False:
        raise AssertionError("FAIRsharing submission must remain unauthorized")


if __name__ == "__main__":
    check()
    print("Archive registry readiness contract passed.")
