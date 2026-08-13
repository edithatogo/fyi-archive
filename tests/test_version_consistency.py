"""Tests for release version parity."""

from scripts import check_version_consistency


def test_release_version_sources_include_lockfile() -> None:
    expected = check_version_consistency.read_version_file()

    assert check_version_consistency.read_pyproject_version() == expected
    assert check_version_consistency.read_pkg_version() == expected
    assert check_version_consistency.read_lock_version() == expected
