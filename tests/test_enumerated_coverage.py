import pytest

from fyi_archive.commands.doctor import get_coverage_info


def test_enumerated_public_denominator_reports_nz_completion(monkeypatch) -> None:
    monkeypatch.delenv("COVERAGE_TARGET_PERCENT", raising=False)
    monkeypatch.delenv("COVERAGE_PUBLIC_DENOMINATOR_NZ_FYI", raising=False)
    monkeypatch.setenv("COVERAGE_PUBLIC_DENOMINATOR", "34432")

    coverage = get_coverage_info(33217)

    assert coverage["denominator"] == 34432
    assert coverage["denominator_method"] == "enumerated_public_records"
    assert coverage["planning_estimate"] is False
    assert coverage["id_horizon"] is None
    assert coverage["target"] == pytest.approx(100.0)
    assert coverage["target_records"] == 34432
    assert coverage["percent_covered"] == pytest.approx(96.47, abs=0.01)
    assert coverage["remaining_to_target"] == 1215


def test_instance_denominator_overrides_global_denominator(monkeypatch) -> None:
    monkeypatch.delenv("COVERAGE_TARGET_PERCENT", raising=False)
    monkeypatch.setenv("COVERAGE_PUBLIC_DENOMINATOR", "100")
    monkeypatch.setenv("COVERAGE_PUBLIC_DENOMINATOR_NZ_FYI", "80")

    coverage = get_coverage_info(80, instance_id="nz-fyi")

    assert coverage["denominator"] == 80
    assert coverage["percent_covered"] == pytest.approx(100.0)
    assert coverage["remaining_to_target"] == 0
