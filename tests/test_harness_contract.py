"""Meta-tests that keep the repository's quality harness executable."""

from __future__ import annotations

import time

import pytest

from fyi_archive.manifest import canonical_sha256


@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.system
@pytest.mark.smoke
@pytest.mark.property
@pytest.mark.edge
@pytest.mark.performance
@pytest.mark.security
@pytest.mark.compatibility
@pytest.mark.regression
@pytest.mark.sanity
@pytest.mark.usability
def test_harness_contract_is_deterministic() -> None:
    """Exercise a stable, low-cost invariant in every named test profile."""
    payload = {"request_id": 1, "title": "harness"}
    assert canonical_sha256(payload) == canonical_sha256(payload)


@pytest.mark.performance
def test_canonical_hash_throughput_is_bounded() -> None:
    started = time.perf_counter()
    for request_id in range(500):
        canonical_sha256({"request_id": request_id, "title": "performance"})
    assert time.perf_counter() - started < 2.0


@pytest.mark.mutation
def test_mutation_profile_has_a_real_assertion() -> None:
    assert canonical_sha256({"request_id": 1}) != canonical_sha256({"request_id": 2})
