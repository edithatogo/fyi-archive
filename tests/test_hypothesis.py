"""Hypothesis property tests for core invariants."""

from __future__ import annotations

import hashlib
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st


def canonical_hash_stable(data: dict[str, Any]) -> str:
    """Canonical hash for manifest records - invariant under key ordering."""
    canonical = repr(sorted(data.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@given(st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
@settings(max_examples=50)
def test_canonical_hash_is_deterministic(data: dict[str, Any]) -> None:
    """Hash must be identical regardless of dict key order."""
    hash1 = canonical_hash_stable(data)
    hash2 = canonical_hash_stable(data)
    assert hash1 == hash2


@given(st.dictionaries(st.text(min_size=1), st.text(), min_size=1))
@settings(max_examples=50)
def test_canonical_hash_changes_if_content_changes(data: dict[str, Any]) -> None:
    """Hash must differ when content differs."""
    hash_original = canonical_hash_stable(data)
    modified = dict(data)
    if modified:
        first_key = next(iter(modified))
        modified[first_key] = str(modified.get(first_key, "")) + "_modified"
        hash_modified = canonical_hash_stable(modified)
        assert hash_original != hash_modified
