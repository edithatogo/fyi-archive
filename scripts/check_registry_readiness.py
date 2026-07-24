"""Validate the repository-side archive registry readiness contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "registry-readiness.md"
README = ROOT / "README.md"
LICENSE = ROOT / "LICENSE"


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


if __name__ == "__main__":
    check()
    print("Archive registry readiness contract passed.")
