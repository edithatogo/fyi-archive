from scripts.capture_historical_fulltext import capture


def test_fulltext_capture_is_fail_closed_for_governance() -> None:
    result = capture({"records": []}, instance_id="au-rtk", delay=0, timeout=1)
    assert result["rights_eligible"] is False
    assert result["annotation_execution_authorized"] is False
    assert result["captured_count"] == 0
