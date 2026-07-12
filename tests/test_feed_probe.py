from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import respx

from fyi_archive.instances import get_instance

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.probe_alaveteli_feeds import main, probe_instance  # noqa: E402


@respx.mock
def test_probe_records_non_json_response() -> None:
    instance = get_instance("uy-quesabes")
    respx.get(instance.capture_base_url() + "/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow:\n")
    )
    respx.get(instance.search_feed_url()).mock(
        return_value=httpx.Response(
            200, text="<html>not a feed</html>", headers={"content-type": "text/html"}
        )
    )
    result = probe_instance("uy-quesabes", timeout_seconds=2, user_agent="test")
    assert result["robots_status"] == 200
    assert result["feed_status"] == 200
    assert result["json_compatible"] is False
    assert result["diagnostic"] == "response body is not valid JSON"
    assert len(result["payload_sha256"]) == 64


@respx.mock
def test_probe_cli_writes_machine_readable_output(tmp_path: Path, monkeypatch) -> None:
    instance = get_instance("uy-quesabes")
    respx.get(instance.capture_base_url() + "/robots.txt").mock(return_value=httpx.Response(200))
    respx.get(instance.search_feed_url()).mock(
        return_value=httpx.Response(
            200, json={"entries": []}, headers={"content-type": "application/json"}
        )
    )
    output = tmp_path / "probe.json"
    monkeypatch.setattr(
        "sys.argv",
        ["probe", "--instance", "uy-quesabes", "--output", str(output), "--delay-seconds", "0"],
    )
    assert main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "alaveteli-feed-probe-v1"
    assert payload["results"][0]["json_compatible"] is True
