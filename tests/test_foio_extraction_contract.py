import json
from pathlib import Path


CONTRACT = Path("tests/fixtures/foi_o_extraction_contract_nz.json")


def test_archive_consumes_pinned_candidate_contract() -> None:
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert document["conforms_to"] == "foi-o-extraction-contract/0.1.0"
    assert document["release_status"] == "draft"
    assert document["candidate_status"] == "candidate"
    assert document["provenance"]["source_revision"] not in {"main", "latest", "HEAD"}
    assert document["profile"]["jurisdiction"] == "NZ"
    assert document["migrations"]["unknown_major"] == "reject"
