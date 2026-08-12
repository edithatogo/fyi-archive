"""Emit the enabled Alaveteli automation policies as a GitHub Actions matrix."""

from __future__ import annotations

import json

from fyi_archive.automation import automation_matrix


def main() -> int:
    """Write one compact, deterministic matrix document to stdout."""
    print(json.dumps(automation_matrix(), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
