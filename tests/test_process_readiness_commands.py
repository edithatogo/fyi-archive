from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from fyi_archive.commands.process import (
    package_derived,
    validate_au_sampling_frame,
    validate_jurisdiction_targets,
    verify_derived,
)

FIXTURE = Path("tests/fixtures/foi_o_extraction_contract_nz.json")


def test_readiness_commands_cover_success_paths(tmp_path: Path, capsys) -> None:
    validate_au_sampling_frame(path=Path("configs/au/corpus_sampling_frame.json"))
    assert '"valid": true' in capsys.readouterr().out
    validate_jurisdiction_targets(path=Path("configs/jurisdiction_archive_targets.json"))
    assert '"target_count": 42' in capsys.readouterr().out

    manifest = tmp_path / "manifest.json"
    manifest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    candidates = tmp_path / "candidates.ndjson"
    candidates.write_text(json.dumps({"candidate_id": "one"}) + "\n", encoding="utf-8")
    output = tmp_path / "bundle"
    package_derived(manifest=manifest, candidates=candidates, output_dir=output, baseline=None)
    assert '"publication_status": "not_published"' in capsys.readouterr().out
    verify_derived(output_dir=output)
    assert '"verified": true' in capsys.readouterr().out


@pytest.mark.parametrize(
    ("call", "kwargs"),
    [
        (validate_au_sampling_frame, {"path": Path("missing-au.json")}),
        (validate_jurisdiction_targets, {"path": Path("missing-targets.json")}),
        (
            package_derived,
            {
                "manifest": Path("missing-manifest.json"),
                "candidates": Path("missing-candidates.ndjson"),
                "output_dir": Path("unused"),
                "baseline": None,
            },
        ),
        (verify_derived, {"output_dir": Path("missing-bundle")}),
    ],
)
def test_readiness_commands_translate_validation_errors(call, kwargs) -> None:
    with pytest.raises(typer.BadParameter):
        call(**kwargs)
