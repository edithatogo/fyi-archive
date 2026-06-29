"""Tests for Zenodo DOI citation updates."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def load_update_citation_doi() -> ModuleType:
    module_path = Path("scripts/update_citation_doi.py")
    spec = importlib.util.spec_from_file_location("update_citation_doi", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_citation_text_replaces_placeholder_url() -> None:
    module = load_update_citation_doi()
    text = 'title: "Example"\n# url: <Zenodo DOI once published>\n'

    updated = module.update_citation_text(text, "10.5281/zenodo.1234567")

    assert 'url: "https://doi.org/10.5281/zenodo.1234567"' in updated
    assert "# url:" not in updated


def test_update_citation_text_accepts_doi_url() -> None:
    module = load_update_citation_doi()

    updated = module.update_citation_text(
        "title: Example\n", "https://doi.org/10.5281/zenodo.7654321"
    )

    assert updated.endswith('url: "https://doi.org/10.5281/zenodo.7654321"\n')


def test_update_citation_text_rejects_invalid_doi() -> None:
    module = load_update_citation_doi()

    with pytest.raises(ValueError, match="Invalid DOI"):
        module.update_citation_text("title: Example\n", "not-a-doi")
