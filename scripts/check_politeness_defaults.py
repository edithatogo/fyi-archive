"""Guard the repository's automated archive pacing defaults."""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_DEFAULTS = {
    ".github/workflows/au_nsw_historical_seed.yml": {"min_interval": 'default: "2.0"'},
    ".github/workflows/automated_historical_backfill.yml": {
        "min_interval": 'default: "2.0"',
        "concurrency": 'default: "1"',
    },
    ".github/workflows/historical_backfill_batch.yml": {
        "min_interval": 'default: "2.0"',
        "concurrency": 'default: "1"',
    },
    ".github/workflows/historical_seed.yml": {
        "min_interval": 'default: "2.0"',
        "concurrency": 'default: "1"',
    },
}


def _input_block(text: str, name: str) -> str:
    match = re.search(
        rf"^      {name}:$(.*?)(?=^      \w+:|^\s*permissions:)", text, re.MULTILINE | re.DOTALL
    )
    if not match:
        raise ValueError(f"workflow input {name!r} is missing")
    return match.group(1)


def validate(root: Path = Path()) -> list[str]:
    """Return pacing-default violations without contacting any source site."""
    violations: list[str] = []
    for relative, inputs in WORKFLOW_DEFAULTS.items():
        path = root / relative
        text = path.read_text(encoding="utf-8")
        for name, expected in inputs.items():
            if expected not in _input_block(text, name):
                violations.append(f"{relative}: {name} must contain {expected}")
    return violations


def main() -> int:
    violations = validate()
    if violations:
        raise SystemExit("\n".join(violations))
    print("politeness defaults are safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
