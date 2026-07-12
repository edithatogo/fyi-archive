from pathlib import Path

WORKFLOW = Path(".github/workflows/alaveteli_working_sites.yml").read_text(encoding="utf-8")


def test_empty_request_discovery_uses_bounded_fallback() -> None:
    discovery = WORKFLOW[WORKFLOW.index("Discover request queue") :]
    assert "test -s" in discovery
    assert "grep -q '[^[:space:]]'" in discovery
    assert 'rm -f "data/$INSTANCE/_state/discovered_requests.jsonl"' in discovery
    assert "discovery=bounded-id-fallback" in discovery
