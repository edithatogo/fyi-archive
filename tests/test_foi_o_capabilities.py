from fyi_archive.foi_o_capabilities import validate_foi_o_capabilities


def _document(version: str = "foi-o-nz.core-event.v0.1.0") -> dict[str, object]:
    return {
        "schema_version": "foi-o-nz.capability-declaration.v0.1.0",
        "consumer_id": "fyi-archive-nz",
        "capabilities": [
            {
                "contract_id": "foi-o-nz.core-event",
                "supported_versions": [version],
                "unknown_version_behavior": "reject",
            }
        ],
    }


def test_supported_capability_declaration_is_accepted() -> None:
    result = validate_foi_o_capabilities(_document())
    assert result["ok"] is True


def test_unknown_contract_version_fails_closed() -> None:
    result = validate_foi_o_capabilities(_document("foi-o-nz.core-event.v0.2.0"))
    assert result["ok"] is False
    assert "unknown versions" in result["errors"][0]
