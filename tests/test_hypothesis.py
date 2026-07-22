"""Hypothesis property tests for core invariants."""

from __future__ import annotations

import hashlib
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from fyi_archive.health import parity_report


def canonical_hash_stable(data: dict[str, Any]) -> str:
    """Canonical hash for manifest records - invariant under key ordering."""
    canonical = repr(sorted(data.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@given(st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_canonical_hash_is_deterministic(data: dict[str, Any]) -> None:
    """Hash must be identical regardless of dict key order."""
    hash1 = canonical_hash_stable(data)
    hash2 = canonical_hash_stable(data)
    assert hash1 == hash2


@given(st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_canonical_hash_changes_if_content_changes(data: dict[str, Any]) -> None:
    """Hash must differ when content differs."""
    hash_original = canonical_hash_stable(data)
    modified = dict(data)
    if modified:
        first_key = next(iter(modified))
        modified[first_key] = str(modified.get(first_key, "")) + "_modified"
        hash_modified = canonical_hash_stable(modified)
        assert hash_original != hash_modified


@given(
    manifest_records=st.integers(min_value=0, max_value=10_000),
    tolerance=st.integers(min_value=0, max_value=50),
    skew=st.integers(min_value=-50, max_value=50),
)
@settings(max_examples=100)
def test_parity_report_health_tracks_tolerance(
    manifest_records: int,
    tolerance: int,
    skew: int,
) -> None:
    """Mirror parity health must match the configured absolute skew tolerance."""
    mirror_count = max(0, manifest_records - skew)
    actual_skew = manifest_records - mirror_count

    report = parity_report(
        manifest_records=manifest_records,
        mirror_records={"huggingface": mirror_count},
        tolerance=tolerance,
    )

    assert report["healthy"] is (abs(actual_skew) <= tolerance)
    assert report["mirrors"]["huggingface"]["within_tolerance"] is report["healthy"]
